// StudyPal Web - frontend

const $ = (id) => document.getElementById(id);

const state = {
  audioBlob: null,
  transcript: "",
  translation: "",
  mediaRecorder: null,
  chunks: [],
  recording: false,
  currentAudioUrl: null,
};

// Tab switching
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.add("active");
  });
});

function setStatus(msg, cls = "") {
  const s = $("status");
  s.textContent = msg;
  s.className = "status " + cls;
}

async function copyText(id) {
  const el = $(id);
  if (!el || !el.value) return;
  try {
    await navigator.clipboard.writeText(el.value);
    setStatus("Copied", "success");
    setTimeout(() => setStatus(""), 1500);
  } catch {
    setStatus("Copy failed", "error");
  }
}

// Voices
async function loadVoices() {
  try {
    const r = await fetch("/api/voices");
    const data = await r.json();
    const sel = $("voiceSelect");
    sel.innerHTML = "";
    for (const v of data.voices) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      if (v === data.current) opt.selected = true;
      sel.appendChild(opt);
    }
    setStatus(data.voices.length + " voices loaded", "success");
    setTimeout(() => setStatus(""), 1500);
  } catch (e) {
    setStatus("Voices failed: " + e.message, "error");
  }
}

// Document extraction
$("docFile").addEventListener("change", async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  setStatus("Extracting...");
  const fd = new FormData();
  fd.append("file", file);
  try {
    const r = await fetch("/api/extract", { method: "POST", body: fd });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    $("docText").value = data.text;
    $("docInfo").textContent = file.name;
    setStatus("Loaded " + file.name, "success");
    setTimeout(() => setStatus(""), 2000);
  } catch (e) {
    setStatus("Extract failed: " + e.message, "error");
  }
});

function pasteMode() {
  $("docText").focus();
  $("docInfo").textContent = "Paste mode";
}

// Audio upload
$("audioFile").addEventListener("change", async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  state.audioBlob = file;
  $("audioInfo").textContent = file.name + " (" + (file.size / 1024).toFixed(0) + " KB)";
  await transcribe(file);
});

// Record
$("recordBtn").addEventListener("click", async () => {
  if (state.recording) {
    state.mediaRecorder.stop();
    state.recording = false;
    $("recordBtn").textContent = "Record";
    $("recordBtn").classList.remove("warn");
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.chunks = [];
    state.mediaRecorder = new MediaRecorder(stream);
    state.mediaRecorder.ondataavailable = (e) => state.chunks.push(e.data);
    state.mediaRecorder.onstop = async () => {
      const blob = new Blob(state.chunks, { type: "audio/webm" });
      state.audioBlob = blob;
      $("audioInfo").textContent = "Recorded (" + (blob.size / 1024).toFixed(0) + " KB)";
      stream.getTracks().forEach((t) => t.stop());
      await transcribe(blob);
    };
    state.mediaRecorder.start();
    state.recording = true;
    $("recordBtn").textContent = "Stop Recording";
    $("recordBtn").classList.add("warn");
    setStatus("Recording...");
  } catch (e) {
    setStatus("Mic denied: " + e.message, "error");
  }
});

async function transcribe(blob) {
  setStatus("Transcribing... (may take a while)");
  const fd = new FormData();
  fd.append("file", blob, "audio.wav");
  try {
    const r = await fetch("/api/transcribe", { method: "POST", body: fd });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    state.transcript = data.transcript || "";
    $("transcript").value = state.transcript;
    $("transcriptCard").hidden = false;
    setStatus("Transcribed (" + (data.language || "?") + ")", "success");
    setTimeout(() => setStatus(""), 2000);
  } catch (e) {
    setStatus("Transcribe failed: " + e.message, "error");
  }
}

// Translate
$("translateBtn").addEventListener("click", async () => {
  const text = $("transcript").value.trim();
  const target = $("targetLang").value;
  if (!text || !target) {
    setStatus("Need text and target language", "error");
    return;
  }
  setStatus("Translating...");
  try {
    const r = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text, target: target }),
    });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    state.translation = data.translated;
    $("translation").value = data.translated;
    $("translationWrap").hidden = false;
    setStatus("Translated", "success");
    setTimeout(() => setStatus(""), 1500);
  } catch (e) {
    setStatus("Translate failed: " + e.message, "error");
  }
});

// TTS
async function fetchAndPlay(text, speed) {
  const voice = $("voiceSelect").value;
  const sp = speed != null ? speed : parseFloat($("speedSlider").value);
  setStatus("Generating audio...");
  try {
    const r = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text, voice: voice, speed: sp }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.error || r.statusText);
    }
    const blob = await r.blob();
    if (state.currentAudioUrl) URL.revokeObjectURL(state.currentAudioUrl);
    state.currentAudioUrl = URL.createObjectURL(blob);
    const player = $("player");
    player.src = state.currentAudioUrl;
    await player.play();
    setStatus("Playing");
    $("pauseBtn").disabled = false;
    $("stopBtn").disabled = false;
    $("saveAudioBtn").disabled = false;
  } catch (e) {
    setStatus("TTS failed: " + e.message, "error");
  }
}

function readAloud(textareaId) {
  const text = $(textareaId).value.trim();
  if (!text) return;
  fetchAndPlay(text);
}

function playText() {
  const text = $("docText").value.trim();
  if (!text) { setStatus("Nothing to read", "error"); return; }
  fetchAndPlay(text);
}

function pauseText() {
  const p = $("player");
  if (p.paused) { p.play(); $("pauseBtn").textContent = "Pause"; }
  else { p.pause(); $("pauseBtn").textContent = "Resume"; }
}

function stopText() {
  const p = $("player");
  p.pause();
  p.currentTime = 0;
  $("pauseBtn").textContent = "Pause";
  $("pauseBtn").disabled = true;
  $("stopBtn").disabled = true;
  setStatus("");
}

$("speedSlider").addEventListener("input", (e) => {
  $("speedLabel").textContent = parseFloat(e.target.value).toFixed(1) + "x";
});

// Save audio
async function saveAudioFromText() {
  const player = $("player");
  if (!player.src) { setStatus("Nothing to save - play first", "error"); return; }
  try {
    const blob = await (await fetch(player.src)).blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "studypal.wav";
    a.click();
    URL.revokeObjectURL(url);
    setStatus("Audio saved", "success");
  } catch (e) {
    setStatus("Save failed: " + e.message, "error");
  }
}

// Save transcript
function downloadFile(name, content) {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function saveAsTxt() {
  const text = $("transcript").value.trim();
  if (!text) return;
  downloadFile("studypal_transcript.txt", text);
}

function saveAsSrt() {
  const text = $("transcript").value.trim();
  if (!text) return;
  const srt = "1\n00:00:00,000 --> 00:00:30,000\n" + text + "\n";
  downloadFile("studypal_transcript.srt", srt);
}

// Player events
$("player").addEventListener("ended", () => {
  $("pauseBtn").disabled = true;
  $("stopBtn").disabled = true;
  $("pauseBtn").textContent = "Pause";
  setStatus("");
});

// Boot
loadVoices();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
