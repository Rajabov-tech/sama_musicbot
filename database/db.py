import aiosqlite

DB_NAME = "database.db"

async def init_users_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                is_vip INTEGER DEFAULT 0
            )
        """)
        # Agar jadval avval yaratilgan bo'lib, is_vip ustuni yo'q bo'lsa, xavfsiz qo'shamiz
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.commit()

async def check_user_vip(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row and row[0] == 1

async def set_user_vip(user_id: int, status: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_vip = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Foydalanuvchilar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'uz',
                is_admin INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0
            )
        """)
        await db.commit()
    
    # Kanallar va kesh jadvallarini ham birga ishga tushiramiz
    await init_channels_table()
    await init_cache_table()
    await init_stems_cache_table()
async def init_channels_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                name TEXT,
                type TEXT
            )
        """)
        await db.commit()

async def init_cache_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS media_cache (
                url TEXT PRIMARY KEY,
                file_id TEXT,
                title TEXT,
                media_type TEXT
            )
        """)
        await db.commit()

# --- KESH FUNKSIYALARI (ASINXRON) ---

async def get_cached_media(url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT file_id, title FROM media_cache WHERE url = ?", (url,)) as cursor:
            return await cursor.fetchone()

async def save_media_cache(url: str, file_id: str, title: str, media_type: str):
    async with aiosqlite.connect(DB_NAME) as db:
        # 'INSERT OR REPLACE' to'g'ri sintaksis bilan yozildi
        await db.execute("""
            INSERT OR REPLACE INTO media_cache (url, file_id, title, media_type)
            VALUES (?, ?, ?, ?)
        """, (url, file_id, title, media_type))
        await db.commit()

# --- FOYDALANUVCHI VA KANAL FUNKSIYALARI ---

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, language, is_admin, is_vip) VALUES (?, 'uz', 0, 0)",
            (user_id,)
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, language, is_admin, is_vip FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def set_user_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

async def get_user_language(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 'uz'

async def get_all_user_ids():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def toggle_vip_status(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                new_status = 0 if row[0] == 1 else 1
                await db.execute("UPDATE users SET is_vip = ? WHERE user_id = ?", (new_status, user_id))
                await db.commit()
                return new_status
        return None

async def get_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT channel_id, name, type FROM channels") as cursor:
            return await cursor.fetchall()

async def add_channel(channel_id: str, name: str, c_type: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO channels (channel_id, name, type) VALUES (?, ?, ?)", (channel_id, name, c_type))
        await db.commit()

async def remove_channel(channel_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        await db.commit()

async def init_stems_cache_table():
    async with aiosqlite.connect(DB_NAME) as db:
        # Avval jadvalni yaratib olamiz (agar umuman yo'q bo'lsa)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stems_cache (
                url TEXT PRIMARY KEY,
                vocals_id TEXT,
                instrumental_id TEXT
            )
        """)
        
        # Agar 'title' ustuni mavjud bo'lmasa, uni xavfsiz qo'shamiz
        try:
            await db.execute("ALTER TABLE stems_cache ADD COLUMN title TEXT")
        except Exception:
            pass  # Agar ustun allaqachon mavjud bo'lsa, xatolikni o'tkazib yuboradi
            
        await db.commit()

async def get_cached_stems(url: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT vocals_id, instrumental_id, title FROM stems_cache WHERE url = ?", (url,)) as cursor:
            return await cursor.fetchone()

# 4 ta argument qabul qiladigan qilib to'g'rilaymiz:
async def save_stems_cache(url: str, vocals_id: str, instrumental_id: str, title: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO stems_cache (url, vocals_id, instrumental_id, title) VALUES (?, ?, ?, ?)", 
            (url, vocals_id, instrumental_id, title)
        )
        await db.commit()