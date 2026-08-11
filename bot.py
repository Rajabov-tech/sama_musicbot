import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from config import BOT_TOKEN

# Bazani import qilish (bu qism to'g'ri ekanligiga ishonch hosil qiling)
import database.db as db 

# Routerlarni import qilish
from handlers import start_lang, media_handler, effects_handler, admin_handler

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Bazani ishga tushiramiz (agar 1-qadamdagi kod bo'lsa, bu ishlaydi)
    try:
        await db.init_db()
        print("✅ Ma'lumotlar bazasi muvaffaqiyatli ishga tushdi.")
    except Exception as e:
        print(f"❌ Baza ishga tushishida xatolik: {e}")
        return

    session = AiohttpSession(timeout=120)
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()

    # Routerlarni ulaymiz
    dp.include_router(start_lang.router)
    dp.include_router(admin_handler.router)
    dp.include_router(media_handler.router)
    dp.include_router(effects_handler.router)

    print("🚀 SAMA_Musicbot ishga tushdi!")
    # Eski pollingni tozalab, yangisini boshlaymiz
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    print("Ping keldi! Bot tirik.")
    return "SAMA Musicbot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()

# Botni ishga tushirishdan oldin mana shu funksiyani chaqirasiz:
if __name__ == '__main__':
    keep_alive()
    # Bu yerda sizning asosiy botingizni ishga tushiruvchi kodlaringiz bo'ladi (masalan, asyncio.run(main()) yoki dp.start_polling())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi!")
