from flask import Flask, render_template, request, jsonify, send_from_directory
from gtts import gTTS
import os
import tempfile
from pydub import AudioSegment

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    text = request.form.get('text', '').strip()
    rate = float(request.form.get('rate', 0))
    pitch = float(request.form.get('pitch', 0))  # Không dùng pitch vì gTTS không hỗ trợ, giữ input cho giao diện

    if not text:
        return jsonify({"error": "Nhập văn bản đi mày!"})

    # Chọn slow nếu rate âm (chậm hơn, nghe ngọt hơn)
    slow_mode = rate < 0

    # Tạo TTS bằng gTTS
    try:
        tts = gTTS(text=text, lang='vi', slow=slow_mode)
    except Exception as e:
        return jsonify({"error": f"Lỗi gTTS: {str(e)}"})

    # Lưu file tạm
    os.makedirs('static', exist_ok=True)
    speech_path = "static/speech.mp3"
    tts.save(speech_path)

    music_path = None
    music_file = request.files.get('music')
    if music_file and music_file.filename.endswith('.mp3'):
        temp_music = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        music_file.save(temp_music.name)
        music_path = temp_music.name

    final_path = "static/output.mp3"
    speech = AudioSegment.from_mp3(speech_path)

    if music_path:
        try:
            bg = AudioSegment.from_mp3(music_path)
            if len(bg) < len(speech):
                bg = bg * ((len(speech) // len(bg)) + 1)
            bg = bg[:len(speech)] - 18  # Giảm vol nhạc để giọng rõ
            bg = bg.fade_in(3000).fade_out(4000)
            combined = speech.overlay(bg)
        except Exception as e:
            print("Lỗi overlay nhạc:", e)
            combined = speech
        os.unlink(music_path)
    else:
        combined = speech

    combined.export(final_path, format="mp3")

    # Xóa file tạm speech
    os.unlink(speech_path)

    # Trả URL preview với timestamp tránh cache
    timestamp = str(os.path.getmtime(final_path))
    return jsonify({"file": f"/static/output.mp3?t={timestamp}"})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
