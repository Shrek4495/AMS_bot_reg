import asyncio
import os
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

API_TOKEN = "8852961042:AAEnZDBLC_61l5hM1e0YJKsyEfw5w8xiw9Q"

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

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

def parse_registration(text: str):
    tag_match = re.search(r'Тег:(\S+)', text)
    if not tag_match:
        return None, None
    
    tag = tag_match.group(1)
    nickname = text[:tag_match.start()].strip()
    
    if not nickname or not tag:
        return None, None
        
    return nickname, tag

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id in users_db:
        user = users_db[user_id]
        # Сохраняем ID сообщения с данными
        sent_message = await message.answer(f"{user['nickname']} Тег:{user['tag']}")
        
        # Сохраняем ID сообщения в базу рядом с данными пользователя
        users_db[user_id]['last_msg_id'] = sent_message.message_id
        save_users(users_db)
    else:
        await message.answer("Вы еще не зарегистрированы.")

    await message.answer(
        "ℹ️ <b>Инструкция:</b>\n\n"
        "Чтобы сохранить или посмотреть свои данные, введите:\n"
        "<code>+пати Никнейм Тег:ваш_тег</code>\n\n"
        "Пример: <code>+пати Shrek Тег:qr2pk</code>\n\n"
        "Чтобы удалить сообщение с данными из чата:\n"
        "<code>-пати</code>"
    )

@dp.message(F.text.startswith("+пати"))
async def cmd_add_party(message: types.Message):
    user_id = str(message.from_user.id)

    try:
        await message.delete()
    except Exception:
        pass

    if user_id in users_db:
        user = users_db[user_id]
        # Сохраняем ID нового сообщения с данными
        sent_message = await message.answer(f"{user['nickname']} Тег:{user['tag']}")
        
        # Обновляем ID сообщения в базе
        users_db[user_id]['last_msg_id'] = sent_message.message_id
        save_users(users_db)
        return

    input_text = message.text[5:].strip()
    nickname, tag = parse_registration(input_text)
    
    if not nickname or not tag:
        await message.answer(
            "❌ Неверный формат. Используйте команду с пробелом:\n"
            "<code>+пати Никнейм Тег:ваш_тег</code>\n\n"
            "Пример: <code>+пати Shrek Тег:qr2pk</code>"
        )
        return

    users_db[user_id] = {
        "nickname": nickname,
        "tag": tag
    }
    save_users(users_db)

    sent_message = await message.answer(
        f"✅ Регистрация прошла успешно!\n"
        f"{nickname} Тег:{tag}"
    )
    
    # Сохраняем ID сообщения для будущего удаления
    users_db[user_id]['last_msg_id'] = sent_message.message_id
    save_users(users_db)

@dp.message(F.text.startswith("-пати"))
async def cmd_remove_party(message: types.Message):
    user_id = str(message.from_user.id)

    try:
        await message.delete()
    except Exception:
        pass

    if user_id in users_db and 'last_msg_id' in users_db[user_id]:
        # Удаляем конкретное сообщение бота по его ID
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=users_db[user_id]['last_msg_id'])
        except Exception:
            # Если сообщение уже удалено или не найдено
            pass
        
        # Опционально: удаляем ID из базы, чтобы нельзя было удалить его дважды
        del users_db[user_id]['last_msg_id']
        save_users(users_db)
    else:
        await message.answer("❗ У вас нет активного сообщения для удаления или вы не зарегистрированы.")

# Админские команды (если нужны)

@dp.message(Command("admin_export"))
async def cmd_export(message: types.Message):
    if message.from_user.id not in {6723183204}:
        return

    if not users_db:
        await message.answer("База пуста.")
        return

    text = "📋 БАЗА РЕГИСТРАЦИЙ:\n\n"
    for user_id, data in users_db.items():
        text += f"ID: <code>{user_id}</code> | {data['nickname']} Тег:{data['tag']}\n"
        
    await message.answer(text)

@dp.message(Command("admin_clear"))
async def cmd_clear(message: types.Message):
    if message.from_user.id not in {6723183204}:
        return

    users_db.clear()
    save_users(users_db)
    await message.answer("✅ База очищена.")

async def on_startup(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)

async def main():
    await dp.start_polling(bot, on_startup=on_startup)

if __name__ == "__main__":
    asyncio.run(main())
