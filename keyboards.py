from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from locales import MESSAGES


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇺🇿 O'zbekcha", callback_data="lang_uz"
                ),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            ],
            [
                InlineKeyboardButton(
                    text="🇬🇧 English", callback_data="lang_en"
                )
            ],
        ]
    )


def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    texts = MESSAGES.get(lang, MESSAGES["uz"])
    kb = [
        [
            KeyboardButton(text=texts["btn_chat"]),
            KeyboardButton(text=texts["btn_tools"]),
        ],
        [
            KeyboardButton(text=texts["btn_settings"]),
            KeyboardButton(text=texts["btn_about"]),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def tools_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💵 Kurslar", callback_data="tool_currency"
                ),
                InlineKeyboardButton(text="🔤 QR Kod", callback_data="tool_qr"),
            ],
            [
                InlineKeyboardButton(
                    text="🆔 Mening ID", callback_data="tool_id"
                ),
                InlineKeyboardButton(
                    text="🏓 Ping / Tezlik", callback_data="tool_ping"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏳ Yangi Yil", callback_data="tool_ny"
                ),
                InlineKeyboardButton(
                    text="🎲 Random (Tasodif)", callback_data="tool_random"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📝 Imlo Tekshirish", callback_data="tool_imlo"
                ),
                InlineKeyboardButton(
                    text="🌐 Tarjimon", callback_data="tool_tr"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📄 Xulosa Qilish", callback_data="tool_sum"
                ),
                InlineKeyboardButton(
                    text="🐍 Kod Yozuvchi", callback_data="tool_code"
                ),
            ],
        ]
    )


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Statistika", callback_data="admin_stats"
                ),
                InlineKeyboardButton(
                    text="📢 E'lon Yuborish", callback_data="admin_broadcast"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💾 Baza Nusxasi (.db)", callback_data="admin_get_db"
                )
            ],
        ]
    )


def broadcast_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Faqat Foydalanuvchilarga",
                    callback_data="broad_users",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Faqat Guruhlarga", callback_data="broad_groups"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Barchaga (Chat + Guruh)",
                    callback_data="broad_all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish", callback_data="broad_cancel"
                )
            ],
        ]
    )
