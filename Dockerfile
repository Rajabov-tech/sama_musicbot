FROM python:3.10-slim

# Tizim uchun zarur dasturlarni (ffmpeg va boshqalarni) o'rnatamiz
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Qolgan barcha kodlarni ko'chiramiz
COPY . .

# Botni ishga tushirish
CMD ["python", "bot.py"]