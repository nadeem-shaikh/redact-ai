// redact-ai local web UI — single-file vanilla JS implementation.
// Copy strings live in BUILD_SPEC §15.2; keep them in sync.
(() => {
  "use strict";

  const COPY = {
    idle: "Drop a screenshot here, or click to choose a file.",
    working: "Redacting…",
    success: (n, k) => `Done. ${n} regions redacted across ${k} categories.`,
    noFindings: "No sensitive content found. Output is your original image.",
    errors: {
      E_INPUT_FORMAT:
        "That file type isn't supported. Try PNG, JPEG, WebP, GIF, BMP, TIFF, HEIC/HEIF, or AVIF.",
      E_OCR: "We couldn't read text from that image. Try a sharper version.",
      E_REDACTION:
        "Something went wrong and we didn't produce an output. No data left your device.",
    },
  };

  const dropZone = document.getElementById("drop-zone");
  const dropZoneMessage = document.getElementById("drop-zone-message");
  const fileInput = document.getElementById("file-input");
  const submit = document.getElementById("submit-button");
  const status = document.getElementById("status");
  const styleSelect = document.getElementById("style-select");
  const resultSection = document.getElementById("result");
  const previewOriginal = document.getElementById("preview-original");
  const previewRedacted = document.getElementById("preview-redacted");
  const downloadLink = document.getElementById("download-link");
  const downloadManifest = document.getElementById("download-manifest");
  const copyImage = document.getElementById("copy-image");
  const manifestPreview = document.getElementById("manifest-preview");

  let currentFile = null;
  let currentManifest = null;
  let currentRedactedBlob = null;
  let currentRedactedURL = null;
  let currentOriginalURL = null;

  function readCsrfToken() {
    const meta = document.querySelector('meta[name="rai-csrf"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function setStatus(text, isError) {
    status.textContent = text;
    status.classList.toggle("error", Boolean(isError));
  }

  function selectFile(file) {
    if (!file) return;
    currentFile = file;
    dropZoneMessage.textContent = file.name;
    submit.disabled = false;
    if (currentOriginalURL) {
      URL.revokeObjectURL(currentOriginalURL);
    }
    currentOriginalURL = URL.createObjectURL(file);
    previewOriginal.src = currentOriginalURL;
    resultSection.hidden = false;
    previewRedacted.removeAttribute("src");
    setStatus("");
  }

  ["dragenter", "dragover"].forEach((event) => {
    dropZone.addEventListener(event, (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      dropZone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((event) => {
    dropZone.addEventListener(event, (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      dropZone.classList.remove("dragging");
    });
  });
  dropZone.addEventListener("drop", (ev) => {
    if (ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0]) {
      selectFile(ev.dataTransfer.files[0]);
    }
  });
  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener("change", (ev) => {
    const files = ev.target.files;
    if (files && files[0]) {
      selectFile(files[0]);
    }
  });

  submit.addEventListener("click", async () => {
    if (!currentFile) {
      return;
    }
    submit.disabled = true;
    setStatus(COPY.working);
    const data = new FormData();
    data.append("image", currentFile);
    data.append("policy_id", "default");
    if (styleSelect.value) {
      data.append("style", styleSelect.value);
    }
    try {
      const response = await fetch("/redact", {
        method: "POST",
        body: data,
        headers: {
          Accept: "application/json",
          "X-Redact-CSRF": readCsrfToken(),
        },
      });
      if (!response.ok) {
        const payload = await safeJson(response);
        const code = payload && payload.error ? payload.error.code : "";
        const message = (payload && payload.error && payload.error.message) || "Something went wrong.";
        const hint = (payload && payload.error && payload.error.hint) || "";
        const localised = COPY.errors[code] || message;
        setStatus(`${localised}${hint ? ` ${hint}` : ""}`, true);
        return;
      }
      const payload = await response.json();
      const manifest = payload.manifest;
      currentManifest = manifest;
      const bytesB64 = payload.image.bytes_b64;
      const mime = payload.image.mime_type;
      const blob = b64ToBlob(bytesB64, mime);
      currentRedactedBlob = blob;
      if (currentRedactedURL) {
        URL.revokeObjectURL(currentRedactedURL);
      }
      currentRedactedURL = URL.createObjectURL(blob);
      previewRedacted.src = currentRedactedURL;
      downloadLink.href = currentRedactedURL;
      downloadLink.download = makeDownloadName(currentFile.name, mime);
      manifestPreview.textContent = JSON.stringify(manifest, null, 2);
      const n = manifest.stats.redactions_total;
      const k = Object.keys(manifest.stats.by_category || {}).length;
      setStatus(n === 0 ? COPY.noFindings : COPY.success(n, k));
    } catch (err) {
      setStatus("Network error. The server is local; please retry.", true);
    } finally {
      submit.disabled = false;
    }
  });

  downloadManifest.addEventListener("click", () => {
    if (!currentManifest) return;
    const blob = new Blob([JSON.stringify(currentManifest, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "manifest.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  copyImage.addEventListener("click", async () => {
    if (!currentRedactedBlob) return;
    try {
      if (navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([
          new ClipboardItem({ [currentRedactedBlob.type]: currentRedactedBlob }),
        ]);
        setStatus("Copied redacted image to clipboard.");
      } else {
        setStatus("Clipboard image copy is not supported in this browser.", true);
      }
    } catch (err) {
      setStatus("Could not copy to clipboard. Try downloading instead.", true);
    }
  });

  async function safeJson(response) {
    try {
      return await response.json();
    } catch (err) {
      return null;
    }
  }

  function b64ToBlob(b64, mime) {
    const binary = atob(b64);
    const len = binary.length;
    const buf = new Uint8Array(len);
    for (let i = 0; i < len; i++) buf[i] = binary.charCodeAt(i);
    return new Blob([buf], { type: mime });
  }

  function makeDownloadName(originalName, mime) {
    const dot = originalName.lastIndexOf(".");
    const base = dot > 0 ? originalName.slice(0, dot) : originalName;
    const ext = mime.split("/")[1] || "png";
    return `${base}.redacted.${ext}`;
  }
})();
