import asyncio
import yt_dlp
import os
from shazamio import Shazam

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

cookie_path = os.path.join(BASE_DIR, 'cookies.txt')

def sanitize_url(url: str) -> str:
    if "shorts/" in url:
        url = url.replace("shorts/", "watch?v=")
    if "watch?v=" in url:
        try:
            parts = url.split("watch?v=")
            if len(parts) > 1:
                v_id = parts[1].split("&")[0]
                if len(v_id) < 11:
                    # Havola qisqartirib yuborilgan bo'lsa, qidiruvga aylantiramiz
                    return f"ytsearch1:{url}"
        except Exception:
            pass
    return url

def run_ytdlp_extract_sample(url: str) -> str:
    target_url = sanitize_url(url)

    options = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_PATH}/sample_%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
    }
    
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(target_url, download=True)
        if 'entries' in info:
            entries = info['entries']
            if entries:
                info = entries[0]
            else:
                raise Exception("Havola bo'yicha media topilmadi (entries bo'sh).")
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        return base + ".mp3"

async def recognize_and_download(url: str, is_audio: bool = False) -> dict:
    def _process():
        try:
            current_url = sanitize_url(url)

            song_query = None
            if is_audio:
                print("🔍 Shazam orqali musiqa aniqlanmoqda...")
                try:
                    sample_path = run_ytdlp_extract_sample(current_url)
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    shazam = Shazam()
                    shazam_result = loop.run_until_complete(shazam.recognize(sample_path))
                    loop.close()

                    if os.path.exists(sample_path):
                        os.remove(sample_path)

                    if isinstance(shazam_result, dict) and 'track' in shazam_result:
                        track_info = shazam_result['track']
                        title = track_info.get('title')
                        artist = track_info.get('subtitle')
                        if title and artist:
                            song_query = f"{artist} - {title}"
                            print(f"✅ Musiqa topildi: {song_query}")
                except Exception as shazam_err:
                    print(f"⚠️ Shazam ishlamadi, to'g'ridan-to'g'ri yuklab olinmoqda: {shazam_err}")

            if song_query:
                search_options = {
                    'format': 'best',
                    'outtmpl': f'{DOWNLOAD_PATH}/%(id)s.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True,
                    'no_warnings': True,
                    'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
                }
                search_query_str = f"ytsearch1:{song_query} official audio"
                with yt_dlp.YoutubeDL(search_options) as ydl:
                    search_res = ydl.extract_info(search_query_str, download=True)
                    if 'entries' in search_res:
                        entries = search_res['entries']
                        if entries:
                            search_res = entries[0]
                        else:
                            raise Exception("Qidiruv natijasi bo'sh qaytdi.")
                    filename = ydl.prepare_filename(search_res)
                    base, _ = os.path.splitext(filename)
                    final_path = base + ".mp3"
                    
                    return {
                        "success": True,
                        "title": song_query,
                        "file_path": final_path,
                        "duration": search_res.get("duration", 0)
                    }

            options = {
                'format': 'best',
                'outtmpl': f'{DOWNLOAD_PATH}/%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
            }
            if is_audio:
                options['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(current_url, download=True)
                if 'entries' in info:
                    entries = info['entries']
                    if entries:
                        info = entries[0]
                    else:
                        raise Exception("Media topilmadi.")
                filename = ydl.prepare_filename(info)
                
                if is_audio:
                    base, _ = os.path.splitext(filename)
                    file_path = base + ".mp3"
                else:
                    file_path = filename

                return {
                    "success": True,
                    "title": info.get("title", "Musiqa / Video"),
                    "file_path": file_path,
                    "duration": info.get("duration", 0)
                }

        except Exception as e:
            print(f"❌ YUKLASHDA XATOLIK YUZ BERDI: {str(e)}")
            return {"success": False, "error": str(e)}

    return await asyncio.to_thread(_process)

async def download_media(url: str, is_audio: bool = False) -> dict:
    return await recognize_and_download(url, is_audio)