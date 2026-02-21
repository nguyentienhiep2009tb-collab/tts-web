import os
import asyncio
from flask import Flask, render_template, request, send_file
import edge_tts

app = Flask(__name__)

OUTPUT_FILE = "output.mp3"

async def generate_tts(text):
    communicate = edge_tts.Communicate(text, "vi-VN-HoaiMyNeural")
    await communicate.save(OUTPUT_FILE)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        text = request.form.get("text")
        if text:
            asyncio.run(generate_tts(text))
            return send_file(OUTPUT_FILE, as_attachment=True)
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
