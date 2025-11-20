import os
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .llm import LLMClient
from .session import LevelCheckSession


app = FastAPI(title="Speak Buddy C Web")


class StartResponse(BaseModel):
    session_id: str
    question: str
    level_tag: Optional[str] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None


class RespondPayload(BaseModel):
    session_id: str
    transcript: str


class RespondResponse(BaseModel):
    next_question: str
    completed: bool
    summary: Optional[str] = None
    level_tag: str
    confidence: float
    rationale: str


def build_client() -> LLMClient:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return LLMClient(api_key=api_key, model=model)


_sessions: Dict[str, LevelCheckSession] = {}


@app.post("/api/level-check/start", response_model=StartResponse)
def start_level_check() -> StartResponse:
    session_id = str(uuid.uuid4())
    session = LevelCheckSession(build_client())
    question = session.start()
    _sessions[session_id] = session
    result = session.state.latest_result
    return StartResponse(
        session_id=session_id,
        question=question,
        level_tag=result.level_tag if result else None,
        confidence=result.confidence if result else None,
        rationale=result.rationale if result else None,
    )


@app.post("/api/level-check/respond", response_model=RespondResponse)
def respond(payload: RespondPayload) -> RespondResponse:
    if payload.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Start a new level check.")

    session = _sessions[payload.session_id]
    result = session.process_response(payload.transcript)
    summary = session.summary() if result["completed"] else None
    if result["completed"]:
        _sessions.pop(payload.session_id, None)
    return RespondResponse(
        next_question=result["next_question"],
        completed=result["completed"],
        summary=summary,
        level_tag=result["level_tag"],
        confidence=result["confidence"],
        rationale=result["rationale"],
    )


