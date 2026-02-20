from flask import Flask, request, send_file, render_template, jsonify
import edge_tts
import asyncio
from pydub import AudioSegment
import os
import uuid
import threading
import time

app = Flask(__name__)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# ===============================
# Chia nhỏ text cho truyện dài
# ===============================
def split_text(text, max_length=2500):
    parts = []
    while len(text) > max_length:
        split_at = text.rfind(" ", 0, max_length)
        if split_at == -1:
            split_at = max_length
        parts.append(text[:split_at])
        text = text[split_at:]
    parts.append(text)
    return parts

async def generate_tts(text, voice, filename):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def delete_later(path, delay=300):
    def delete():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=delete).start()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    text = request.form.get("text")
    voice = request.form.get("voice")
    speed = float(request.form.get("speed", 1.0))

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(TEMP_FOLDER, filename)

    parts = split_text(text)
    combined = AudioSegment.empty()

    for part in parts:
        temp_name = f"{uuid.uuid4()}.mp3"
        temp_path = os.path.join(TEMP_FOLDER, temp_name)

        asyncio.run(generate_tts(part, voice, temp_path))
        segment = AudioSegment.from_mp3(temp_path)
        combined += segment

        os.remove(temp_path)

    # chỉnh tốc độ
    combined = combined._spawn(
        combined.raw_data,
        overrides={"frame_rate": int(combined.frame_rate * speed)}
    ).set_frame_rate(combined.frame_rate)

    combined.export(filepath, format="mp3")

    delete_later(filepath, 300)

    return jsonify({
        "file": f"/download/{filename}",
        "duration": len(combined) / 1000
    })

@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join(TEMP_FOLDER, filename)
    return send_file(filepath)

if __name__ == "__main__":
    app.run()

