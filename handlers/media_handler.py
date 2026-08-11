import os
import aiosqlite
import asyncio
import yt_dlp
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import yt_downloader, stem_separator
import database.db as db

AUDIO_CAPTION = "@SAMA_Musicbot orqali musiqalarni oson toping!"
VIDEO_CAPTION = "@SAMA_Musicbot orqali videolarni oson yuklab oling!"

router = Router()

URL_MAP = {}

class SearchState(StatesGroup):
    waiting_for_selection = State()

def extract_yt_id(url: str) -> str:
    if not url:
        return "media"
    if "v=" in url:
        parts = url.split("v=")
        if len(parts) > 1:
            return parts[1].split("&")[0]
    elif "youtu.be/" in url:
        parts = url.split("youtu.be/")
        if len(parts) > 1:
            return parts[1].split("?")[0]
    
    uid = str(abs(hash(url)) % (10 ** 8))
    URL_MAP[uid] = url
    return uid

def get_stem_choice_kb(video_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎤 Vokal", callback_data=f"stem_v_{video_id}"),
            InlineKeyboardButton(text="🎹 Minusovka", callback_data=f"stem_i_{video_id}")
        ]
    ])

def get_main_audio_kb(video_url: str = ""):
    yt_id = extract_yt_id(video_url)
    URL_MAP[str(yt_id)] = video_url
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎙 Vokal / Minusovka", callback_data=f"stem_menu_{yt_id}")
        ],
        [
            InlineKeyboardButton(text="🎛 Effekt", callback_data="eff_menu"),
            InlineKeyboardButton(text="🎵 Top Music", callback_data="top_music")
        ],
        [
            InlineKeyboardButton(text="⭐ VIP Statusim", callback_data="check_vip")
        ],
        [
            InlineKeyboardButton(text="➕ Guruhga qoʻshish", url="t.me/SAMA_Musicbot?startgroup=true")
        ]
    ])

def get_main_video_kb(video_url: str = ""):
    yt_id = extract_yt_id(video_url)
    URL_MAP[str(yt_id)] = video_url
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 Musiqaga aylantirish", callback_data=f"conv_audio_{yt_id}")
        ],
        [
            InlineKeyboardButton(text="🎵 Top Music", callback_data="top_music"),
            InlineKeyboardButton(text="⭐ VIP Statusim", callback_data="check_vip")
        ],
        [
            InlineKeyboardButton(text="➕ Guruhga qoʻshish", url="t.me/SAMA_Musicbot?startgroup=true")
        ]
    ])

async def check_user_subscription(bot: Bot, user_id: int) -> list:
    if await db.check_user_vip(user_id):
        return []
        
    channels = await db.get_channels()
    unsubscribed_channels = []
    for ch_id, name, c_type in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ['left', 'kicked']: 
                unsubscribed_channels.append({"id": ch_id, "name": name})
        except: 
            pass
    return unsubscribed_channels

@router.message(F.text == "/vip")
async def vip_status_handler(message: Message):
    user_id = message.from_user.id
    is_vip = await db.check_user_vip(user_id)
    if is_vip:
        await message.answer("🌟 **Sizda VIP status mavjud!** Barcha cheklovlar olib tashlangan.")
    else:
        await message.answer("👤 **Siz Oddiy foydalanuvchisiz.** VIP status uchun adminga murojaat qiling.")

@router.callback_query(F.data == "check_vip")
async def check_vip_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_vip = await db.check_user_vip(user_id)
    text = "🌟 Sizda VIP status mavjud!" if is_vip else "👤 Siz Oddiy foydalanuvchisiz. Admin: @SamariddinRajabov"
    await callback.answer(text, show_alert=True)

def get_subscription_kb(unsubscribed_list):
    builder = InlineKeyboardBuilder()
    for ch in unsubscribed_list:
        ch_username = ch["id"].replace("@", "")
        builder.button(text=f"📢 {ch['name']}", url=f"https://t.me/{ch_username}")
    builder.button(text="✅ Obunani tekshirish", callback_data="check_sub")
    builder.adjust(1)
    return builder.as_markup()

def get_search_kb(page: int = 1):
    builder = InlineKeyboardBuilder()
    start_idx = 0 if page == 1 else 10
    end_idx = 10 if page == 1 else 20
    for i in range(start_idx, end_idx):
        builder.button(text=str(i + 1), callback_data=f"sel_{i}")
    builder.adjust(5, 5)
    nav_builder = InlineKeyboardBuilder()
    if page == 1: nav_builder.button(text="➡️ 11-20 variantlar", callback_data="page_2")
    else: nav_builder.button(text="⬅️ 1-10 variantlar", callback_data="page_1")
    builder.attach(nav_builder)
    return builder.as_markup()

