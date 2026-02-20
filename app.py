from flask import Flask, render_template, request, jsonify, send_file
import edge_tts
import asyncio
import os
import uuid
import threading
import time

app = Flask(__name__)
TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

def delete_later(path, delay=300):
    def remove():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=remove).start()

async def generate_tts(text, voice, rate, pitch, filename):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=f"{rate:+d}%",
        pitch=f"{pitch:+d}Hz"
    )
    await communicate.save(filename)

def split_text(text, max_length=4000):
    parts = []
    while len(text) > max_length:
        split_point = text.rfind('.', 0, max_length)
        if split_point == -1:
            split_point = max_length
        parts.append(text[:split_point+1])
        text = text[split_point+1:]
    parts.append(text)
    return parts

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    text = data["text"]
    voice = data["voice"]
    rate = int(data["rate"])
    pitch = int(data["pitch"])

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(TEMP_FOLDER, filename)

    parts = split_text(text)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for i, part in enumerate(parts):
        temp_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}.mp3")
        loop.run_until_complete(generate_tts(part, voice, rate, pitch, temp_path))

        if i == 0:
            os.rename(temp_path, filepath)
        else:
            with open(filepath, "ab") as main_file:
                with open(temp_path, "rb") as part_file:
                    main_file.write(part_file.read())
            os.remove(temp_path)

    delete_later(filepath, 300)

    return jsonify({"file": f"/download/{filename}"})

@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join(TEMP_FOLDER, filename)
    return send_file(filepath)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
