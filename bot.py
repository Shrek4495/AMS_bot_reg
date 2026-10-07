import asyncio
import os
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

API_TOKEN = "8852961042:AAEnZDBLC_61l5hM1e0YJKsyEfw5w8xiw9Q"
ADMIN_ID = 6723183204  # ID админа (оставьте, если нужны /admin_ команды)

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

users_db = load_users()

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ИЗМЕНЕНО: Регистронезависимый поиск тега, допускающий отсутствие пробела
def parse_registration(text: str):
    # Флаг re.IGNORECASE делает поиск нечувствительным к регистру (тег, Тег, ТЕГ)
    tag_match = re.search(r'тег[:\s]*(\S+)', text, re.IGNORECASE)
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
        sent_message = await message.answer(f"{user['nickname']} Тег:{user['tag']}")
        users_db[user_id]['last_msg_id'] = sent_message.message_id
        save_users(users_db)
    else:
        await message.answer("Вы еще не зарегистрированы.")

    await message.answer(
        "ℹ️ <b>Инструкция:</b>\n\n"
        "Чтобы сохранить или обновить свои данные, введите:\n"
        "<code>+пати Никнейм Тег:ваш_тег</code>\n\n"
        "Пример: <code>+пати Shrek Тег:qr2pk</code>\n\n"
        "Чтобы попросить убрать вас с пати:\n"
        "<code>-пати</code>"
    )

@dp.message(F.text.lower().startswith("+пати"))
async def cmd_add_party(message: types.Message):
    user_id = str(message.from_user.id)

    try:
        await message.delete()
    except Exception:
        pass

    if user_id in users_db:
        user = users_db[user_id]
        
        if len(message.text.strip()) <= 5: 
            sent_message = await message.answer(f"{user['nickname']} Тег:{user['tag']}")
            users_db[user_id]['last_msg_id'] = sent_message.message_id
            save_users(users_db)
            return
            
        input_text = message.text[5:].strip()
        nickname, tag = parse_registration(input_text)
        
        if not nickname or not tag:
            await message.answer(
                "❌ Неверный формат. Пример: <code>+пати Shrek тег:qr2pk</code> (регистр и пробел не важны)"
            )
            return

        # Проверка на русские буквы в теге оставлена
        if re.search(r'[а-яА-Я]', tag):
            await message.answer("❌ Тег не может содержать русские буквы.")
            return

        if user['nickname'] == nickname and user['tag'] == tag:
            sent_message = await message.answer(f"{user['nickname']} Тег:{user['tag']}")
            users_db[user_id]['last_msg_id'] = sent_message.message_id
            save_users(users_db)
            return
        else:
            user['nickname'] = nickname
            user['tag'] = tag
            save_users(users_db)
            
            sent_message = await message.answer(
                f"✅ Данные успешно обновлены!\n"
                f"👤 Ник: {nickname}\n"
                f"🏷 Тег: {tag}"
            )
            users_db[user_id]['last_msg_id'] = sent_message.message_id
            save_users(users_db)
            return

    input_text = message.text[5:].strip()
    nickname, tag = parse_registration(input_text)
    
    if not nickname or not tag:
        await message.answer(
            "❌ Неверный формат. Пример: <code>+пати Shrek тег:qr2pk</code> (регистр и пробел не важны)"
        )
        return

    if re.search(r'[а-яА-Я]', tag):
        await message.answer("❌ Тег не может содержать русские буквы.")
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
    
    users_db[user_id]['last_msg_id'] = sent_message.message_id
    save_users(users_db)

@dp.message(F.text.lower().startswith("-пати"))
async def cmd_remove_party(message: types.Message):
    user_id = str(message.from_user.id)

    try:
        await message.delete()
    except Exception:
        pass

    if user_id in users_db:
        user = users_db[user_id]
        
        try:
            await bot.send_message(
                chat_id=message.chat.id, 
                text=f"Пользователь просит убрать его с пати\n"
                     f"👤 Ник: {user['nickname']}\n"
                     f"🏷 Тег: {user['tag']}"
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение: {e}")
        
        if 'last_msg_id' in users_db[user_id]:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=users_db[user_id]['last_msg_id'])
                del users_db[user_id]['last_msg_id']
            except Exception:
                pass
            
        save_users(users_db)
    else:
        await message.answer("❗ Вы не зарегистрированы.")

@dp.message(Command("admin_export"))
async def cmd_export(message: types.Message):
    if message.from_user.id != ADMIN_ID:
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
    if message.from_user.id != ADMIN_ID:
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
