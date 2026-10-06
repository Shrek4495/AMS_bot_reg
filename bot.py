import asyncio
import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

API_TOKEN = "8968729833:AAGJbrjRAHIrc1VIu7HDWQt8tZbBkOKASis"

# Файлы для хранения данных
MAIN_FILE = "data.txt"
RESERVE_FILE = "reserve.txt"
MAX_PARTICIPANTS = 24

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

participants_list = load_list(MAIN_FILE)
reserve_list = load_list(RESERVE_FILE)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Registration(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_tag = State()

class Reserve(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_tag = State()

def get_main_keyboard(user_id: int):
    in_main = any(p for p in participants_list if p['nickname'] == get_user_nickname(user_id))
    in_reserve = any(r for r in reserve_list if r['nickname'] == get_user_nickname(user_id))

    buttons = []
    if not in_main and not in_reserve:
        buttons.append([types.InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="register_start")])
    
    buttons.append([types.InlineKeyboardButton(text="👥 Посмотреть список", callback_data="show_list")])
    buttons.append([types.InlineKeyboardButton(text="🔄 Перезапустить меню", callback_data="user_restart")])

    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_user_nickname(user_id: int):
    return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.bot.current_state(user=message.from_user.id).clear()
    keyboard = get_main_keyboard(message.from_user.id)
    await message.answer("👋 Добро пожаловать в меню регистрации!", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "user_restart")
async def process_restart(callback: types.CallbackQuery):
    await callback.message.edit_text("🔄 Меню успешно перезапущено.")
    await callback.message.bot.current_state(user=callback.from_user.id).clear()
    keyboard = get_main_keyboard(callback.from_user.id)
    await callback.message.answer("Выберите действие:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "show_list")
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

@dp.callback_query(lambda c: c.data == "register_start")
async def process_register_button(callback: types.CallbackQuery):
    in_main = any(p for p in participants_list if p['nickname'] == get_user_nickname(callback.from_user.id))
    in_reserve = any(r for r in reserve_list if r['nickname'] == get_user_nickname(callback.from_user.id))

    if in_main or in_reserve:
        await callback.message.edit_text("❗ Вы уже зарегистрированы в списке или резерве.")
        return

    await callback.message.edit_text("Введите ваш никнейм:")
    await callback.message.bot.current_state(user=callback.from_user.id).set_state(Registration.waiting_for_nickname)

@dp.message(StateFilter(Registration.waiting_for_nickname))
async def process_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname:
        await message.answer("Никнейм не может быть пустым.")
        return
    await state.update_data(nickname=nickname)
    await message.answer(f"Никнейм: *{nickname}*\n\nТеперь введите ваш тег игрока.", parse_mode="Markdown")
    await state.set_state(Registration.waiting_for_tag)

@dp.message(StateFilter(Registration.waiting_for_tag))
async def process_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip()
    if not tag:
        await message.answer("Тег не может быть пустым.")
        return

    user_data = await state.get_data()
    nickname = user_data.get("nickname")
    participant_number = len(participants_list) + 1

    if participant_number > MAX_PARTICIPANTS:
        await message.answer("Пока вы вводили данные, места закончились. Предлагаю добавить вас в резерв.")
        await add_to_reserve_logic(message, nickname, tag)
        await state.clear()
        keyboard = get_main_keyboard(message.from_user.id)
        await message.answer("Выберите действие:", reply_markup=keyboard)
        return

    if any(p for p in participants_list if p['nickname'] == nickname):
        await message.answer("❗ Никнейм уже занят в основном списке. Попробуйте другой.")
        await state.clear()
        keyboard = get_main_keyboard(message.from_user.id)
        await message.answer("Выберите действие:", reply_markup=keyboard)
        return

    participant_entry = {
        "number": participant_number,
        "nickname": nickname,
        "tag": tag
    }
    participants_list.append(participant_entry)

    with open(MAIN_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{participant_number}. Ник: {nickname}. Тег: {tag}\n")

    await message.answer(f"✅ Регистрация прошла успешно! Вы под номером {participant_number}.")
    await state.clear()
    keyboard = get_main_keyboard(message.from_user.id)
    await message.answer("Выберите действие:", reply_markup=keyboard)

async def add_to_reserve_logic(message: types.Message, nickname=None, tag=None):
    if nickname and tag:
        reserve_number = len(reserve_list) + 1
        reserve_entry = {"number": reserve_number, "nickname": nickname, "tag": tag}
        reserve_list.append(reserve_entry)
        with open(RESERVE_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{reserve_number}. Ник: {nickname}. Тег: {tag}\n")
        await message.answer(f"✅ Вы добавлены в резерв под номером {reserve_number}.")
        return

    await message.answer("Введите ваш никнейм для резервного списка:")
    await message.bot.send_chat_action(message.chat.id, "typing")
    await message.bot.current_state(user=message.from_user.id).set_state(Reserve.waiting_for_nickname)

@dp.callback_query(lambda c: c.data == "reserve_start")
async def reserve_button(callback: types.CallbackQuery):
    await callback.message.edit_text("Введите ваш никнейм для резервного списка:")
    await callback.message.bot.send_chat_action(callback.message.chat.id, "typing")
    await callback.message.bot.current_state(user=callback.from_user.id).set_state(Reserve.waiting_for_nickname)

@dp.message(StateFilter(Reserve.waiting_for_nickname))
async def reserve_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()
    if not nickname:
        await message.answer("Никнейм не может быть пустым.")
        return
    await state.update_data(nickname=nickname)
    await message.answer(f"Никнейм: *{nickname}*\n\nТеперь введите ваш тег игрока.", parse_mode="Markdown")
    await state.set_state(Reserve.waiting_for_tag)

@dp.message(StateFilter(Reserve.waiting_for_tag))
async def reserve_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip()
    if not tag:
        await message.answer("Тег не может быть пустым.")
        return

    user_data = await state.get_data()
    nickname = user_data.get("nickname")
    reserve_number = len(reserve_list) + 1

    if any(r for r in reserve_list if r['nickname'] == nickname):
        await message.answer("❗ Этот никнейм уже есть в резерве.")
        await state.clear()
        keyboard = get_main_keyboard(message.from_user.id)
        await message.answer("Выберите действие:", reply_markup=keyboard)
        return

    reserve_entry = {"number": reserve_number, "nickname": nickname, "tag": tag}
    reserve_list.append(reserve_entry)

    with open(RESERVE_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{reserve_number}. Ник: {nickname}. Тег: {tag}\n")

    await message.answer(f"✅ Вы добавлены в резерв под номером {reserve_number}.")
    await state.clear()
    
    keyboard = get_main_keyboard(message.from_user.id)
    await message.answer("Выберите действие:", reply_markup=keyboard)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
