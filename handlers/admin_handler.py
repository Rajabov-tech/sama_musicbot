import asyncio
import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database.db as db

router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_user_id = State()
    waiting_for_channel_data = State()

def get_admin_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
                InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton(text="🔍 Foydalanuvchini boshqarish", callback_data="admin_manage_user"),
                InlineKeyboardButton(text="📢 Kanallarni boshqarish", callback_data="admin_channels")
            ],
            [
                InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
            ]
        ]
    )

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    
    user = await db.get_user(user_id)
    if not user:
        await db.add_user(user_id)
        
    async with aiosqlite.connect(db.DB_NAME) as connection:
        async with connection.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1") as cursor:
            admin_count = await cursor.fetchone()
            if admin_count[0] == 0:
                await connection.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
                await connection.commit()

    updated_user = await db.get_user(user_id)
    if not updated_user or updated_user[2] != 1:
        await message.answer("❌ Kechirasiz, sizda admin huquqi yo'q.")
        return

    await message.answer(
        "👑 <b>Admin Panelga xush kelibsiz!</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=get_admin_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    async with aiosqlite.connect(db.DB_NAME) as connection:
        async with connection.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
            
        async with connection.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1") as cursor:
            total_vips = (await cursor.fetchone())[0]

    text = (
        "📊 <b>Bot Statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b> ta\n"
        f"⭐ VIP foydalanuvchilar: <b>{total_vips}</b> ta"
    )
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]])
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_back")]])
    await callback.message.edit_text(
        "📢 <b>Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:</b>\n\n"
        "<i>Matn, rasm (caption bilan), video yoki istalgan kontent yuborishingiz mumkin.</i>",
        reply_markup=back_kb,
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    
    user_ids = await db.get_all_user_ids()
    status_msg = await message.answer(f"⏳ Xabar tarqatilmoqda... Jami: {len(user_ids)} ta foydalanuvchi.")
    
    success = 0
    blocked = 0
    failed = 0
    
    for uid in user_ids:
        try:
            await message.send_copy(chat_id=uid)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                blocked += 1
            else:
                failed += 1

    await status_msg.edit_text(
        "✅ <b>Rassilka yakunlandi!</b>\n\n"
        f"📤 Muvaffaqiyatli yuborildi: <b>{success}</b> ta\n"
        f"🚫 Botni bloklaganlar: <b>{blocked}</b> ta\n"
        f"❌ Xatolik yuz berdi: <b>{failed}</b> ta",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_manage_user")
async def admin_manage_user(callback: CallbackQuery, state: FSMContext):
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]])
    await callback.message.edit_text(
        "🔍 Boshqarish uchun foydalanuvchining <b>Telegram ID</b> raqamini yuboring:",
        reply_markup=back_kb,
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.answer()

@router.message(AdminStates.waiting_for_user_id)
async def process_user_lookup(message: Message, state: FSMContext):
    await state.clear()
    
    if not message.text.isdigit():
        await message.answer("❌ Noto'g'ri ID. Faqat raqamlardan iborat Telegram ID kiriting.")
        return
        
    target_id = int(message.text)
    user = await db.get_user(target_id)
    
    if not user:
        await message.answer(f"❌ {target_id} ID raqamli foydalanuvchi ma'lumotlar bazasida topilmadi.")
        return
        
    is_admin_text = "Ha 👑" if user[2] else "Yo'q"
    is_vip_text = "Ha ⭐" if user[3] else "Yo'q"
    
    user_info = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"🆔 ID: <code>{user[0]}</code>\n"
        f"🌐 Til: <b>{user[1]}</b>\n"
        f"👑 Admin: <b>{is_admin_text}</b>\n"
        f"⭐ VIP: <b>{is_vip_text}</b>"
    )
    
    manage_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ VIP statusni o'zgartirish", callback_data=f"toggle_vip_{target_id}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
        ]
    )
    
    await message.answer(user_info, reply_markup=manage_kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("toggle_vip_"))
async def callback_toggle_vip(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[2])
    new_status = await db.toggle_vip_status(target_id)
    
    status_str = "Berildi ⭐" if new_status == 1 else "Olib tashlandi"
    await callback.answer(f"✅ VIP status o'zgartirildi: {status_str}", show_alert=True)
    
    user = await db.get_user(target_id)
    is_admin_text = "Ha 👑" if user[2] else "Yo'q"
    is_vip_text = "Ha ⭐" if user[3] else "Yo'q"
    
    user_info = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"🆔 ID: <code>{user[0]}</code>\n"
        f"🌐 Til: <b>{user[1]}</b>\n"
        f"👑 Admin: <b>{is_admin_text}</b>\n"
        f"⭐ VIP: <b>{is_vip_text}</b>"
    )
    manage_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ VIP statusni o'zgartirish", callback_data=f"toggle_vip_{target_id}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
        ]
    )
    try:
        await callback.message.edit_text(user_info, reply_markup=manage_kb, parse_mode="HTML")
    except Exception:
        pass

@router.callback_query(F.data == "admin_channels")
async def admin_channels_menu(callback: CallbackQuery):
    channels = await db.get_channels()
    
    text = "📢 <b>Majburiy kanallar ro'yxati:</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    if channels:
        for ch_id, name, c_type in channels:
            type_label = "⭐ Asosiy" if c_type == "base" else "📌 Random"
            text += f"• {name} (<code>{ch_id}</code>) — <b>{type_label}</b>\n"
            builder.button(text=f"❌ O'chirish: {name}", callback_data=f"del_chan_{ch_id}")
    else:
        text += "Hozircha kanallar qo'shilmagan."
        
    builder.button(text="➕ Kanal qo'shish", callback_data="add_channel_start")
    builder.button(text="🔙 Orqaga", callback_data="admin_back")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "add_channel_start")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_channels")]])
    await callback.message.edit_text(
        "➕ <b>Yangi kanal qo'shish uchun quyidagi formatda yuboring:</b>\n\n"
        "<code>@kanal_username, Kanal Nomi, turi</code>\n\n"
        "<i>Turi qismiga faqat <b>base</b> (asosiy) yoki <b>random</b> deb yozing.</i>\n"
        "<b>Misol:</b> <code>@my_channel, Mening Kanalim, base</code>",
        reply_markup=back_kb,
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_channel_data)
    await callback.answer()

@router.message(AdminStates.waiting_for_channel_data)
async def process_new_channel(message: Message, state: FSMContext):
    await state.clear()
    
    try:
        parts = [p.strip() for p in message.text.split(",")]
        if len(parts) != 3:
            raise ValueError("Format xato")
            
        ch_id, name, c_type = parts[0], parts[1], parts[2].lower()
        if c_type not in ["base", "random"]:
            await message.answer("❌ Xatolik: Turi faqat <b>base</b> yoki <b>random</b> bo'lishi kerak!", parse_mode="HTML")
            return
            
        await db.add_channel(ch_id, name, c_type)
        await message.answer(f"✅ <b>{name}</b> ({ch_id}) muvaffaqiyatli qo'shildi!", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Xato format! Iltimos, quyidagicha yuboring:\n<code>@kanal_username, Kanal Nomi, base</code>", parse_mode="HTML")

@router.callback_query(F.data.startswith("del_chan_"))
async def delete_channel_callback(callback: CallbackQuery):
    ch_id = callback.data.replace("del_chan_", "")
    await db.remove_channel(ch_id)
    await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
    await admin_channels_menu(callback)

@router.callback_query(F.data == "admin_back")
async def admin_back_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "👑 <b>Admin Panelga xush kelibsiz!</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=get_admin_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def admin_close_panel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()