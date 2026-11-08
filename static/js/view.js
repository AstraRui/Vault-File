const revealState = document.getElementById("state-reveal");
const loadingState = document.getElementById("state-loading");
const textState = document.getElementById("state-text");
const fileState = document.getElementById("state-file");
const errorState = document.getElementById("state-error");

const revealBtn = document.getElementById("reveal-btn");
const secretTextArea = document.getElementById("secret-text");
const copyTextBtn = document.getElementById("copy-text-btn");
const fileInfo = document.getElementById("file-info");
const downloadBtn = document.getElementById("download-btn");
const errorMessage = document.getElementById("error-message");

function showState(element) {
  [revealState, loadingState, textState, fileState, errorState].forEach((el) =>
    el.classList.add("d-none")
  );
  element.classList.remove("d-none");
}

function parseFilename(contentDisposition) {
  const match = /filename\*=UTF-8''([^;]+)/.exec(contentDisposition || "");
  return match ? decodeURIComponent(match[1]) : "файл";
}

async function revealSecret() {
  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) {
    errorMessage.textContent = "Ссылка некорректна: отсутствует идентификатор секрета";
    showState(errorState);
    return;
  }

  showState(loadingState);

  try {
    const response = await fetch(`/api/v1/secrets/${id}`);
    const contentType = response.headers.get("content-type") || "";

    if (!response.ok) {
      const data = contentType.includes("application/json") ? await response.json() : null;
      errorMessage.textContent = data?.detail || "Не удалось открыть секрет";
      showState(errorState);
      return;
    }

    if (contentType.includes("application/json")) {
      const data = await response.json();
      secretTextArea.value = data.content;
      showState(textState);
      return;
    }

    const filename = parseFilename(response.headers.get("content-disposition"));
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    fileInfo.textContent = filename;
    downloadBtn.href = url;
    downloadBtn.download = filename;
    downloadBtn.addEventListener(
      "click",
      () => setTimeout(() => URL.revokeObjectURL(url), 1000),
      { once: true }
    );
    showState(fileState);
  } catch (err) {
    errorMessage.textContent = "Не удалось связаться с сервером";
    showState(errorState);
  }
}

revealBtn.addEventListener("click", revealSecret);

copyTextBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(secretTextArea.value);
  copyTextBtn.innerHTML = '<i class="bi bi-check2 text-success"></i> Скопировано';
  setTimeout(() => {
    copyTextBtn.innerHTML = '<i class="bi bi-copy"></i> Скопировать';
  }, 2000);
});
