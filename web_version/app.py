"""
StudyPal Web Server — wraps the desktop engine (src/) as a mobile-friendly API.
Run:  python web_version/app.py
Then: http://localhost:5000  (or http://<your-lan-ip>:5000 from your phone)
"""

import os
import sys
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

# --- import the desktop engine, one source of truth -----------------------
ROOT = Path(__file__).resolve().parent.parent   # ~/mystudy
sys.path.insert(0, str(ROOT / "src"))            # so "from engine.tts import ..." works

from engine.tts import TTSManager                # your fixed TTSManager
from engine.document import load_document        # TXT/PDF/DOCX

# STT / translator — adjust import paths if yours differ
try:
    from stt.whisper_engine import WhisperEngine
    _whisper = WhisperEngine()
    _HAS_STT = True
except Exception as e:
    print(f"[warn] STT not available: {e}")
    _whisper = None
    _HAS_STT = False

try:
    from stt.translator import Translator
    _translator = Translator()
    _HAS_TRANSLATE = True
except Exception as e:
    print(f"[warn] Translator not available: {e}")
    _translator = None
    _HAS_TRANSLATE = False

_tts = TTSManager()

# --- flask app ------------------------------------------------------------
STATIC_DIR = Path(__file__).parent / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
CORS(app)

# 100 MB upload cap
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# =========================================================================
#  Static
# =========================================================================
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


# =========================================================================
#  Voices
# =========================================================================
@app.get("/api/voices")
def api_voices():
    try:
        voices = _tts.get_voice_list()
        return jsonify({
            "voices": voices,
            "current": _tts.current_voice,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================================
#  Document extract (TXT / PDF / DOCX)
# =========================================================================
@app.post("/api/extract")
def api_extract():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "empty filename"}), 400

    suffix = Path(f.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        text = load_document(tmp_path)
        return jsonify({"success": True, "text": text, "filename": f.filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# =========================================================================
#  Transcribe (STT)
# =========================================================================
@app.post("/api/transcribe")
def api_transcribe():
    if not _HAS_STT:
        return jsonify({"error": "STT engine not available on this server"}), 503
    if "file" not in request.files:
        return jsonify({"error": "no audio file"}), 400

    f = request.files["file"]
    suffix = Path(f.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = _whisper.transcribe(tmp_path)
        # Normalize shape — adjust to whatever WhisperEngine returns
        if isinstance(result, dict):
            return jsonify({
                "success": True,
                "transcript": result.get("text") or result.get("transcript", ""),
                "language": result.get("language"),
                "segments": result.get("segments", []),
            })
        return jsonify({"success": True, "transcript": str(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# =========================================================================
#  Translate
# =========================================================================
@app.post("/api/translate")
def api_translate():
    if not _HAS_TRANSLATE:
        return jsonify({"error": "Translator not available"}), 503
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    target = (data.get("target") or "").strip()
    source = (data.get("source") or "auto").strip()
    if not text or not target:
        return jsonify({"error": "text and target are required"}), 400

    try:
        # Adjust to whatever Translator.translate signature yours has
        translated = _translator.translate(text, target, source=source)
        return jsonify({"success": True, "translated": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================================
#  TTS  — returns a WAV file
# =========================================================================
@app.post("/api/tts")
def api_tts():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = data.get("voice")
    speed = float(data.get("speed", 1.0))

    if not text:
        return jsonify({"error": "text is required"}), 400
    if len(text) > 20000:
        return jsonify({"error": "text too long (20000 chars max)"}), 400

    try:
        if voice:
            _tts.set_voice(voice)
        audio, sr = _tts.generate_audio(text, speed)

        # Write to a temp WAV and stream it back
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".wav", dir=str(Path(__file__).parent / "outputs")
        )
        tmp.close()
        import soundfile as sf
        sf.write(tmp.name, audio, sr)

        return send_file(
            tmp.name,
            mimetype="audio/wav",
            as_attachment=False,
            download_name="studypal.wav",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================================
if __name__ == "__main__":
    print(f"StudyPal Web → http://0.0.0.0:5000  (static: {STATIC_DIR})")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
