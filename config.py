import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "AGAR_LOKAL_BO'LSA_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AGAR_LOKAL_BO'LSA_KEY")
ADMIN_IDS = [int(os.getenv("ADMIN_ID", "123456789"))]

DB_NAME = "perfect_bot.db"
GEMINI_MODEL = "gemini-2.5-flash"
SYSTEM_PROMPT = "Sening isming PERFECT..."
