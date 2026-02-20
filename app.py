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
# ===============================from flask import Flask, request, jsonify, send_file, render_template
import edge_tts
import asyncio
import os
import uuid
import threading
import time

app = Flask(__name__)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

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

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(TEMP_FOLDER, filename)

    parts = split_text(text)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for i, part in enumerate(parts):
        temp_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}.mp3")
        loop.run_until_complete(generate_tts(part, voice, temp_path))

        if i == 0:
            os.rename(temp_path, filepath)
        else:
            with open(filepath, "ab") as main_file:
                with open(temp_path, "rb") as part_file:
                    main_file.write(part_file.read())
            os.remove(temp_path)

    delete_later(filepath, 300)

    return jsonify({
        "file": f"/download/{filename}"
    })

@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join(TEMP_FOLDER, filename)
    return send_file(filepath)

if __name__ == "__main__":
    app.run()
