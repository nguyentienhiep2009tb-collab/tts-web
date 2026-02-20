import os
import uuid
import asyncio
import threading
from flask import Flask, request, jsonify, send_file
import edge_tts

app = Flask(__name__)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)


# ====== CHIA TEXT DÀI ======
def split_text(text, max_length=4000):
    parts = []
    while len(text) > max_length:
        split_index = text.rfind(" ", 0, max_length)
        if split_index == -1:
            split_index = max_length
        parts.append(text[:split_index])
        text = text[split_index:]
    parts.append(text)
    return parts


# ====== TẠO TTS ======
async def generate_tts(text, voice, rate, pitch, output_file):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch
    )
    await communicate.save(output_file)


# ====== AUTO DELETE ======
def delete_later(filepath, delay):
    def delete():
        if os.path.exists(filepath):
            os.remove(filepath)
    timer = threading.Timer(delay, delete)
    timer.start()


# ====== API GENERATE ======
@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    text = data.get("text")
    voice = data.get("voice")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")

    parts = split_text(text, 4000)

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(TEMP_FOLDER, filename)

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

    delete_later(filepath, 3600)

    return jsonify({
        "file": f"/download/{filename}"
    })


@app.route("/download/<filename>")
def download(filename):
    filepath = os.path.join(TEMP_FOLDER, filename)
    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run()
