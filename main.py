import asyncio
from datetime import datetime
import io
import logging
import random
import time
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, FSInputFile
import aiohttp
from config import ADMIN_IDS, BOT_TOKEN, DB_NAME, GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT
import database as db
from google import genai
from google.genai import types as genai_types
from keyboards import admin_main_kb, broadcast_type_kb, language_kb, main_menu_kb, tools_menu_kb
from locales import MESSAGES
import qrcode

# Ishga tushish vaqtini belgilash
UPTIME_START = time.time()

# Bot, Dispatcher va Gemini mijozini initsializatsiya qilish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)


# FSM Holatlari
class AdminStates(StatesGroup):
    target = State()
    message = State()


class ToolInputState(StatesGroup):
    waiting_for_qr = State()
    waiting_for_translate = State()
    waiting_for_grammar = State()
    waiting_for_summarize = State()
    waiting_for_code = State()


# ================= GEMINI AI FUNKSIYASI =================
async def request_gemini(
    prompt: str, image_bytes: bytes = None, mime_type: str = "image/jpeg"
) -> str:
    try:
        contents = []
        if image_bytes:
            contents.append(
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            )
        contents.append(prompt)

        config = genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        )

        response = await asyncio.to_thread(
            ai_client.models.generate_content,
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        return (
            response.text
            or "Kechirasiz, mazkur so'rov bo'yicha javob shakllantirilmadi."
        )
    except Exception as error:
        logging.error(f"Gemini API xatosi: {error}")
        return f"⚠️ Tizimda nosozlik yuz berdi: {error}"


# ================= GURUH VA BAZANI NAZORAT QILISH =================
@dp.message(F.chat.type.in_(["group", "supergroup"]))
async def group_tracker_handler(message: types.Message):
    db.add_group(message.chat.id, message.chat.title)

    bot_info = await bot.get_me()
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user.id == bot_info.id
    )
    is_mentioned = (
        bot_info.username and f"@{bot_info.username}" in (message.text or "")
    )

    # Guruhda botga murojaat qilingandagina Gemini javob beradi
    if is_reply_to_bot or is_mentioned:
        clean_text = (
            message.text.replace(f"@{bot_info.username}", "").strip()
            if message.text
            else "Salom"
        )
        await bot.send_chat_action(message.chat.id, "typing")
        reply = await request_gemini(clean_text)
        await message.reply(reply)


# ================= START VA TIL TANLASH =================
@dp.message(CommandStart(), F.chat.type == "private")
async def start_handler(message: types.Message):
    if db.is_user_banned(message.from_user.id):
        await message.answer(MESSAGES["uz"]["banned"])
        return

    db.add_or_update_user(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username,
    )
    await message.answer(MESSAGES["uz"]["choose_lang"], reply_markup=language_kb())


@dp.callback_query(F.data.startswith("lang_"))
async def select_lang_callback(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    db.set_user_language(callback.from_user.id, lang_code)

    msg_data = MESSAGES.get(lang_code, MESSAGES["uz"])
    await callback.message.delete()
    await callback.message.answer(msg_data["lang_selected"])
    await callback.message.answer(
        msg_data["welcome_intro"],
        reply_markup=main_menu_kb(lang_code),
        parse_mode="HTML",
    )
    await callback.answer()


# ================= ASOSIY MENYU BOSHQARUVI =================
@dp.message(F.chat.type == "private", F.text)
async def main_menu_text_handler(
    message: types.Message, state: FSMContext
):
    if db.is_user_banned(message.from_user.id):
        return

    lang = db.get_user_language(message.from_user.id)
    t = MESSAGES.get(lang, MESSAGES["uz"])
    txt = message.text

    if txt == t["btn_chat"]:
        await message.answer(t["chat_mode_on"], parse_mode="HTML")
    elif txt == t["btn_tools"]:
        await message.answer(
            t["tools_title"], reply_markup=tools_menu_kb(), parse_mode="HTML"
        )
    elif txt == t["btn_settings"]:
        await message.answer(t["choose_lang"], reply_markup=language_kb())
    elif txt == t["btn_about"]:
        await message.answer(t["about_text"], parse_mode="HTML")
    else:
        # Erkin suhbat - Gemini AI
        await bot.send_chat_action(message.chat.id, "typing")
        response = await request_gemini(txt)
        await message.answer(response)


# ================= GEMINI VISION (RASMLAR TAHLILI) =================
@dp.message(F.photo, F.chat.type == "private")
async def vision_analyzer_handler(message: types.Message):
    if db.is_user_banned(message.from_user.id):
        return

    lang = db.get_user_language(message.from_user.id)
    wait_msg = await message.answer(MESSAGES[lang]["wait_ai"])

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)

    caption = (
        message.caption
        or "Ushbu tasvirni to'liq va professional tarzda tahlil qilib ber."
    )
    analysis = await request_gemini(caption, image_bytes=file_bytes.read())

    await wait_msg.edit_text(analysis)