HTML_PAGE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Speak Buddy C - Voice Coach</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 0; background: #0b1021; color: #f5f7ff; }
    header { background: #1a2140; padding: 18px 24px; box-shadow: 0 2px 6px rgba(0,0,0,0.3); }
    h1 { margin: 0; font-size: 22px; }
    main { padding: 24px; max-width: 840px; margin: auto; }
    section { background: #121733; border: 1px solid #1f2a4d; border-radius: 14px; padding: 20px; margin-bottom: 18px; }
    .question { font-size: 20px; margin-bottom: 12px; }
    .pill { display: inline-block; padding: 6px 10px; border-radius: 999px; background: #1f2a4d; color: #c2c8ff; font-size: 12px; margin-right: 6px; }
    button { background: linear-gradient(135deg, #4f70ff, #7f5af0); color: white; border: none; padding: 12px 18px; border-radius: 12px; font-weight: 700; cursor: pointer; box-shadow: 0 6px 12px rgba(0,0,0,0.25); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .recording { background: #ee4266; }
    #transcript { min-height: 60px; padding: 12px; border-radius: 10px; background: #0d1328; border: 1px dashed #2f3a63; margin-top: 8px; white-space: pre-wrap; }
    .chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
    .status { font-size: 14px; color: #a9b1e1; }
    #feedback { margin-top: 12px; }
    #feedback strong { color: #f3c969; }
    .footer { font-size: 13px; color: #7c86b3; text-align: center; padding: 12px 0 24px; }
  </style>
</head>
<body>
  <header>
    <h1>Speak Buddy C — Voice-first Level Check</h1>
    <div class=\"status\">Live mic transcript → LLM feedback → Next question (max 5 turns)</div>
  </header>
  <main>
    <section>
      <div class=\"question\" id=\"question\">Loading your first question...</div>
      <div class=\"chips\">
        <span class=\"pill\" id=\"level-pill\">Level: --</span>
        <span class=\"pill\" id=\"confidence-pill\">Confidence: --</span>
      </div>
    </section>

    <section>
      <div class=\"status\" id=\"mic-status\">Mic idle. Click record and speak naturally.</div>
      <button id=\"record-btn\" disabled>Start recording</button>
      <div id=\"transcript\">Transcript will appear here.</div>
      <div id=\"feedback\"></div>
    </section>

    <section>
      <div class=\"status\">If your browser blocks speech capture, type below and submit manually.</div>
      <textarea id=\"manual-input\" rows=\"3\" style=\"width:100%; border-radius:10px; border:1px solid #2f3a63; background:#0d1328; color:#f5f7ff; padding:10px;\" placeholder=\"Type your answer and press send\"></textarea>
      <div style=\"margin-top:8px; display:flex; gap:10px;\">
        <button id=\"send-btn\">Send typed answer</button>
        <button id=\"restart-btn\" style=\"background:#22375f;\">Restart level check</button>
      </div>
    </section>

    <div class=\"footer\">Browser speech recognition stays on-device. Only finalized text is sent to the coach API.</div>
  </main>

  <script>
    let sessionId = null;
    let recognition = null;
    let isRecording = false;
    let pendingTranscript = '';

    async function startSession() {
      toggleButtons(false);
      const res = await fetch('/api/level-check/start', { method: 'POST' });
      const data = await res.json();
      sessionId = data.session_id;
      updateQuestion(data.question);
      updateMeta(data.level_tag, data.confidence, data.rationale);
      toggleButtons(true);
      initSpeech();
    }

    function updateQuestion(text) {
      document.getElementById('question').textContent = text;
      document.getElementById('transcript').textContent = 'Transcript will appear here.';
      document.getElementById('feedback').textContent = '';
    }

    function updateMeta(level, confidence, rationale) {
      const levelEl = document.getElementById('level-pill');
      const confEl = document.getElementById('confidence-pill');
      levelEl.textContent = level ? `Level: ${level}` : 'Level: --';
      confEl.textContent = confidence !== null && confidence !== undefined ? `Confidence: ${(confidence * 100).toFixed(0)}%` : 'Confidence: --';
      if (rationale) {
        document.getElementById('feedback').innerHTML = `<strong>Coach note:</strong> ${rationale}`;
      }
    }

    function toggleButtons(enabled) {
      document.getElementById('record-btn').disabled = !enabled;
      document.getElementById('send-btn').disabled = !enabled;
    }

    function initSpeech() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        document.getElementById('mic-status').textContent = 'Speech recognition not supported. Use the text box instead.';
        return;
      }
      recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onstart = () => {
        isRecording = true;
        pendingTranscript = '';
        document.getElementById('record-btn').textContent = 'Stop recording';
        document.getElementById('record-btn').classList.add('recording');
        document.getElementById('mic-status').textContent = 'Listening... speak freely.';
      };

      recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            pendingTranscript += transcript + ' ';
          } else {
            interim += transcript;
          }
        }
        document.getElementById('transcript').textContent = (pendingTranscript + interim).trim();
      };

      recognition.onend = () => {
        if (isRecording) {
          submitTranscript((pendingTranscript || '').trim());
        }
        isRecording = false;
        document.getElementById('record-btn').textContent = 'Start recording';
        document.getElementById('record-btn').classList.remove('recording');
        document.getElementById('mic-status').textContent = 'Mic idle. Click record and speak naturally.';
      };

      recognition.onerror = () => {
        document.getElementById('mic-status').textContent = 'Mic error. Try again or type your answer.';
        isRecording = false;
        document.getElementById('record-btn').textContent = 'Start recording';
        document.getElementById('record-btn').classList.remove('recording');
      };

      document.getElementById('record-btn').onclick = () => {
        if (!recognition) return;
        if (isRecording) {
          recognition.stop();
        } else {
          recognition.start();
        }
      };
    }

    async function submitTranscript(text) {
      if (!text) {
        document.getElementById('mic-status').textContent = 'Please say or type a response before sending.';
        return;
      }
      toggleButtons(false);
      document.getElementById('mic-status').textContent = 'Sending to coach...';
      const res = await fetch('/api/level-check/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, transcript: text })
      });

      if (!res.ok) {
        document.getElementById('mic-status').textContent = 'Session expired. Restarting...';
        startSession();
        return;
      }

      const data = await res.json();
      updateQuestion(data.next_question);
      updateMeta(data.level_tag, data.confidence, data.rationale);
      if (data.summary) {
        document.getElementById('feedback').innerHTML = `<strong>Summary:</strong> ${data.summary}`;
        document.getElementById('mic-status').textContent = 'Session completed. Restart to try again.';
        toggleButtons(false);
      } else {
        document.getElementById('mic-status').textContent = 'Ready for the next question. Record when ready.';
        toggleButtons(true);
      }
      pendingTranscript = '';
    }

    document.getElementById('send-btn').onclick = () => {
      const text = document.getElementById('manual-input').value.trim();
      submitTranscript(text);
    };

    document.getElementById('restart-btn').onclick = () => {
      startSession();
    };

    startSession();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(content=HTML_PAGE)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
