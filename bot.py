import asyncio
import os
import re
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = "8968729833:AAGJbrjRAHIrc1VIu7HDWQt8tZbBkOKASis"
ADMIN_IDS = {6723183204}  # Замените на свой Telegram ID

# Файлы для хранения данных
MAIN_FILE = "data.txt"
RESERVE_FILE = "reserve.txt"
USERS_FILE = "users.json"
MAX_PARTICIPANTS = 24

# Валидация тега (пример для Brawl Stars: 8 символов, цифры и заглавные буквы)
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
                    number = int(match.group(1))
                    nickname = match.group(2)
                    tag = match.group(3)
                    participants.append({
                        "number": number,
                        "nickname": nickname,
                        "tag": tag
                    })
    return participants

def save_list(filename, data_list):
    """Полная перезапись файла для синхронизации с памятью"""
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

# Загрузка данных при старте
participants_list = load_list(MAIN_FILE)
reserve_list = load_list(RESERVE_FILE)
users_db = load_users()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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

    builder = InlineKeyboardBuilder()
    
    if not in_main and not in_reserve:
        builder.button(text="📝 В основной список", callback_data="register_start")
        builder.button(text="➡️ Сразу в резерв", callback_data="reserve_start")
    
    builder.button(text="👥 Посмотреть список", callback_data="show_list")
    builder.button(text="🔄 Перезапустить меню", callback_data="user_restart")
    
    builder.adjust(1)
    return builder.as_markup()

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
    await dp.fsm.clear(user=message.from_user.id)
    keyboard = get_main_keyboard(message.from_user.id)
    await message.answer("👋 Добро пожаловать в меню регистрации!", reply_markup=keyboard)

@dp.message(Command("reload"))
async def cmd_reload(message: types.Message):
    if not await is_admin(message):
