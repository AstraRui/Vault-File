const form = document.getElementById("create-form");
const resultBox = document.getElementById("result");
const resultLink = document.getElementById("result-link");
const errorBox = document.getElementById("error");
const copyBtn = document.getElementById("copy-btn");
const contentInput = document.getElementById("content");
const fileInput = document.getElementById("file");
const ttlSelect = document.getElementById("ttl");
const attachBtn = document.getElementById("attach-btn");
const fileChip = document.getElementById("file-chip");
const fileNameLabel = document.getElementById("file-name");
const fileClearBtn = document.getElementById("file-clear");

const COPY_ICON = '<i class="bi bi-copy"></i>';
const COPIED_ICON = '<i class="bi bi-check2 text-success"></i>';

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function setFile(file) {
  if (!file) {
    fileInput.value = "";
    fileChip.classList.add("d-none");
    attachBtn.classList.remove("d-none");
    contentInput.disabled = false;
    contentInput.placeholder = "Введите секретный текст...";
    return;
  }

  fileNameLabel.textContent = `${file.name} (${formatSize(file.size)})`;
  fileChip.classList.remove("d-none");
  attachBtn.classList.add("d-none");

  contentInput.value = "";
  contentInput.disabled = true;
  contentInput.placeholder = "Прикреплен файл. Текст недоступен.";
}

attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => setFile(fileInput.files[0] || null));
fileClearBtn.addEventListener("click", () => setFile(null));

contentInput.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    form.requestSubmit();
  }
});

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("d-none");
}

async function createTextSecret(ttlSeconds) {
  return fetch("/api/v1/secrets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: contentInput.value, ttl_seconds: ttlSeconds }),
  });
}

async function createFileSecret(ttlSeconds) {
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("ttl_seconds", ttlSeconds);
  return fetch("/api/v1/secrets/file", { method: "POST", body: formData });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.classList.add("d-none");
  resultBox.classList.add("d-none");

  const hasFile = fileInput.files.length > 0;
  const ttlSeconds = Number(ttlSelect.value);

  if (!hasFile && !contentInput.value.trim()) {
    showError("Введите текст или прикрепите файл");
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  const originalBtnText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML =
    '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Создание...';

  try {
    const response = hasFile
      ? await createFileSecret(ttlSeconds)
      : await createTextSecret(ttlSeconds);

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось создать секрет");
    }

    resultLink.value = `${window.location.origin}/view.html?id=${data.id}`;
    resultBox.classList.remove("d-none");

    resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

    form.reset();
    setFile(null);
  } catch (err) {
    showError(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnText;
  }
});

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(resultLink.value);
    copyBtn.innerHTML = COPIED_ICON;
    setTimeout(() => {
      copyBtn.innerHTML = COPY_ICON;
    }, 2000);
  } catch (err) {
    console.error("Failed to copy", err);
  }
});
