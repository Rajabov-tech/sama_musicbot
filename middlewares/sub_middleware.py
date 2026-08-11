from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import BASE_CHANNEL_ID, BASE_CHANNEL_URL
import database.db as db

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Event Message yoki CallbackQuery bo'lishi mumkin
        bot = data['bot']
        user = event.from_user
        
        if not user:
            return await handler(event, data)

        # Foydalanuvchini bazadan topish (yoki yaratish)
        user_data = await db.get_user(user.id)
        if not user_data:
            await db.add_user(user.id)
            user_data = await db.get_user(user.id)

        is_vip = user_data[3] # (is_vip boolean)
        
        # Agar VIP bo'lsa, obuna tekshirib o'tirmaymiz (Premium daraja)
        if is_vip:
            return await handler(event, data)

        # 1. Asosiy kanal tekshiruvi
        try:
            member = await bot.get_chat_member(chat_id=BASE_CHANNEL_ID, user_id=user.id)
            if member.status in ['left', 'kicked']:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Asosiy Kanal", url=BASE_CHANNEL_URL)],
                    [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
                ])
                text = "Botdan foydalanish uchun asosiy kanalimizga obuna bo'ling!"
                
                if isinstance(event, Message):
                    await event.answer(text, reply_markup=markup)
                elif isinstance(event, CallbackQuery):
                    await event.message.answer(text, reply_markup=markup)
                return # Kod shu yerda to'xtaydi, keyingi amallar bajarilmaydi
        except Exception:
            # Agar bot kanalga admin qilinmagan bo'lsa, o'tkazib yuboradi (Crash bo'lmasligi uchun)
            pass 

        # (Qo'shimcha: Har 10-yuklashda tasodifiy kanal tekshiruvi mantiqini handler ichiga yozamiz)

        # Agar hamma narsa joyida bo'lsa, foydalanuvchini botga kiritamiz
        return await handler(event, data)