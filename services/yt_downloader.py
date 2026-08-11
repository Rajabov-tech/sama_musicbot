import requests

def download_media(url: str, is_audio: bool = False):
    """
    Cobalt API yordamida media havolasini olish (yt_dlp o'rniga).
    Eski kodlardagi result['success'], result['file_path'] formatini saqlab qoladi.
    """
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "downloadMode": "audio" if is_audio else "auto",
        "audioFormat": "mp3" if is_audio else None
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=25)
        data = response.json()
        
        if data.get("status") in ["tunnel", "stream", "redirect"]:
            media_url = data.get("url")
            title = data.get("filename", "Media")
            return {
                "success": True,
                "file_path": media_url, # Bu yerda to'g'ridan-to'g'ri URL qaytadi
                "title": title,
                "duration": 0
            }
        elif data.get("status") == "picker":
            picker_list = data.get("picker", [])
            if picker_list:
                media_url = picker_list[0].get("url")
                return {
                    "success": True,
                    "file_path": media_url,
                    "title": "Media",
                    "duration": 0
                }
                
    except Exception as e:
        print(f"Cobalt yt_downloader xatosi: {e}")
        
    return {
        "success": False, 
        "error": "Cobalt orqali havolani olib bo'lmadi yoki vaqt tugadi."
    }
