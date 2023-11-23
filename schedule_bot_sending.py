import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
import schedule
import time

logging.basicConfig(level=logging.INFO)
bot = Bot(token="6807889233:AAGliw-1Md2KaaRVIUUvdzmxDS4F1AnmAtA")
dp = Dispatcher()


# Определение состояний
class RegistrationState(StatesGroup):
    course = State()
    group = State()


# Хэндлер на команду /start
@dp.message_handler(Command("start"), state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Пройдите регистрацию")
    await RegistrationState.course.set()


# Хэндлер на выбор курса
@dp.message(state=RegistrationState.course)
async def choose_course(message: types.Message, state: FSMContext):
    await state.update_data(course=message.text)
    await message.answer("Выберите свою группу")
    # Предложение клавиатуры для выбора группы
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton(text="ВМК"))
    kb.add(types.KeyboardButton(text="Эконом"))
    kb.add(types.KeyboardButton(text="ФФ"))
    kb.add(types.KeyboardButton(text="ММ"))
    kb.add(types.KeyboardButton(text="Гео"))
    await message.answer("Выберите свою группу", reply_markup=kb)
    await RegistrationState.group.set()


# Хэндлер на выбор группы
@dp.message(state=RegistrationState.group)
async def choose_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    user_data = await state.get_data()
    await message.answer(f"Спасибо за регистрацию! Вы выбрали курс {user_data['course']} и группу {user_data['group']}")
    # В этом месте вы можете добавить логику сохранения данных о пользователе в базе данных или еще где-то
    # Например, можно использовать ORM, базу данных, файлы и т.д.
    await state.finish()

async def send_file():
    # Замените 'путь к файлу' на путь к директории с вашими файлами
    directory_path = "путь к файлу"
    file_list = os.listdir(directory_path)

    for file_name in file_list:
        # Замените 'путь_к_файлу' на полный путь к файлу
        file_path = os.path.join(directory_path, file_name)

        # Замените 'user_id' на реальный ID пользователя
        user_id = 'user_id'

        # Отправляем файл пользователю
        with open(file_path, 'rb') as file:
            await bot.send_document(user_id, file)

# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)

# Планирование отправки файла каждую субботу в 12:00
schedule.every().saturday.at("12:00").do(asincio.run, send_file())

if __name__ == "__main__":
    asyncio.run(main())
