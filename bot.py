import asyncio
import os
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

# Вспомогательные функции для чтения файлов
def load_list(filename):
    participants = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                parts = line.strip().split('. ')
                if len(parts) > 1:
                    info = parts[1].split('. Тег: ')
                    if len(info) == 2:
                        # Извлекаем номер из начала строки
                        num_part = parts[0]
                        try:
                            number = int(num_part)
                        except ValueError:
                            number = len(participants) + 1
                        participants.append({
                            "number": number,
                            "nickname": info[0].replace('Ник: ', ''),
                            "tag": info[1]
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

# --- КНОПКА СТАРТА И ПРОВЕРКА ЛИМИТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Проверяем основной список
    if len(participants_list) >= MAX_PARTICIPANTS:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Добавить в резерв", callback_data="reserve_start")]
        ])
        await message.answer(
            f"❌ Регистрация окончена. Лимит в {MAX_PARTICIPANTS} участников достигнут.\n\n"
            "Вы можете добавить себя в резервный список.",
            reply_markup=keyboard
        )
    else:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Зарегистрироваться", callback_data="register_start")]
        ])
        await message.answer("Нажмите кнопку для регистрации.", reply_markup=keyboard)

# --- ОСНОВНАЯ РЕГИСТРАЦИЯ ---
@dp.callback_query(lambda c: c.data == "register_start")
async def process_register_button(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваш никнейм:")
    await state.set_state(Registration.waiting_for_nickname)

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

    # Повторная проверка лимита (на случай, если два человека нажали кнопку одновременно)
    if participant_number > MAX_PARTICIPANTS:
        await message.answer("Пока вы вводили данные, места закончились. Предлагаю добавить вас в резерв.")
# Перенаправляем в логику резерва
        await add_to_reserve_logic(message, nickname, tag)
        await state.clear()
        return

    participant_entry = {
        "number": participant_number,
        "nickname": nickname,
        "tag": tag
    }
    participants_list.append(participant_entry)

    # Запись в файл
    with open(MAIN_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{participant_number}. Ник: {nickname}. Тег: {tag}\n")

    await message.answer(f"✅ Регистрация прошла успешно! Вы под номером {participant_number}.")
    await state.clear()

# --- ЛОГИКА РЕЗЕРВА ---
async def add_to_reserve_logic(message: types.Message, nickname=None, tag=None):
    # Если функция вызвана из основной регистрации, ник и тег уже есть
    if nickname and tag:
        reserve_number = len(reserve_list) + 1
        reserve_entry = {"number": reserve_number, "nickname": nickname, "tag": tag}
        reserve_list.append(reserve_entry)
        with open(RESERVE_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{reserve_number}. Ник: {nickname}. Тег: {tag}\n")
        await message.answer(f"✅ Вы добавлены в резерв под номером {reserve_number}.")
        return

    # Если пользователь нажал кнопку "В резерв" сам
    await message.answer("Введите ваш никнейм для резервного списка:")
    await message.bot.send_chat_action(message.chat.id, "typing")

@dp.callback_query(lambda c: c.data == "reserve_start")
async def reserve_button(callback: types.CallbackQuery):
    await callback.message.edit_text("Введите ваш никнейм для резервного списка:")
    await callback.message.bot.send_chat_action(callback.message.chat.id, "typing")
    # Используем состояние резерва
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

    reserve_entry = {"number": reserve_number, "nickname": nickname, "tag": tag}
    reserve_list.append(reserve_entry)

    with open(RESERVE_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{reserve_number}. Ник: {nickname}. Тег: {tag}\n")

    await message.answer(f"✅ Вы добавлены в резерв под номером {reserve_number}.")
    await state.clear()

# --- ПРОСМОТР СПИСКОВ ---
@dp.message(Command("list"))
async def cmd_list(message: types.Message):
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

    await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
