from flask import Flask, render_template, request, send_file
import os
from gtts import gTTS

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    text = request.form['text']
    voice = request.form['voice']

    filename = "output.mp3"

    tts = gTTS(text=text, lang='vi')
    tts.save(filename)

    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
