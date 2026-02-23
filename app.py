from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
import os
import tempfile
import re
from pydub import AudioSegment

app = Flask(__name__)

AZURE_KEY = os.environ.get('AZURE_KEY')
if not AZURE_KEY:
    raise ValueError("Thiếu AZURE_KEY trong environment variables!")

AZURE_REGION = "southeastasia"

CHUNK_SIZE = 8000

def split_text(text, max_length=CHUNK_SIZE):
    chunks = []
    current = ""
    sentences = re.split(r'(?<=[\.\!\?])\s+', text.strip())
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_length:
            current += sentence + " "
        else:
            if current:
                chunks.append(current.strip())
            current = sentence + " "
    if current:
        chunks.append(current.strip())
    return chunks if chunks else [text]

def generate_ssml(chunk, voice, rate_percent, pitch_percent):
    rate = max(0.5, min(2.0, 1.0 + (rate_percent / 100.0)))
    pitch = f"{pitch_percent:+.0f}%"
    if pitch_percent == 0:
        pitch = "+15%"

    ssml = f"""
    <speak version='1.0' xml:lang='vi-VN'>
        <voice name='{voice}'>
            <prosody rate='{rate}' pitch='{pitch}'>
                {chunk.replace('.', '. <break time="200ms"/> ')}
            </prosody>
        </voice>
    </speak>
    """
    return ssml.encode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    text = request.form.get('text', '').strip()
    voice = request.form.get('voice', 'vi-VN-HoaiMyNeural')
    rate = float(request.form.get('rate', 0))
    pitch = float(request.form.get('pitch', 0))

    if not text:
        return jsonify({"error": "Nhập văn bản đi mày!"})

    music_path = None
    music_file = request.files.get('music')
    if music_file and music_file.filename.endswith('.mp3'):
        temp_music = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        music_file.save(temp_music.name)
        music_path = temp_music.name

    chunks = split_text(text)
    audio_segments = []

    for chunk in chunks:
        ssml = generate_ssml(chunk, voice, rate, pitch)
        url = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
        }
        resp = requests.post(url, data=ssml, headers=headers)
        if resp.status_code != 200:
            if music_path:
                os.unlink(music_path)
            return jsonify({"error": f"Lỗi Azure: {resp.text[:200]}"})

        temp_mp3 = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_mp3.write(resp.content)
        temp_mp3.close()
        audio_segments.append(AudioSegment.from_mp3(temp_mp3.name))
        os.unlink(temp_mp3.name)

    combined = sum(audio_segments, AudioSegment.empty())

    if music_path:
        try:
            bg = AudioSegment.from_mp3(music_path)
            if len(bg) < len(combined):
                bg = bg * ((len(combined) // len(bg)) + 1)
            bg = bg[:len(combined)] - 18
            bg = bg.fade_in(3000).fade_out(4000)
            combined = combined.overlay(bg)
        except:
            pass
        os.unlink(music_path)

    os.makedirs('static', exist_ok=True)
    output_path = "static/output.mp3"
    combined.export(output_path, format="mp3")

    timestamp = str(os.path.getmtime(output_path))
    return jsonify({"file": f"/static/output.mp3?t={timestamp}"})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
