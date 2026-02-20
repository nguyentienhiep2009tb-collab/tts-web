from flask import Flask, render_template_string, request, send_file
import edge_tts
import asyncio
import os
import uuid

app = Flask(__name__)

if not os.path.exists("audio_files"):
    os.makedirs("audio_files")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TTS Pro Max</title>
    <style>
        body {
            font-family: Arial;
            max-width: 900px;
            margin: auto;
            padding: 20px;
            background: #f0f2f5;
        }
        textarea {
            width: 100%;
            height: 250px;
            padding: 10px;
        }
        select, input, button {
            padding: 10px;
            margin-top: 10px;
            width: 100%;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            font-size: 16px;
        }
        button:hover {
            background: #45a049;
        }
        .box {
            background: white;
            padding: 20px;
            border-radius: 8px;
        }
    </style>
</head>
<body>

<div class="box">
<h2>🎧 Tạo Truyện Audio MP3</h2>

<form method="post" enctype="multipart/form-data">

    <label>Nhập văn bản (hoặc để trống nếu upload file):</label>
    <textarea name="text"></textarea>

    <label>Hoặc upload file .txt:</label>
    <input type="file" name="file" accept=".txt">

    <label>Chọn giọng:</label>
    <select name="voice">
        <option value="vi-VN-HoaiMyNeural">Hoài My (Nữ)</option>
        <option value="vi-VN-NamMinhNeural">Nam Minh (Nam)</option>
    </select>

    <label>Tốc độ (-50% đến +50%)</label>
    <input type="text" name="rate" value="+0%">

    <label>Cao độ (-50Hz đến +50Hz)</label>
    <input type="text" name="pitch" value="+0Hz">

    <button type="submit">Tạo MP3</button>
</form>
</div>

</body>
</html>
"""

async def generate_audio(text, voice, rate, pitch, filename):
    chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]

    with open(filename, "wb") as f:
        for chunk in chunks:
            communicate = edge_tts.Communicate(
                chunk,
                voice,
                rate=rate,
                pitch=pitch
            )
            async for data in communicate.stream():
                if data["type"] == "audio":
                    f.write(data["data"])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        text = request.form.get("text", "")
        file = request.files.get("file")

        if file and file.filename.endswith(".txt"):
            text = file.read().decode("utf-8")

        if not text.strip():
            return "Không có nội dung!"

        voice = request.form["voice"]
        rate = request.form["rate"]
        pitch = request.form["pitch"]

        filename = os.path.join("audio_files", f"{uuid.uuid4()}.mp3")

        asyncio.run(generate_audio(text, voice, rate, pitch, filename))

        return send_file(filename, as_attachment=True)

    return render_template_string(HTML)

if __name__ == "__main__":

import os

app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
