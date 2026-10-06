import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

API_TOKEN = "8968729833:AAGJbrjRAHIrc1VIu7HDWQt8tZbBkOKASis"

# Файл для хранения данных
DATA_FILE = "data.txt"

# Проверяем, есть ли файл с данными, и считываем его
participants_list = []
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            # Формат строки в файле: 1. Ник: Shrek. Тег: 2fj68
            parts = line.strip().split('. ')
            if len(parts) > 1:
                info = parts[1].split('. Тег: ')
                if len(info) == 2:
                    participants_list.append({
                        "number": i,
                        "nickname": info[0].replace('Ник: ', ''),
                        "tag": info[1]
                    })

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Registration(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_tag = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Зарегистрироваться", callback_data="register_start")]
    ])
    await message.answer("Нажмите кнопку для регистрации.", reply_markup=keyboard)

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

    participant_entry = {
        "number": participant_number,
        "nickname": nickname,
        "tag": tag
    }
    
    participants_list.append(participant_entry)

    # ЗАПИСЬ В ФАЙЛ (самое важное изменение)
    with open(DATA_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{participant_number}. Ник: {nickname}. Тег: {tag}\n")

    final_text = f"✅ Регистрация прошла успешно!\n\nВы под номером {participant_number}.\nНик: {nickname}\nТег: {tag}"
    await message.answer(final_text)
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
