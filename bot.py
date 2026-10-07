import asyncio
import os
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

API_TOKEN = "8294705765:AAGXgWlHrPDSASeW6I9Qen3RBN36eC6OMqU"
ADMIN_IDS = {6723183204}  # Замените на свой Telegram ID

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Ошибка записи в файл {USERS_FILE}: {e}")

# Загрузка данных при старте
users_db = load_users()

# Корректная инициализация для aiogram 3.7.0+ (каждая команда на новой строке)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def parse_registration(text: str):
    """
    Парсит строку вида: Shrek Тег:qr2pk
    Возвращает (nickname, tag) или (None, None) если формат неверный.
    """
    tag_match = re.search(r'Тег:(\S+)', text)
    if not tag_match:
        return None, None
    
    tag = tag_match.group(1)
    # Никнейм — это всё, что идет до "Тег:"
    nickname = text[:tag_match.start()].strip()
    
    if not nickname or not tag:
        return None, None
        
    return nickname, tag

async def is_admin(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        return True
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Чтобы записаться на пати, введите:\n"
        "<code>+пати Никнейм Тег:ваш_тег</code>\n\n"
        "Пример:\n"
        "<code>+пати Shrek Тег:qr2pk</code>\n\n"
        "Чтобы выйти из списка:\n"
        "<code>-пати</code>"
    )

@dp.message(F.text.startswith("+пати"))
async def cmd_add_party(message: types.Message):
    user_id = str(message.from_user.id)
    
    # Удаляем сообщение пользователя (+пати ...)
    try:
        await message.delete()
    except Exception:
        # Бот может не иметь прав на удаление в чате
        pass

    # Проверяем, есть ли пользователь уже в базе
    if user_id in users_db:
        user = users_db[user_id]
        await message.answer(
            f"✅ Вы уже зарегистрированы!\n\n"
            f"👤 Ник: <b>{user['nickname']}</b>\n"
            f"🏷 Тег: <code>{user['tag']}</code>"
        )
        return

    # Если пользователя нет, пытаемся зарегистрировать
    input_text = message.text[5:].strip()
    
    nickname, tag = parse_registration(input_text)
    
    if not nickname or not tag:
        await message.answer(
            "❌ Неверный формат. Используйте команду с пробелом:\n"
            "<code>+пати Никнейм Тег:ваш_тег</code>\n\n"
            "Пример: <code>+пати Shrek Тег:qr2pk</code>"
        )
        return

    # Сохраняем данные
    users_db[user_id] = {
        "nickname": nickname,
        "tag": tag
    }
    save_users(users_db)

    await message.answer(
        f"✅ Регистрация прошла успешно!\n\n"
        f"👤 Ник: <b>{nickname}</b>\n"
        f"🏷 Тег: <code>{tag}</code>"
    )

@dp.message(F.text.startswith("-пати"))
async def cmd_remove_party(message: types.Message):
    user_id = str(message.from_user.id)
    
    # Удаляем сообщение пользователя (-пати)
    try:
        await message.delete()
    except Exception:
        pass

    if user_id not in users_db:
        await message.answer("❗ Вы не найдены в базе зарегистрированных пользователей.")
        return

    user = users_db[user_id]
    
    # Удаляем из базы
    del users_db[user_id]
    save_users(users_db)

    await message.answer(
        f"🗑 Вы удалены из списка на пати.\n\n"
        f"Данные были: <b>{user['nickname']}</b> | <code>{user['tag']}</code>"
    )

# Оставил команды для админа на случай, если нужно будет выгрузить базу
@dp.message(Command("export"))
async def cmd_export(message: types.Message):
    if not await is_admin(message):
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    if not users_db:
        await message.answer("База пользователей пуста.")
        return

    text = "📋 СПИСОК УЧАСТНИКОВ ПАТИ:\n\n"
    for user_id, data in users_db.items():
        text += f"👤 ID: <code>{user_id}</code>\nНик: <b>{data['nickname']}</b>\nТег: <code>{data['tag']}</code>\n---\n"
        
    await message.answer(text)

@dp.message(Command("reload"))
async def cmd_reload(message: types.Message):
    if not await is_admin(message):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    global users_db
    users_db = load_users()
    await message.answer("✅ Данные пользователей перезагружены из файла.")

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    if not await is_admin(message):
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    global users_db
    users_db.clear()
    save_users(users_db)
    await message.answer("✅ База пользователей очищена.")

async def on_startup(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)

async def main():
    await dp.start_polling(bot, on_startup=on_startup)

if __name__ == "__main__":
    asyncio.run(main())
