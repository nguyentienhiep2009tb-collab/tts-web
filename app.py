from flask import Flask, render_template, request, jsonify, send_file
import edge_tts
import asyncio
import os
import uuid
import threading
import time
from pydub import AudioSegment

app = Flask(__name__)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

def delete_later(path, delay=300):
    def remove():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=remove).start()

def split_text(text, max_length=4000):
    parts = []
    while len(text) > max_length:
        split_point = text.rfind(".", 0, max_length)
        if split_point == -1:
            split_point = max_length
        parts.append(text[:split_point+1])
        text = text[split_point+1:]
    parts.append(text)
    return parts

async def generate_tts(text, voice, rate, pitch, filename):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=f"{rate:+d}%",
        pitch=f"{pitch:+d}Hz"
    )
    await communicate.save(filename)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    text = request.form["text"]
    voice = request.form["voice"]
    rate = int(request.form["rate"])
    pitch = int(request.form["pitch"])
    music_file = request.files.get("music")

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(TEMP_FOLDER, filename)

    parts = split_text(text)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tts_files = []
    for part in parts:
        part_file = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}.mp3")
        loop.run_until_complete(generate_tts(part, voice, rate, pitch, part_file))
        tts_files.append(part_file)

    combined_voice = AudioSegment.empty()
    for file in tts_files:
        combined_voice += AudioSegment.from_mp3(file)
        os.remove(file)

    if music_file:
        music_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}_music.mp3")
        music_file.save(music_path)

        music = AudioSegment.from_mp3(music_path)
        music = music - 15

        if len(music) < len(combined_voice):
            repeat_times = int(len(combined_voice) / len(music)) + 1
            music = music * repeat_times

        music = music[:len(combined_voice)]
        final_audio = combined_voice.overlay(music)

        os.remove(music_path)
    else:
        final_audio = combined_voice

    final_audio.export(filepath, format="mp3")

    delete_later(filepath)

    return jsonify({"file": f"/download/{filename}"})

@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(TEMP_FOLDER, filename), as_attachment=False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
