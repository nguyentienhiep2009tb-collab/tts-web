from flask import Flask, request, send_file, render_template
import edge_tts
import asyncio
import os
import uuid

app = Flask(__name__)

VOICE = "vi-VN-HoaiMyNeural"

async def generate_tts(text, filename):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(filename)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        text = request.form["text"]

        if not text.strip():
            return "Vui lòng nhập văn bản."

        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join("static", filename)

        if not os.path.exists("static"):
            os.makedirs("static")

        asyncio.run(generate_tts(text, filepath))

        return send_file(filepath, as_attachment=True)

    return '''
        <h2>TTS Web - Chuyển văn bản thành MP3</h2>
        <form method="POST">
            <textarea name="text" rows="10" cols="50" placeholder="Nhập văn bản..."></textarea><br><br>
            <button type="submit">Tạo file MP3</button>
        </form>
    '''

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
