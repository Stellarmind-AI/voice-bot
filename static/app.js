// // Silence-detection recorder + simple survey loop
// async function playAudio(url) {
//     return new Promise((resolve, reject) => {
//       const audio = new Audio(url);
//       audio.preload = "auto";
//       audio.onended = () => resolve();
//       audio.onerror = (e) => reject(e);
//       const p = audio.play();
//       if (p && typeof p.then === "function") {
//         p.catch((err) => {
//           // If autoplay blocked, resolve so flow continues; user clicked Start earlier so should be fine.
//           console.warn("Autoplay/play error:", err);
//           resolve();
//         });
//       }
//     });
//   }
  
//   async function playInSequence(urls = []) {
//     for (const u of urls) {
//       await playAudio(u);
//     }
//   }
  
//   const logDiv = document.getElementById("log");
//   function log(msg) {
//     const p = document.createElement("p");
//     p.textContent = msg;
//     logDiv.appendChild(p);
//     logDiv.scrollTop = logDiv.scrollHeight;
//   }
  
//   let running = false;
//   let questionIndex = 0;
//   let mediaStream = null;
//   let mediaRecorder = null;
//   let chunks = [];
//   let rafId = null;
//   let audioContext = null;
//   let analyser = null;
  
//   const SILENCE_AFTER_SPEECH_MS = 1500; // stop after ~1.5s silence
//   const MIN_SPEECH_MS = 300;            // ignore tiny blips
//   const RMS_START_THRESHOLD = 0.02;     // start talking threshold
//   const RMS_CONTINUE_THRESHOLD = 0.015; // stay talking threshold
//   const MAX_UTTERANCE_MS = 30000;       // safety cap 30s
  
//   async function startSurvey() {
//     running = true;
//     questionIndex = 0;
//     logDiv.innerHTML = "";
  
//     // Initial request to get first question + its TTS
//     const res = await fetch("/api/start", { method: "POST" });
//     const data = await res.json();
//     if (data.done) {
//       log("Survey already done.");
//       return;
//     }
  
//     // Play first question (this click unlocks autoplay)
//     await playAudio(data.question_tts_url);
//     log("🤖 " + data.question_text);
  
//     await ensureMic();
//     captureNextAnswerLoop();
//   }
  
//   async function ensureMic() {
//     if (mediaStream) return;
//     mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
//     audioContext = new (window.AudioContext || window.webkitAudioContext)();
//     const sourceNode = audioContext.createMediaStreamSource(mediaStream);
//     analyser = audioContext.createAnalyser();
//     analyser.fftSize = 2048;
//     sourceNode.connect(analyser);
//   }
  
//   function resetUtteranceState() {
//     chunks = [];
//     if (mediaRecorder && mediaRecorder.state === "recording") {
//       try { mediaRecorder.stop(); } catch(e) {}
//     }
//     mediaRecorder = null;
//   }
  
//   function startRecorder() {
//     if (mediaRecorder && mediaRecorder.state === "recording") return;
//     mediaRecorder = new MediaRecorder(mediaStream, { mimeType: "audio/webm" });
//     mediaRecorder.ondataavailable = (e) => {
//       if (e.data && e.data.size > 0) chunks.push(e.data);
//     };
//     mediaRecorder.onstop = async () => {
//       const blob = new Blob(chunks, { type: "audio/webm" });
//       await sendAnswerBlob(blob);
//       if (!running) return;
//       captureNextAnswerLoop();
//     };
//     mediaRecorder.start();
//   }
  
//   function stopRecorder() {
//     if (mediaRecorder && mediaRecorder.state === "recording") {
//       mediaRecorder.stop();
//     }
//   }
  
//   function captureNextAnswerLoop() {
//     resetUtteranceState();
//     if (rafId) cancelAnimationFrame(rafId);
//     const floatBuf = new Float32Array(analyser.fftSize);
//     let speaking = false;
//     let speechStartedAt = 0;
//     let silenceMs = 0;
  
