from flask import Flask, render_template, request, send_file, jsonify
import requests
import io
import os
import tempfile
import re
from pydub import AudioSegment

app = Flask(__name__)

# THAY KEY AZURE CỦA MÀY Ở ĐÂY (tạo Speech resource tier Free F0 trên Azure portal)
AZURE_KEY = "your_azure_speech_key_here"
AZURE_REGION = "southeastasia"  # Gần VN, latency thấp

CHUNK_SIZE = 8000  # Azure giới hạn ~10k chars/request, để an toàn

def split_text(text, max_length=CHUNK_SIZE):
    chunks = []
    current = ""
    # Chia theo câu để tự nhiên hơn
    sentences = re.split(r'(?<=[\.\!\?])\s+', text.strip())
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_length:
            current += sentence + " "
        else:
            if current:
                chunks.append(current.strip())
            current = sentence + " "
    if current:
        chunks.append(current.strip())
    return chunks if chunks else [text]

def generate_ssml(chunk, voice, rate_percent, pitch_percent):
    # rate_percent: -50 đến +50 → chuyển thành rate multiplier (0.5 → 1.5x)
    rate = 1.0 + (rate_percent / 100.0)
    # pitch_percent: -50 đến +50 → % thay đổi
    pitch = f"{pitch_percent:+.0f}%"

    # Làm ngọt ngào hơn: thêm break 150-250ms giữa câu, pitch + mặc định 15% nếu 0
    if pitch_percent == 0:
        pitch = "+15%"  # Na ná Ngọc Huyền (cao nhẹ, ngọt)

    ssml = f"""
    <speak version='1.0' xml:lang='vi-VN'>
        <voice name='{voice}'>
            <prosody rate='{rate}' pitch='{pitch}'>
                {chunk.replace('.', '. <break time="200ms"/> ')}
            </prosody>
        </voice>
    </speak>
    """
    return ssml.encode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    text = request.form.get('text', '').strip()
    voice = request.form.get('voice', 'vi-VN-HoaiMyNeural')
    rate = float(request.form.get('rate', 0))
    pitch = float(request.form.get('pitch', 0))

    if not text:
        return jsonify({"error": "Nhập văn bản đi mày!"}), 400

    music_file = request.files.get('music')
    music_path = None
    if music_file and music_file.filename.endswith('.mp3'):
        music_temp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        music_file.save(music_temp.name)
        music_path = music_temp.name

    chunks = split_text(text)
    audio_segments = []

    for chunk in chunks:
        ssml = generate_ssml(chunk, voice, rate, pitch)
        url = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            "User-Agent": "TTSWebPro"
        }
        resp = requests.post(url, data=ssml, headers=headers)
        if resp.status_code != 200:
            if music_path:
                os.unlink(music_path)
            return jsonify({"error": f"Lỗi Azure: {resp.text}"}), 500

        temp_mp3 = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_mp3.write(resp.content)
        temp_mp3.close()
        audio_segments.append(AudioSegment.from_mp3(temp_mp3.name))
        os.unlink(temp_mp3.name)

    # Ghép speech chunks
    combined_speech = sum(audio_segments, AudioSegment.empty())

    final_audio = combined_speech

    # Nếu có nhạc nền: overlay, giảm vol nhạc 60-70% để giọng rõ
    if music_path:
        try:
            bg_music = AudioSegment.from_mp3(music_path)
            # Loop nhạc nếu ngắn hơn speech
            if len(bg_music) < len(combined_speech):
                bg_music = bg_music * (len(combined_speech) // len(bg_music) + 1)
            bg_music = bg_music[:len(combined_speech)]
            # Giảm vol nhạc, fade in/out
            bg_music = bg_music - 18  # Giảm ~70% vol
            bg_music = bg_music.fade_in(3000).fade_out(4000)
            final_audio = combined_speech.overlay(bg_music)
        except Exception as e:
            print("Lỗi nhạc nền:", e)
        finally:
            os.unlink(music_path)

    # Lưu final
    output_path = "output.mp3"
    final_audio.export(output_path, format="mp3")

    # Trả URL tạm (hoặc base64 nếu muốn, nhưng send_file ổn hơn)
    # Để preview, tao trả file path tạm (trong production dùng static hoặc cloud)
    return jsonify({"file": "/static/output.mp3"})  # Cần tạo route static hoặc dùng send_file

# Để preview: thêm route serve file (dev only, production dùng Render static)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_file(filename)

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)  # Nếu cần
    app.run(host="0.0.0.0", port=10000, debug=True)