# --- LINK KELGANDA (TEZKOR VIDEO KESHLASH VA YUKLASH) ---
@router.message(F.text.contains("http://") | F.text.contains("https://"))
async def handle_url(message: Message, state: FSMContext):
    await state.clear()
    url = message.text.strip()
    yt_id = extract_yt_id(url)
    URL_MAP[str(yt_id)] = url
    
    # 1. Video keshini tekshirish (0.1 soniyada yuborish)
    cached_data = await db.get_cached_media(url)
    if cached_data:
        file_id, title = cached_data
        await message.answer_video(video=file_id, caption=VIDEO_CAPTION, reply_markup=get_main_video_kb(url))
        return

    wait_msg = await message.answer("⏳ Tayyorlanmoqda...")
    result = await yt_downloader.download_media(url, is_audio=False)

    if result["success"]:
        file_path = result["file_path"]
        title = result.get("title", "Video")
        duration = result.get("duration", 0)
        
        sent_msg = await message.answer_video(
            video=FSInputFile(file_path),
            caption=VIDEO_CAPTION,
            duration=int(duration) if duration else None,
            reply_markup=get_main_video_kb(url)
        )
        # Videoni toza url bo'yicha keshga saqlaymiz
        await db.save_media_cache(url, sent_msg.video.file_id, title, "video")
        
        try: await wait_msg.delete()
        except: pass

        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        try: await wait_msg.delete()
        except: pass
        await message.answer(f"❌ Xatolik yuz berdi: {result.get('error')}")

# --- VIDEONI MUSIQAGA AYLANTIRISH ---
@router.callback_query(F.data.startswith("conv_audio_"))
async def convert_video_to_audio(callback: CallbackQuery):
    yt_id = callback.data.split("_")[2]
    url = URL_MAP.get(str(yt_id))
    
    if not url:
        if len(str(yt_id)) == 11:
            url = f"https://www.youtube.com/watch?v={yt_id}"
        else:
            await callback.answer("❌ Havola topilmadi. Qaytadan yuboring.", show_alert=True)
            return

    audio_cache_key = f"audio_{url}"

    # Musiqa keshini tekshirish
    cached_data = await db.get_cached_media(audio_cache_key)
    if cached_data:
        file_id, title = cached_data
        await callback.message.answer_audio(
            audio=file_id,
            title=title,
            caption=AUDIO_CAPTION,
            reply_markup=get_main_audio_kb(url)
        )
        await callback.answer()
        return

    await callback.answer("🎵 Musiqaga o'tkazilmoqda...")
    wait_msg = await callback.message.answer("⏳ Tayyorlanmoqda...")

    result = await yt_downloader.download_media(url, is_audio=True)

    if result["success"]:
        title = result.get("title", "Musiqa")
        duration = result.get("duration", 0)
        sent_msg = await callback.message.answer_audio(
            audio=FSInputFile(result["file_path"]),
            title=title,
            caption=AUDIO_CAPTION,
            duration=int(duration) if duration else None,
            reply_markup=get_main_audio_kb(url)
        )
        # Musiqani alohida kesh kaliti bilan saqlaymiz (videoga tegilmaydi)
        await db.save_media_cache(audio_cache_key, sent_msg.audio.file_id, title, "audio")
        
        try: await wait_msg.delete()
        except: pass

        if os.path.exists(result["file_path"]):
            os.remove(result["file_path"])
    else:
        try: await wait_msg.delete()
        except: pass
        await callback.message.answer(f"❌ Xatolik: {result.get('error')}")