//     const loop = (t) => {
//       analyser.getFloatTimeDomainData(floatBuf);
//       let sum = 0;
//       for (let i=0; i<floatBuf.length; i++) {
//         const v = floatBuf[i];
//         sum += v * v;
//       }
//       const rms = Math.sqrt(sum / floatBuf.length);
//       const now = performance.now();
  
//       if (!speaking) {
//         if (rms >= RMS_START_THRESHOLD) {
//           speaking = true;
//           speechStartedAt = now;
//           silenceMs = 0;
//           startRecorder();
//         }
//       } else {
//         const elapsed = now - speechStartedAt;
  
//         if (rms < RMS_CONTINUE_THRESHOLD) {
//           // increment silence estimate by approx frame duration (16ms)
//           silenceMs += 16;
//         } else {
//           silenceMs = 0;
//         }
  
//         // stop when enough silence after some speech OR safety limit reached
//         if (elapsed > MIN_SPEECH_MS && (silenceMs >= SILENCE_AFTER_SPEECH_MS || elapsed >= MAX_UTTERANCE_MS)) {
//           stopRecorder();
//           return;
//         }
//       }
  
//       rafId = requestAnimationFrame(loop);
//     };
  
//     rafId = requestAnimationFrame(loop);
//   }
  
//   async function sendAnswerBlob(blob) {
//     log("⏳ Transcribing...");
//     const form = new FormData();
//     form.append("question_index", String(questionIndex));
//     form.append("audio", blob, "answer.webm");
  
//     const res = await fetch("/api/answer", { method: "POST", body: form });
//     const data = await res.json();
//     if (data.error) {
//       log("Error: " + data.error);
//       return;
//     }
  
//     log("🗣 You: " + (data.transcript || "[no transcription]"));
  
//     if (data.done) {
//       await playInSequence([data.ack_tts_url, data.done_tts_url]);
//       log("✅ Survey completed.");
//       running = false;
//       document.getElementById("stopBtn").disabled = true;
//       document.getElementById("startBtn").disabled = false;
//     } else {
//       // advance index, play ack + next question
//       questionIndex = data.next_question_index;
//       await playInSequence([data.ack_tts_url, data.next_question_tts_url]);
//       log("🤖 " + data.next_question_text);
//     }
//   }
  
//   document.getElementById("startBtn").addEventListener("click", async () => {
//     document.getElementById("startBtn").disabled = true;
//     document.getElementById("stopBtn").disabled = false;
//     await startSurvey();
//   });
  
//   document.getElementById("stopBtn").addEventListener("click", () => {
//     running = false;
//     if (rafId) cancelAnimationFrame(rafId);
//     document.getElementById("stopBtn").disabled = true;
//     document.getElementById("startBtn").disabled = false;
//     try {
//       stopRecorder();
//       if (audioContext && audioContext.state !== "closed") audioContext.close();
//     } catch (e) {}
//   });

// Silence-detection recorder + dynamic bot (LLM) loop
async function playAudio(url) {
  return new Promise((resolve, reject) => {
    const audio = new Audio(url);
    audio.preload = "auto";
    audio.onended = () => resolve();
    audio.onerror = (e) => reject(e);
    const p = audio.play();
    if (p && typeof p.then === "function") {
      p.catch((err) => {
        console.warn("Autoplay/play error:", err);
        resolve();
      });
    }
  });
}

async function playInSequence(urls = []) {
  for (const u of urls) {
    await playAudio(u);
  }
}

const logDiv = document.getElementById("log");
function log(msg) {
  const p = document.createElement("p");
  p.textContent = msg;
  logDiv.appendChild(p);
  logDiv.scrollTop = logDiv.scrollHeight;
}

let running = false;
let questionIndex = 0;
let mediaStream = null;
let mediaRecorder = null;
let chunks = [];
let rafId = null;
let audioContext = null;
let analyser = null;
let sessionId = null;

const SILENCE_AFTER_SPEECH_MS = 1500;
const MIN_SPEECH_MS = 300;
const RMS_START_THRESHOLD = 0.02;
const RMS_CONTINUE_THRESHOLD = 0.015;
const MAX_UTTERANCE_MS = 30000;

