from flask import Flask, request, send_file
import edge_tts
import asyncio
import os
import uuid

app = Flask(__name__)

VOICES = {
    "hoaimy": "vi-VN-HoaiMyNeural",
    "namminh": "vi-VN-NamMinhNeural"
}

async def generate_tts(text, voice, rate, pitch, filename):
    communicate = edge_tts.Communicate(
        text,
        VOICES[voice],
        rate=rate,
        pitch=pitch
    )
    await communicate.save(filename)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        text = request.form.get("text", "")
        voice = request.form.get("voice", "hoaimy")
        rate = request.form.get("rate", "+0%")
        pitch = request.form.get("pitch", "+0Hz")

        # Nếu upload file
        if "file" in request.files and request.files["file"].filename != "":
            file = request.files["file"]
            text = file.read().decode("utf-8")

        if not text.strip():
            return "Vui lòng nhập văn bản hoặc upload file."

        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join("static", filename)

        if not os.path.exists("static"):
            os.makedirs("static")

        asyncio.run(generate_tts(text, voice, rate, pitch, filepath))

        return send_file(filepath, as_attachment=True)

    return """
<!DOCTYPE html>
<html>
<head>
<title>TTS Web Pro</title>
<style>
body {
    font-family: Arial;
    background: #f4f6f9;
    display: flex;
    justify-content: center;
}
.container {
    width: 800px;
    background: white;
    padding: 30px;
    margin-top: 40px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}
h1 {
    text-align: center;
}
textarea {
    width: 100%;
    height: 180px;
    padding: 10px;
    font-size: 15px;
}
input, select {
    width: 100%;
    padding: 10px;
    margin-top: 8px;
    margin-bottom: 15px;
}
button {
    width: 100%;
    padding: 15px;
    background: #4CAF50;
    color: white;
    border: none;
    font-size: 18px;
    border-radius: 8px;
    cursor: pointer;
}
button:hover {
    background: #45a049;
}
@media(max-width: 768px){
    .container{
        width: 95%;
    }
}
</style>
</head>
<body>

<div class="container">
<h1>🎙 TTS Web Pro</h1>

<form method="POST" enctype="multipart/form-data">

<label>Nhập văn bản (hoặc để trống nếu upload file):</label>
<textarea name="text" placeholder="Nhập nội dung..."></textarea>

<label>Hoặc upload file .txt:</label>
<input type="file" name="file">

<label>Chọn giọng:</label>
<select name="voice">
    <option value="hoaimy">Hoài My (Nữ)</option>
    <option value="namminh">Nam Minh (Nam)</option>
</select>

<label>Tốc độ (-50% đến +50%):</label>
<input type="text" name="rate" value="+0%">

<label>Cao độ (-50Hz đến +50Hz):</label>
<input type="text" name="pitch" value="+0Hz">

<button type="submit">🚀 Tạo MP3</button>

</form>
</div>

</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
