import os
import uuid
import asyncio
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment
import edge_tts

app = FastAPI()

OUTPUT_DIR = "outputs"
MUSIC_DIR = "music"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

# ===============================
# PRESET THEO THỂ LOẠI
# ===============================
GENRE_CONFIG = {
    "nguoc": {
        "music": "music/nguoc.mp3",
        "rate": "-5%",
        "pitch": "-3Hz"
    },
    "tongtai": {
        "music": "music/tongtai.mp3",
        "rate": "+3%",
        "pitch": "+0Hz"
    }
}

# ===============================
# TTS ĐỔI GIỌNG THEO TAG
# ===============================
async def generate_tts_dialogue(text, output_file, genre):

    lines = text.split("\n")
    combined = AudioSegment.empty()

    config = GENRE_CONFIG.get(genre, GENRE_CONFIG["nguoc"])
    rate = config["rate"]
    pitch = config["pitch"]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Nam:"):
            voice = "vi-VN-NamMinhNeural"
            content = line.replace("Nam:", "").strip()
        elif line.startswith("Nữ:"):
            voice = "vi-VN-HoaiMyNeural"
            content = line.replace("Nữ:", "").strip()
        else:
            voice = "vi-VN-HoaiMyNeural"
            content = line

        temp_file = f"{uuid.uuid4()}.mp3"

        communicate = edge_tts.Communicate(
            text=content,
            voice=voice,
            rate=rate,
            pitch=pitch
        )

        await communicate.save(temp_file)

        audio = AudioSegment.from_file(temp_file)
        combined += audio
        os.remove(temp_file)

    combined.export(output_file, format="mp3")


# ===============================
# GHÉP NHẠC NỀN
# ===============================
def add_background_music(voice_file, music_file, output_file):

    voice = AudioSegment.from_file(voice_file)
    music = AudioSegment.from_file(music_file)

    if len(music) < len(voice):
        times = len(voice) // len(music) + 1
        music = music * times

    music = music[:len(voice)]
    music = music - 20

    music = music.fade_in(3000).fade_out(5000)

    final = voice.overlay(music)
    final.export(output_file, format="mp3")


# ===============================
# ROUTE
# ===============================
@app.post("/generate")
async def generate(
    text: str = Form(""),
    genre: str = Form("nguoc")
):

    file_id = str(uuid.uuid4())
    voice_path = os.path.join(OUTPUT_DIR, f"{file_id}_voice.mp3")
    final_path = os.path.join(OUTPUT_DIR, f"{file_id}_final.mp3")

    await generate_tts_dialogue(text, voice_path, genre)

    music_path = GENRE_CONFIG[genre]["music"]

    if os.path.exists(music_path):
        add_background_music(voice_path, music_path, final_path)
        os.remove(voice_path)
        return FileResponse(final_path, media_type="audio/mpeg")

    return FileResponse(voice_path, media_type="audio/mpeg")
