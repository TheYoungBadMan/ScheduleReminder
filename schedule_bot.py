import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup

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


# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
