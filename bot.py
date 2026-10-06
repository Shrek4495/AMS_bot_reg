import asyncio
import os
import re
import json
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher.filters import Text

API_TOKEN = "8968729833:AAGJbrjRAHIrc1VIu7HDWQt8tZbBkOKASis"
ADMIN_IDS = {6723183204}  # Замените на свой Telegram ID

# Файлы для хранения данных
MAIN_FILE = "data.txt"
RESERVE_FILE = "reserve.txt"
USERS_FILE = "users.json"
MAX_PARTICIPANTS = 24

# Валидация тега (8 символов: цифры и заглавные латинские буквы)
TAG_REGEX = re.compile(r'^[0-9A-Z]{8}$')

def load_list(filename):
    participants = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                match = re.match(r'(\d+)\. Ник: (.+?)\. Тег: (.+)', line)
                if match:
                    participants.append({
                        "number": int(match.group(1)),
                        "nickname": match.group(2),
                        "tag": match.group(3)
                    })
    return participants

def save_list(filename, data_list):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for item in data_list:
                f.write(f"{item['number']}. Ник: {item['nickname']}. Тег: {item['tag']}\n")
    except IOError as e:
        print(f"Ошибка записи в файл {filename}: {e}")

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# Загрузка данных при старте бота
participants_list = load_list(MAIN_FILE)
reserve_list = load_list(RESERVE_FILE)
users_db = load_users()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Registration(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_tag = State()

class Reserve(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_tag = State()

def get_user_nickname(user_id: int):
    return users_db.get(str(user_id))

def get_main_keyboard(user_id: int):
    user_nick = get_user_nickname(user_id)
    in_main = any(p for p in participants_list if p['nickname'] == user_nick)
    in_reserve = any(r for r in reserve_list if r['nickname'] == user_nick)

    buttons = []
    if not in_main and not in_reserve:
        buttons.append([InlineKeyboardButton(text="📝 В основной список", callback_data="register_start")])
        buttons.append([InlineKeyboardButton(text="➡️ Сразу в резерв", callback_data="reserve_start")])
    
    buttons.append([InlineKeyboardButton(text="👥 Посмотреть список", callback_data="show_list")])
    buttons.append([InlineKeyboardButton(text="🔄 Перезапустить меню", callback_data="user_restart")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def is_admin(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        # В aiogram 2.x статусы — это обычные СТРОКИ
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await dp.current_state(user=message.from_user.id).finish()
    keyboard = get_main_keyboard(message.from_user.id)
    await message.answer("👋 Добро пожаловать в меню регистрации!", reply_markup=keyboard)

@dp.message_handler(commands=["reload"])
async def cmd_reload(message: types.Message):
    if not await is_admin(message):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    global participants_list, reserve_list, users_db
    participants_list = load_list(MAIN_FILE)
    reserve_list = load_list(RESERVE_FILE)
    users_db = load_users()
    await message.answer("✅ Данные перезагружены из файлов.")

@dp.message_handler(commands=["clear"])
async def cmd_clear(message: types.Message):
    if not await is_admin(message):
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    global participants_list, reserve_list, users_db
    participants_list.clear()
    reserve_list.clear()
    users_db.clear()
    
    save_list(MAIN_FILE, participants_list)
    save_list(RESERVE_FILE, reserve_list)
    save_users(users_db)
    
    await message.answer("✅ Все списки и база пользователей очищены.")

@dp.message_handler(commands=["export"])
async def cmd_export(message: types.Message):
    if not await is_admin(message):
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    text = "🏆 ОСНОВНОЙ СОСТАВ:\n"
    if not participants_list:
        text += "Список пуст.\n\n"
    else:
        for p in participants_list:
            text += f"{p['number']}. Ник: {p['nickname']}. Тег: {p['tag']}\n"

    text += "\n---\n\n🛡 РЕЗЕРВНЫЙ СПИСОК:\n"
    if not reserve_list:
        text += "Список пуст."
    else:
        for r in reserve_list:
            text += f"{r['number']}. Ник: {r['nickname']}. Тег: {r['tag']}\n"
            
    await message.answer(text)

@dp.callback_query_handler(lambda c: c.data == "user_restart")
async def process_restart(callback: types.CallbackQuery):
    await callback.message.edit_text("🔄 Меню успешно перезапущено.")
    await dp.current_state(user=callback.from_user.id).finish()
    keyboard = get_main_keyboard(callback.from_user.id)
    await callback.message.answer("Выберите действие:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "show_list")
async def process_show_list(callback: types.CallbackQuery):
    text = "🏆 ОСНОВНОЙ СОСТАВ (24 места):\n"
    if not participants_list:
        text += "Список пуст.\n\n"
    else:
        for p in participants_list:
            text += f"{p['number']}. Ник: {p['nickname']}. Тег: {p['tag']}\n"

    text += "\n---\n\n🛡 РЕЗЕРВНЫЙ СПИСОК:\n"
    if not reserve_list:
        text += "Список пуст."
    else:
        for r in reserve_list:
            text += f"{r['number']}. Ник: {r['nickname']}. Тег: {r['tag']}\n"

    await callback.message.edit_text(text)

@dp.callback_query_handler(lambda c: c.data == "register_start")
async def process_register_button(callback: types.CallbackQuery):
    user_nick = get_user_nickname(callback.from_user.id)
    in_main = any(p for p in participants_list if p['nickname'] == user_nick)
    in_reserve = any(r for r in reserve_list if r['nickname'] == user_nick)

    if in_main or in_reserve:
        await callback.message.edit_text("❗ Вы уже зарегистрированы в списке или резерве.")
        return

    await callback.message.edit_text("Введите ваш никнейм:")
    await dp.current_state(user=callback.from_user.id).set_state(Registration.waiting_for_nickname.state)

@dp.callback_query_handler(lambda c: c.data == "reserve_start")
async def process_reserve_button(callback: types.CallbackQuery):
    user_nick = get_user_nickname(callback.from_user.id)
    in_main = any(p for p in participants_list if p['nickname'] == user_nick)
    in_reserve = any(r for r in reserve_list if r['nickname'] == user_nick)

    if in_main or in_reserve:
        await callback.message.edit_text("❗ Вы уже зарегистрированы в списке или резерве.")
        return

    await callback.message.edit_text("Введите ваш никнейм для резервного списка:")
    await bot.send_chat_action(callback.message.chat.id, "typing")
    await dp.current_state(user=callback.from_user.id).set_state(Reserve.waiting_for_nickname.state)

@dp.message_handler(state=Registration.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname:
        await message.answer("Никнейм не может быть пустым.")
        return
    await state.update_data(nickname=nickname)
    await message.answer(f"Никнейм: *{nickname}*\n\nТеперь введите ваш тег игрока.", parse_mode="Markdown")
    await state.set_state(Registration.waiting_for_tag.state)

@dp.message_handler(state=Registration.waiting_for_tag)
async def process_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip().upper()
    if not tag:
        await message.answer("Тег не может быть пустым.")
        return
    if not TAG_REGEX.match(tag):
        await message.answer("❗ Тег введен неверно. Он должен состоять из 8 цифр и заглавных латинских букв (пример: 1234ABCD).")
        return

    user_data = await state.get_data()
    nickname = user_data.get("nickname")
    user_id = str(message.from_user.id)

    if any(p for p in participants_list if p['nickname'] == nickname):
        await message.answer("❗ Никнейм уже занят в основном списке. Попробуйте другой.")
        await state.finish()
        keyboard = get_main_keyboard(message.from_user.id)
        await message.answer("Выберите действие:", reply_markup=keyboard)
        return

    if any(r for r in reserve_list if r['nickname'] == nickname):
        await message.answer("❗ Этот никнейм уже есть в резерве.")
        await state.finish()
        keyboard = get_main_keyboard(message.from_user.id)
        await message.answer("Выберите действие:", reply_markup=keyboard)
        return

    if len(participants_list) >= MAX_PARTICIPANTS:
        await message.answer("❌ Места в основном составе закончились. Добавляем в резерв.")
        await add_to_reserve_logic(message, nickname, tag)
        await state.finish()
        return

    participant_number = len(participants_list) + 1
    participant_entry = {
        "number": participant_number,
        "nickname": nickname,
        "tag": tag
    }
    participants_list.append(participant_entry)
    
    save_list(MAIN_FILE, participants_list)
    users_db[user_id] = nickname
    save_users(users_db)

    await message.answer(f"✅ Регистрация прошла успешно! Вы под номером {participant_number}.")
    await state.finish()
    keyboard = get_main_keyboard(message.from_user.id)
    await message.answer("Выберите действие:", reply_markup=keyboard)

async def add_to_reserve_logic(message: types.Message, nickname=None, tag=None):
    if nickname and tag:
        reserve_number = len(reserve_list) + 1
        reserve_entry = {"number": reserve_number, "nickname": nickname, "tag": tag}
        reserve_list.append(reserve_entry)
        save_list(RESERVE_FILE, reserve_list)
        
        user_id = str(message.from_user.id)
        users_db[user_id] = nickname
        save_users(users_db)
        
        await message.answer(f"✅ Вы добавлены в резерв под номером {reserve_number}.")
        return

    await message.answer("Введите ваш никнейм для резервного списка:")
    await bot.send_chat_action(message.chat.id, "typing")
    await dp.current_state(user=message.from_user.id).set_state(Reserve.waiting_for_nickname.state)

@dp.message_handler(state=Reserve.waiting_for_nickname)
async def reserve_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname:
        await message.answer("Никнейм не может быть пустым.")
        return
    await state.update_data(nickname=nickname)
    await message.answer(f"Никнейм: *{nickname}*\n\nТеперь введите ваш тег игрока.", parse_mode="Markdown")
    await state.set_state(Reserve.waiting_for_tag.state)

@dp.message_handler(state=Reserve.waiting_for_tag)
async def reserve_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip().upper()
    if not tag:
        await message.answer("Тег не может быть пустым.")
        return
    if not TAG_REGEX.match(tag):
        await message.answer("❗ Тег введен неверно. Он должен состоять из 8 цифр и заглавных латинских букв (пример: 1234ABCD).")
        return

    user_data = await state.get_data()
    nickname = user_data.get("nickname")
    user_id = str(message.from_user.id)

    if any(r for r in reserve_list if r['nickname'] == nickname):
        await message.answer("❗ Этот никнейм уже есть в резерве.")
        await state.finish()
        keyboard = get_main_keyboard(message.from_user.id)
        await message.answer("Выберите действие:", reply_markup=keyboard)
        return

    reserve_number = len(reserve_list) + 1
    reserve_entry = {"number": reserve_number, "nickname": nickname, "tag": tag}
    reserve_list.append(reserve_entry)

    save_list(RESERVE_FILE, reserve_list)
    users_db[user_id] = nickname
    save_users(users_db)

    await message.answer(f"✅ Вы добавлены в резерв под номером {reserve_number}.")
    await state.finish()
    
    keyboard = get_main_keyboard(message.from_user.id)
    await message.answer("Выберите действие:", reply_markup=keyboard)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