# --- ODDIY MATN BILAN QIDIRISH ---
@router.message(F.text & ~F.text.startswith('/'))
async def handle_text_search(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_id = message.from_user.id
    unsubscribed = await check_user_subscription(bot, user_id)
    if unsubscribed:
        await message.answer("⚠️ Botdan foydalanish uchun obuna bo'ling:", reply_markup=get_subscription_kb(unsubscribed))
        return

    query = message.text
    wait_msg = await message.answer(f"🔍 \"{query}\" qidirilmoqda...")

    def search_youtube(search_term):
        ydl_opts = {'extract_flat': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(f"ytsearch20:{search_term}", download=False).get('entries', [])

    entries = await asyncio.to_thread(search_youtube, query)
    try: await wait_msg.delete()
    except: pass

    if not entries:
        await message.answer("❌ Topilmadi.")
        return

    await state.update_data(search_results=entries, query=query, page=1)
    await state.set_state(SearchState.waiting_for_selection)
    
    text = f"🎶 Natijalar (1-10):\n\n"
    for i in range(min(10, len(entries))):
        text += f"{i+1}. {entries[i].get('title', "Noma'lum")}\n"
    await message.answer(text, reply_markup=get_search_kb(page=1))

@router.callback_query(SearchState.waiting_for_selection, F.data.startswith("sel_"))
async def download_selected_song(callback: CallbackQuery, bot: Bot, state: FSMContext):
    data = await state.get_data()
    entries = data.get("search_results", [])
    idx = int(callback.data.split("_")[1])
    selected_entry = entries[idx]
    video_url = selected_entry.get('url') or f"https://www.youtube.com/watch?v={selected_entry.get('id')}"
    
    audio_cache_key = f"audio_{video_url}"
    cached_data = await db.get_cached_media(audio_cache_key)
    if cached_data:
        file_id, title = cached_data
        try: await callback.message.delete()
        except: pass
        await callback.message.answer_audio(audio=file_id, title=title, caption=AUDIO_CAPTION, reply_markup=get_main_audio_kb(video_url))
        await state.clear()
        return

    try: await callback.message.delete()
    except: pass
    
    wait_msg = await callback.message.answer("⏳ Tayyorlanmoqda...")
    result = await yt_downloader.download_media(video_url, is_audio=True)

    if result["success"]:
        title = result.get("title", "Musiqa")
        duration = result.get("duration", 0)
        sent_msg = await callback.message.answer_audio(
            audio=FSInputFile(result["file_path"]), 
            title=title, 
            caption=AUDIO_CAPTION, 
            duration=int(duration) if duration else None,
            reply_markup=get_main_audio_kb(video_url)
        )
        await db.save_media_cache(audio_cache_key, sent_msg.audio.file_id, title, "audio")
        await state.clear()
        
        try: await wait_msg.delete()
        except: pass

        if os.path.exists(result["file_path"]): 
            os.remove(result["file_path"])
    else:
        try: await wait_msg.delete()
        except: pass

@router.callback_query(F.data.startswith("stem_menu_"))
async def stem_menu_handler(callback: CallbackQuery):
    yt_id = callback.data.split("_", 2)[2]
    await callback.message.edit_reply_markup(reply_markup=get_stem_choice_kb(yt_id))

# --- VOKAL / MINUSOVKA AJRATISH ---
@router.callback_query(F.data.startswith("stem_v_") | F.data.startswith("stem_i_"))
async def handle_stem_action(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]  
    yt_id = parts[2]
    
    video_url = URL_MAP.get(str(yt_id))
    if not video_url:
        if len(str(yt_id)) == 11:
            video_url = f"https://www.youtube.com/watch?v={yt_id}"
        else:
            await callback.answer("❌ Havola topilmadi. Qaytadan yuboring.", show_alert=True)
            return
    
    is_vocal = (action == 'v')
    target_name = "Vokal" if is_vocal else "Minusovka"

    cached = await db.get_cached_stems(video_url)
    if cached:
        vocals_id, inst_id, title = cached
        file_id = vocals_id if is_vocal else inst_id
        if file_id:
            file_title = f"Vokal [{title}]" if is_vocal else f"Minusovka [{title}]"
            await callback.message.answer_audio(
                audio=file_id,
                title=file_title,
                caption=file_title
            )
            return

    wait_msg = await callback.message.answer("⏳ Tayyorlanmoqda...")
    
    result = await yt_downloader.download_media(video_url, is_audio=True)
    if not result["success"]:
        try: await wait_msg.delete()
        except: pass
        await callback.message.answer("❌ Yuklashda xatolik yuz berdi.")
        return

    title = result.get("title", "Musiqa")
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    
    vocals_path, inst_path = await stem_separator.separate_stems(result["file_path"])
    
    if vocals_path and inst_path:
        vocal_title_str = f"Vokal [{title}]"
        inst_title_str = f"Minusovka [{title}]"

        dir_name = os.path.dirname(vocals_path)
        new_vocal_path = os.path.join(dir_name, f"Vokal_{safe_title}.mp3")
        new_inst_path = os.path.join(dir_name, f"Minusovka_{safe_title}.mp3")
        
        if os.path.exists(new_vocal_path): os.remove(new_vocal_path)
        if os.path.exists(new_inst_path): os.remove(new_inst_path)
        
        os.rename(vocals_path, new_vocal_path)
        os.rename(inst_path, new_inst_path)

        if is_vocal:
            v_msg = await callback.message.answer_audio(
                audio=FSInputFile(new_vocal_path, filename=f"Vokal [{title}].mp3"),
                title=vocal_title_str,
                caption=vocal_title_str
            )
            vocals_id = v_msg.audio.file_id
            
            temp_msg = await callback.message.answer_audio(
                audio=FSInputFile(new_inst_path, filename=f"Minusovka [{title}].mp3"),
                title=inst_title_str
            )
            inst_id = temp_msg.audio.file_id
            try: await temp_msg.delete()
            except: pass
        else:
            i_msg = await callback.message.answer_audio(
                audio=FSInputFile(new_inst_path, filename=f"Minusovka [{title}].mp3"),
                title=inst_title_str,
                caption=inst_title_str
            )
            inst_id = i_msg.audio.file_id
            
            temp_msg = await callback.message.answer_audio(
                audio=FSInputFile(new_vocal_path, filename=f"Vokal [{title}].mp3"),
                title=vocal_title_str
            )
            vocals_id = temp_msg.audio.file_id
            try: await temp_msg.delete()
            except: pass
        
        await db.save_stems_cache(video_url, vocals_id, inst_id, title)
        
        try: await wait_msg.delete()
        except: pass
        
        if os.path.exists(new_vocal_path): os.remove(new_vocal_path)
        if os.path.exists(new_inst_path): os.remove(new_inst_path)
    else:
        try: await wait_msg.delete()
        except: pass
        await callback.message.answer("❌ AI ajrata olmadi.")
    
    if os.path.exists(result["file_path"]): os.remove(result["file_path"])