async function startSurvey() {
  running = true;
  questionIndex = 0;
  logDiv.innerHTML = "";

  const res = await fetch("/api/start", { method: "POST" });
  const data = await res.json();
  if (data.done) {
    log("Survey already done.");
    return;
  }

  sessionId = data.session_id;
  await playAudio(data.question_tts_url);
  log("🤖 " + data.question_text);

  await ensureMic();
  captureNextAnswerLoop();
}

async function ensureMic() {
  if (mediaStream) return;
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const sourceNode = audioContext.createMediaStreamSource(mediaStream);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 2048;
  sourceNode.connect(analyser);
}

function resetUtteranceState() {
  chunks = [];
  if (mediaRecorder && mediaRecorder.state === "recording") {
    try { mediaRecorder.stop(); } catch(e) {}
  }
  mediaRecorder = null;
}

function startRecorder() {
  if (mediaRecorder && mediaRecorder.state === "recording") return;
  mediaRecorder = new MediaRecorder(mediaStream, { mimeType: "audio/webm" });
  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) chunks.push(e.data);
  };
  mediaRecorder.onstop = async () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    await sendAnswerBlob(blob);
    if (!running) return;
    captureNextAnswerLoop();
  };
  mediaRecorder.start();
}

function stopRecorder() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
}

function captureNextAnswerLoop() {
  resetUtteranceState();
  if (rafId) cancelAnimationFrame(rafId);
  const floatBuf = new Float32Array(analyser.fftSize);
  let speaking = false;
  let speechStartedAt = 0;
  let silenceMs = 0;

  const loop = () => {
    analyser.getFloatTimeDomainData(floatBuf);
    let sum = 0;
    for (let i = 0; i < floatBuf.length; i++) {
      const v = floatBuf[i];
      sum += v * v;
    }
    const rms = Math.sqrt(sum / floatBuf.length);
    const now = performance.now();

    if (!speaking) {
      if (rms >= RMS_START_THRESHOLD) {
        speaking = true;
        speechStartedAt = now;
        silenceMs = 0;
        startRecorder();
      }
    } else {
      const elapsed = now - speechStartedAt;

      if (rms < RMS_CONTINUE_THRESHOLD) {
        silenceMs += 16;
      } else {
        silenceMs = 0;
      }

      if (elapsed > MIN_SPEECH_MS && (silenceMs >= SILENCE_AFTER_SPEECH_MS || elapsed >= MAX_UTTERANCE_MS)) {
        stopRecorder();
        return;
      }
    }
    rafId = requestAnimationFrame(loop);
  };

  rafId = requestAnimationFrame(loop);
}

async function sendAnswerBlob(blob) {
  log("⏳ Transcribing...");
  const form = new FormData();
  form.append("question_index", String(questionIndex)); // compatibility
  form.append("session_id", sessionId);                 // NEW: session tracking
  form.append("audio", blob, "answer.webm");

  const res = await fetch("/api/answer", { method: "POST", body: form });
  const data = await res.json();
  if (data.error) {
    log("Error: " + data.error);
    return;
  }

  log("🗣 You: " + (data.transcript || "[no transcription]"));

  if (data.done) {
    await playInSequence([data.ack_tts_url, data.done_tts_url]);
    log("✅ Conversation completed. Thanks!");
    running = false;
    document.getElementById("stopBtn").disabled = true;
    document.getElementById("startBtn").disabled = false;
  } else {
    questionIndex = data.next_question_index;
    await playInSequence([data.ack_tts_url, data.next_question_tts_url]);
    log("🤖 " + data.next_question_text);
  }
}

document.getElementById("startBtn").addEventListener("click", async () => {
  document.getElementById("startBtn").disabled = true;
  document.getElementById("stopBtn").disabled = false;
  await startSurvey();
});

document.getElementById("stopBtn").addEventListener("click", () => {
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  document.getElementById("stopBtn").disabled = true;
  document.getElementById("startBtn").disabled = false;
  try {
    stopRecorder();
    if (audioContext && audioContext.state !== "closed") audioContext.close();
  } catch (e) {}
});
