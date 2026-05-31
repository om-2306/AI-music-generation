const state = {
  currentJobId: null,
  polling: null,
  pianoTick: 0,
};

const elements = {
  projectPath: document.querySelector("#projectPath"),
  music21Status: document.querySelector("#music21Status"),
  tensorflowStatus: document.querySelector("#tensorflowStatus"),
  midiCount: document.querySelector("#midiCount"),
  modelStatus: document.querySelector("#modelStatus"),
  rawFiles: document.querySelector("#rawFiles"),
  generatedFiles: document.querySelector("#generatedFiles"),
  logs: document.querySelector("#logs"),
  jobBadge: document.querySelector("#jobBadge"),
  buttons: [...document.querySelectorAll("button")],
  canvas: document.querySelector("#pianoRoll"),
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function setBadge(status) {
  elements.jobBadge.className = "";
  elements.jobBadge.textContent = status[0].toUpperCase() + status.slice(1);
  if (["running", "failed", "completed"].includes(status)) {
    elements.jobBadge.classList.add(status);
  }
}

function setBusy(isBusy) {
  elements.buttons.forEach((button) => {
    button.disabled = isBusy;
  });
}

function setStage(action, status) {
  document.querySelectorAll(".stage").forEach((stage) => stage.classList.remove("active"));
  if (status !== "running") return;
  const map = {
    demo: "data",
    train: "train",
    generate: "generate",
  };
  const target = document.querySelector(`[data-stage="${map[action] || "data"}"]`);
  if (target) target.classList.add("active");
}

async function refreshStatus() {
  const status = await requestJson("/api/status");
  elements.projectPath.textContent = status.projectRoot;
  const byName = Object.fromEntries(status.dependencies.map((item) => [item.name, item]));
  elements.music21Status.textContent = byName.music21.installed ? "Ready" : "Missing";
  elements.tensorflowStatus.textContent = byName.tensorflow.installed ? "Ready" : "Missing";
  elements.midiCount.textContent = String(status.rawMidiCount);
  elements.modelStatus.textContent = status.modelReady ? "Ready" : "Not trained";
}

function renderFileList(node, files, generated = false) {
  node.innerHTML = "";
  if (!files.length) {
    const empty = document.createElement("li");
    empty.innerHTML = "<span>None yet</span><small>-</small>";
    node.appendChild(empty);
    return;
  }

  files.forEach((file) => {
    const item = document.createElement("li");
    const name = document.createElement(generated ? "a" : "span");
    name.textContent = file.name;
    if (generated) {
      name.href = `/generated/${encodeURIComponent(file.name)}`;
      name.download = file.name;
    }
    const size = document.createElement("small");
    size.textContent = formatSize(file.size);
    item.append(name, size);
    node.appendChild(item);
  });
}

async function refreshFiles() {
  const files = await requestJson("/api/files");
  renderFileList(elements.rawFiles, files.raw);
  renderFileList(elements.generatedFiles, files.generated, true);
}

async function refreshAll() {
  try {
    await Promise.all([refreshStatus(), refreshFiles()]);
  } catch (error) {
    elements.projectPath.textContent = "Run python src/web_app.py";
    elements.music21Status.textContent = "-";
    elements.tensorflowStatus.textContent = "-";
    elements.midiCount.textContent = "0";
    elements.modelStatus.textContent = "Offline";
    setBadge("failed");
    elements.logs.textContent = error.message;
  }
}

async function startJob(action, params) {
  try {
    setBusy(true);
    setBadge("queued");
    elements.logs.textContent = "Queued...\n";
    const job = await requestJson("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ action, params }),
    });
    state.currentJobId = job.id;
    pollJob();
    state.polling = setInterval(pollJob, 1000);
  } catch (error) {
    setBusy(false);
    setBadge("failed");
    elements.logs.textContent = error.message;
  }
}

async function pollJob() {
  if (!state.currentJobId) return;
  const job = await requestJson(`/api/jobs/${state.currentJobId}`);
  setBadge(job.status);
  setStage(job.action, job.status);
  elements.logs.textContent = (job.logs || []).join("\n") || "Starting...";
  elements.logs.scrollTop = elements.logs.scrollHeight;

  if (!["queued", "running"].includes(job.status)) {
    clearInterval(state.polling);
    state.polling = null;
    state.currentJobId = null;
    setBusy(false);
    setStage(job.action, job.status);
    await refreshAll();
  }
}

function formParams(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function uploadFiles(files) {
  if (!files.length) return;
  setBusy(true);
  setBadge("running");
  elements.logs.textContent = "";

  try {
    for (const file of files) {
      const buffer = await file.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = "";
      bytes.forEach((byte) => {
        binary += String.fromCharCode(byte);
      });
      await requestJson("/api/upload", {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          content: btoa(binary),
        }),
      });
      elements.logs.textContent += `Uploaded ${file.name}\n`;
    }
    setBadge("completed");
    await refreshAll();
  } catch (error) {
    setBadge("failed");
    elements.logs.textContent += error.message;
  } finally {
    setBusy(false);
  }
}

function drawPianoRoll() {
  const canvas = elements.canvas;
  const context = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.floor(rect.width * scale));
  const height = Math.max(1, Math.floor(rect.height * scale));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#fffdf8";
  context.fillRect(0, 0, width, height);

  const rowCount = 12;
  for (let row = 0; row <= rowCount; row += 1) {
    const y = (row / rowCount) * height;
    context.strokeStyle = row % 3 === 0 ? "#d9d4c8" : "#eee8dc";
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }

  const colors = ["#0f766e", "#b7791f", "#b42346", "#247857"];
  for (let index = 0; index < 42; index += 1) {
    const lane = (index * 5 + 2) % rowCount;
    const x = ((index * 78 - state.pianoTick * 1.8) % (width + 180)) - 160;
    const y = (lane / rowCount) * height + 5;
    const noteWidth = 44 + ((index * 17) % 82);
    const noteHeight = Math.max(8, height / 18);
    context.fillStyle = colors[index % colors.length];
    context.globalAlpha = 0.82;
    context.fillRect(x, y, noteWidth, noteHeight);
  }
  context.globalAlpha = 1;

  state.pianoTick += state.currentJobId ? 2 : 0.55;
  requestAnimationFrame(drawPianoRoll);
}

document.querySelector("#demoForm").addEventListener("submit", (event) => {
  event.preventDefault();
  startJob("demo", formParams(event.currentTarget));
});

document.querySelector("#trainForm").addEventListener("submit", (event) => {
  event.preventDefault();
  startJob("train", formParams(event.currentTarget));
});

document.querySelector("#generateForm").addEventListener("submit", (event) => {
  event.preventDefault();
  startJob("generate", formParams(event.currentTarget));
});

document.querySelector("#refreshBtn").addEventListener("click", refreshAll);
document.querySelector("#midiInput").addEventListener("change", (event) => {
  uploadFiles([...event.target.files]);
  event.target.value = "";
});

refreshAll();
drawPianoRoll();
