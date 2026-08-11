import os
import asyncio
import requests
from uuid import uuid4
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services import ffmpeg_service
from handlers.media_handler import AUDIO_CAPTION, get_main_audio_kb
from config import BOT_TOKEN

router = Router()

def get_effects_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎧 8D Audio", callback_data="eff_8d")
    builder.button(text="🔊 Bass Boost", callback_data="eff_bass")
    builder.button(text="🏛 Concert Hall", callback_data="eff_concert")
    builder.button(text="📻 Radio", callback_data="eff_radio")
    builder.button(text="🐢 Slow Motion", callback_data="eff_slow")
    builder.button(text="🗣 Echo", callback_data="eff_echo")
    builder.button(text="🔄 MP3 Convert", callback_data="eff_convert")
    builder.button(text="🔙 Orqaga", callback_data="eff_back")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()

@router.callback_query(F.data == "eff_menu")
async def show_effects(callback: CallbackQuery):
    try:
        await callback.message.edit_reply_markup(reply_markup=get_effects_kb())
    except Exception:
        await callback.answer()

@router.callback_query(F.data == "eff_back")
async def hide_effects(callback: CallbackQuery):
    try:
        await callback.message.edit_reply_markup(reply_markup=get_main_audio_kb())
    except Exception:
        await callback.answer()

@router.callback_query(F.data.startswith("eff_") & (F.data != "eff_menu") & (F.data != "eff_back"))
async def process_effect(callback: CallbackQuery, bot: Bot):
    effect_key = callback.data.split("_")[1]
    
    if not callback.message.audio:
        return await callback.answer("❌ Effekt qo'shish uchun audio fayl topilmadi!", show_alert=True)
    
    await callback.answer("⏳ Effekt qo'llanilmoqda, iltimos kuting...")
    
    try:
        # bot.get_file ga ham request_timeout qo'shamiz
        file = await bot.get_file(callback.message.audio.file_id, request_timeout=300)
        input_path = f"downloads/input_{callback.from_user.id}_{uuid4().hex[:6]}.mp3"
        
        if not os.path.exists("downloads"):
            os.makedirs("downloads", exist_ok=True)
            
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        def download_sync(url, dest):
            response = requests.get(url, stream=True, timeout=300)
            with open(dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        await asyncio.to_thread(download_sync, file_url, input_path)

        output_path = await ffmpeg_service.apply_audio_effect(input_path, effect_key)
        
        audio_file = FSInputFile(output_path)
        title = callback.message.audio.title or "Musiqa"
        
        await callback.message.answer_audio(
            audio=audio_file, 
            title=f"[{effect_key.upper()}] {title}",
            caption=AUDIO_CAPTION, 
            reply_markup=get_main_audio_kb(),
            request_timeout=300
        )
        
        if os.path.exists(input_path):
            os.remove(input_path)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
            
    except Exception as e:
        print(f"Effect processing error: {e}")
        await callback.message.answer("❌ Effekt qo'llashda xatolik yuz berdi. Qaytadan urinib ko'ring.")