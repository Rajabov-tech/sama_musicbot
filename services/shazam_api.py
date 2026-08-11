import os
from shazamio import Shazam

async def recognize_audio(file_path: str) -> dict:
    """
    Shazamio orqali audio faylni tekshiradi.
    Natija sifatida qo'shiq nomi, ijrochi va rasm (cover) qaytaradi.
    """
    shazam = Shazam()
    try:
        out = await shazam.recognize(file_path)
        if 'track' in out:
            track = out['track']
            title = track.get('title', 'Noma\'lum musiqa')
            artist = track.get('subtitle', 'Noma\'lum ijrochi')
            cover_url = track.get('images', {}).get('coverart', '')
            shazam_id = track.get('key', '')
            
            return {
                "success": True,
                "title": title,
                "artist": artist,
                "cover": cover_url,
                "shazam_id": shazam_id
            }
        else:
            return {"success": False, "error": "Musiqa topilmadi"}
    except Exception as e:
        return {"success": False, "error": str(e)}