# ================= ASBOBLAR FUNKSIYALARI =================
@dp.callback_query(F.data == "tool_currency")
async def tool_currency_cb(call: types.CallbackQuery):
    url = "https://cbu.uz/oz/arkhiv-kursov-valyut/json/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                rates = {
                    item["Ccy"]: (item["Rate"], item["Diff"])
                    for item in data
                    if item["Ccy"] in ["USD", "EUR", "RUB"]
                }
                text = "💵 <b>Markaziy Bank Rasmiy Kurslari:</b>\n\n"
                for c, (r, d) in rates.items():
                    sign = "+" if float(d) > 0 else ""
                    text += f"1 {c} = <b>{r}</b> UZS ({sign}{d})\n"
                await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "tool_qr")
async def tool_qr_cb(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer(
        "QR-kod qilish uchun havola yoki matn yuboring:"
    )
    await state.set_state(ToolInputState.waiting_for_qr)
    await call.answer()


@dp.message(ToolInputState.waiting_for_qr)
async def process_qr_create(message: types.Message, state: FSMContext):
    img = qrcode.make(message.text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    file = BufferedInputFile(buf.read(), filename="qrcode.png")
    await message.answer_photo(file, caption="✅ QR-kod tayyorlandi!")
    await state.clear()


@dp.callback_query(F.data == "tool_id")
async def tool_id_cb(call: types.CallbackQuery):
    await call.message.answer(
        f"👤 Sizning ID: <code>{call.from_user.id}</code>\n"
        f"💬 Ushbu Chat ID: <code>{call.message.chat.id}</code>",
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data == "tool_ping")
async def tool_ping_cb(call: types.CallbackQuery):
    t_start = time.time()
    msg = await call.message.answer("🏓 Hisoblanmoqda...")
    ping = round((time.time() - t_start) * 1000)
    uptime = round(time.time() - UPTIME_START)
    await msg.edit_text(
        f"🏓 <b>Kechikish:</b> {ping} ms\n⏱ <b>Bot faoliyati:</b> {uptime} sekund",
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data == "tool_ny")
async def tool_ny_cb(call: types.CallbackQuery):
    now = datetime.now()
    ny = datetime(now.year + 1, 1, 1)
    diff = ny - now
    await call.message.answer(
        f"🎄 Yangi yilgacha: <b>{diff.days} kun, {diff.seconds // 3600} soat</b> qoldi!",
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data == "tool_random")
async def tool_random_cb(call: types.CallbackQuery):
    num = random.randint(1, 100)
    ans = random.choice(["Ha", "Yo'q"])
    await call.message.answer(
        f"🎲 Tasodifiy son (1-100): <b>{num}</b>\n🔮 Qaror: <b>{ans}</b>",
        parse_mode="HTML",
    )
    await call.answer()


# AI Asboblari
@dp.callback_query(F.data.in_(["tool_imlo", "tool_tr", "tool_sum", "tool_code"]))
async def tools_ai_prompts_cb(call: types.CallbackQuery, state: FSMContext):
    data = call.data
    if data == "tool_imlo":
        await call.message.answer(
            "Xatolarini tekshirish uchun matn yuboring:"
        )
        await state.set_state(ToolInputState.waiting_for_grammar)
    elif data == "tool_tr":
        await call.message.answer("Tarjima qilish uchun matn yuboring:")
        await state.set_state(ToolInputState.waiting_for_translate)
    elif data == "tool_sum":
        await call.message.answer(
            "Konspekt/xulosa qilish uchun matn kiriting:"
        )
        await state.set_state(ToolInputState.waiting_for_summarize)
    elif data == "tool_code":
        await call.message.answer(
            "Qanday vazifa uchun dasturlash kodi kerak? Yozing:"
        )
        await state.set_state(ToolInputState.waiting_for_code)
    await call.answer()


@dp.message(ToolInputState.waiting_for_grammar)
async def tool_exec_grammar(message: types.Message, state: FSMContext):
    await bot.send_chat_action(message.chat.id, "typing")
    res = await request_gemini(
        f"Quyidagi matnning barcha orfografik va uslubiy xatolarini to'g'irla:\n{message.text}"
    )
    await message.answer(res)
    await state.clear()


@dp.message(ToolInputState.waiting_for_translate)
async def tool_exec_translate(message: types.Message, state: FSMContext):
    await bot.send_chat_action(message.chat.id, "typing")
    res = await request_gemini(
        f"Ushbu matnni o'zbek tiliga tabiiy va adabiy tarjima qil:\n{message.text}"
    )
    await message.answer(res)
    await state.clear()


@dp.message(ToolInputState.waiting_for_summarize)
async def tool_exec_summarize(message: types.Message, state: FSMContext):
    await bot.send_chat_action(message.chat.id, "typing")
    res = await request_gemini(
        f"Ushbu matnni asosiy tezislarini saqlab, qisqa xulosa ko'rinishida yozib ber:\n{message.text}"
    )
    await message.answer(res)
    await state.clear()


@dp.message(ToolInputState.waiting_for_code)
async def tool_exec_code(message: types.Message, state: FSMContext):
    await bot.send_chat_action(message.chat.id, "typing")
    res = await request_gemini(
        f"Sen yetakchi dasturchisan. Quyidagi vazifani hal qiluvchi toza kod va unga izoh yoz:\n{message.text}"
    )
    await message.answer(res)
    await state.clear()


# ================= ADMIN PANELI =================
@dp.message(Command("admin"), F.chat.type == "private")
async def admin_entry(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("👑 <b>PERFECT Boshqaruv Markazi</b>", reply_markup=admin_main_kb(), parse_mode="HTML")


@dp.callback_query(F.data == "admin_stats")
async def admin_stats_cb(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    users, groups, langs = db.get_statistics()
    t_uz = langs.get("uz", 0)
    t_ru = langs.get("ru", 0)
    t_en = langs.get("en", 0)

    txt = (
        "📊 <b>Botning Jonli Statistikasi:</b>\n\n"
        f"👤 Foydalanuvchilar: <b>{users} ta</b>\n"
        f"👥 Guruhlar: <b>{groups} ta</b>\n"
        f"📈 Jami auditoriya: <b>{users + groups} ta</b>\n\n"
        "🌐 <b>Tillar taqsimoti:</b>\n"
        f"🇺🇿 O'zbekcha: {t_uz}\n"
        f"🇷🇺 Русский: {t_ru}\n"
        f"🇬🇧 English: {t_en}"
    )
    await call.message.edit_text(txt, reply_markup=admin_main_kb(), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "admin_get_db")
async def admin_get_db_cb(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    file = FSInputFile(DB_NAME)
    await call.message.answer_document(file, caption="📁 Ma'lumotlar bazasi nusxasi")
    await call.answer()


@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_step1(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text(
        "📢 E'lon qaysi auditoriyaga yuborilsin?", reply_markup=broadcast_type_kb()
    )
    await call.answer()


@dp.callback_query(F.data.startswith("broad_"))
async def admin_broadcast_step2(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    target = call.data.split("_")[1]
    if target == "cancel":
        await call.message.edit_text(
            "Amal bekor qilindi.", reply_markup=admin_main_kb()
        )
        await state.clear()
        return

    await state.update_data(target=target)
    await call.message.edit_text(
        "📝 E'loningizni yuboring (Matn, rasm, video yoki havola):"
    )
    await state.set_state(AdminStates.message)
    await call.answer()


@dp.message(AdminStates.message, F.chat.type == "private")
async def admin_broadcast_execute(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    target_type = data.get("target")
    destinations = db.get_broadcast_list(target_type)

    progress = await message.answer(
        f"🚀 E'lon tarqatilmoqda... (Jami: {len(destinations)})"
    )
    sent, failed = 0, 0

    for chat_id in destinations:
        try:
            await message.copy_to(chat_id=chat_id)
            sent += 1
            await asyncio.sleep(0.04)  # Limitdan himoya
        except Exception:
            failed += 1

    await progress.edit_text(
        f"✅ <b>E'lon yakunlandi!</b>\n\n🟢 Yetkazildi: {sent} ta\n🔴 Yetkazilmadi: {failed} ta",
        parse_mode="HTML",
    )
    await state.clear()


@dp.message(Command("ban"))
async def admin_ban_cmd(message: types.Message, command: CommandObject):
    if message.from_user.id in ADMIN_IDS and command.args:
        try:
            uid = int(command.args.strip())
            db.set_ban_status(uid, 1)
            await message.answer(f"🚫 Foydalanuvchi {uid} bloklandi.")
        except ValueError:
            await message.answer("Noto'g'ri ID format.")


@dp.message(Command("unban"))
async def admin_unban_cmd(message: types.Message, command: CommandObject):
    if message.from_user.id in ADMIN_IDS and command.args:
        try:
            uid = int(command.args.strip())
            db.set_ban_status(uid, 0)
            await message.answer(f"✅ Foydalanuvchi {uid} blokdan chiqarildi.")
        except ValueError:
            await message.answer("Noto'g'ri ID format.")


# ================= ASOSIY DASTURNI ISHGA TUSHIRISH =================
async def main():
    logging.basicConfig(level=logging.INFO)
    db.init_db()
    print("=" * 45)
    print("👑 PERFECT BOT TIZIMI MUVAFFAQIYATLI ISHGA TUSHDI!")
    print("=" * 45)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
