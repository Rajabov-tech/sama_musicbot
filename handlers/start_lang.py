import aiosqlite
import database.db as db
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
import database.db as db

router = Router()

# Til tanlash uchun Inline tugmalar
def get_language_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
            ],
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
            ]
        ]
    )

# Foydalanuvchi tiliga mos pastki menyu tugmalari (Reply Keyboard)
def get_main_menu_kb(lang: str = 'uz'):
    if lang == 'ru':
        btn_lang = "🌐 Сменить язык"
        btn_help = "ℹ️ О боте"
    elif lang == 'en':
        btn_lang = "🌐 Change Language"
        btn_help = "ℹ️ About Bot"
    else:
        btn_lang = "🌐 Tilni o'zgartirish"
        btn_help = "ℹ️ Bot haqida"
        
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=btn_lang), KeyboardButton(text=btn_help)]
        ],
        resize_keyboard=True
    )

# 1. /start bosilganda
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    user = await db.get_user(user_id)
    if not user:
        await db.add_user(user_id)
        # Yangi foydalanuvchiga til tanlatamiz
        await message.answer(
            "Iltimos, o'zingizga qulay tilni tanlang:\n"
            "Пожалуйста, выберите язык:\n"
            "Please select your preferred language:",
            reply_markup=get_language_kb()
        )
    else:
        lang = await db.get_user_language(user_id)
        if lang == "uz":
            text = "Xush kelibsiz! Musiqa qidirish uchun qo'shiq nomini yuboring."
        elif lang == "ru":
            text = "Добро пожаловать! Отправьте название песни для поиска."
        else:
            text = "Welcome! Send a song name to search."
            
        await message.answer(text, reply_markup=get_main_menu_kb(lang))

# 2. /lang buyrug'i yoki tugma bosilganda
@router.message(Command("lang"))
async def cmd_lang(message: Message):
    await message.answer(
        "Tilni o'zgartirish / Сменить язык / Change language:",
        reply_markup=get_language_kb()
    )

# Pastki menyudagi "Tilni o'zgartirish" tugmalari bosilganda
@router.message(F.text.in_(["🌐 Tilni o'zgartirish", "🌐 Сменить язык", "🌐 Change Language"]))
async def menu_change_lang(message: Message):
    await message.answer(
        "Tilni o'zgartirish / Сменить язык / Change language:",
        reply_markup=get_language_kb()
    )

# Pastki menyudagi "Bot haqida" tugmalari bosilganda
@router.message(F.text.in_(["ℹ️ Bot haqida", "ℹ️ О боте", "ℹ️ About Bot"]))
async def menu_about(message: Message):
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)
    
    if lang == "uz":
        text = "🤖 **SAMA_Musicbot** — Musiqa va media fayllarni yuklab olish hamda ularga turli effektlar berish uchun eng qulay bot."
    elif lang == "ru":
        text = "🤖 **SAMA_Musicbot** — Удобный бот для скачивания музыки, медиафайлов и добавления аудиоэффектов."
    else:
        text = "🤖 **SAMA_Musicbot** — A convenient bot for downloading music, media files and applying audio effects."
        
    await message.answer(text, parse_mode="HTML")

# 3. Inline orqali til tanlanganda
@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Bazaga saqlaymiz
    await db.set_user_language(user_id, lang)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    if lang == "uz":
        text = "✅ **Til O'zbek tiliga o'zgartirildi!**"
    elif lang == "ru":
        text = "✅ **Язык изменен на русский!**"
    else:
        text = "✅ **Language changed to English!**"
        
    # Yangi tildagi pastki menyu tugmalari bilan xabar beramiz
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_main_menu_kb(lang))
    await callback.answer()