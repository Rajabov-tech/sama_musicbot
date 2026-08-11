import os
import subprocess
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, "temp_stems")

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

async def separate_stems(input_path: str):
    try:
        cmd = [
            "demucs", "--two-stems=vocals", "--shifts=0", "-n", "htdemucs", 
            "-o", TEMP_DIR, input_path
        ]
        
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.wait()
        
        filename = os.path.basename(input_path).rsplit(".", 1)[0]
        output_folder = os.path.join(TEMP_DIR, "htdemucs", filename)
        
        wav_vocals = os.path.join(output_folder, "vocals.wav")
        wav_inst = os.path.join(output_folder, "no_vocals.wav")
        
        mp3_vocals = os.path.join(output_folder, "vocals.mp3")
        mp3_inst = os.path.join(output_folder, "instrumental.mp3")
        
        # FFmpeg yordamida WAV ni kichik hajmli MP3 ga o'tkazamiz (tezlik uchun)
        await convert_to_mp3(wav_vocals, mp3_vocals)
        await convert_to_mp3(wav_inst, mp3_inst)
        
        return mp3_vocals, mp3_inst
        
    except Exception as e:
        print(f"Error separating stems: {e}")
        return None, None

async def convert_to_mp3(input_wav, output_mp3):
    cmd = [
        "ffmpeg", "-y", "-i", input_wav, 
        "-b:a", "192k", output_mp3
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await proc.wait()