import asyncio
import os
from uuid import uuid4

EFFECTS = {
    "8d": "apulsator=hz=0.125",
    "bass": "bass=g=15",
    "concert": "aecho=0.8:0.9:1000:0.3",
    "radio": "highpass=f=200,lowpass=f=3000",
    "slow": "atempo=0.8",
    "echo": "aecho=0.8:0.9:500:0.3",
    "convert": "" 
}

async def apply_audio_effect(input_path: str, effect_key: str) -> str:
    if effect_key not in EFFECTS:
        raise ValueError("Noma'lum effekt!")

    if not os.path.exists("downloads"):
        os.makedirs("downloads", exist_ok=True)

    output_path = f"downloads/processed_{uuid4().hex}.mp3"
    filter_arg = EFFECTS[effect_key]

    cmd = ["ffmpeg", "-y", "-i", input_path]
    if filter_arg:
        cmd.extend(["-af", filter_arg])
    cmd.extend(["-c:a", "libmp3lame", "-q:a", "2", output_path])

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()

    if process.returncode == 0 and os.path.exists(output_path):
        return output_path
    else:
        error_msg = stderr.decode() if stderr else "Noma'lum FFmpeg xatoligi"
        print(f"FFmpeg Error: {error_msg}")
        raise Exception(f"FFmpeg xatoligi: {error_msg}")