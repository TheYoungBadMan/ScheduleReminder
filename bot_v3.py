import asyncio
import logging
import os
import sqlite3
import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.filters.state import State, StatesGroup
from aiogram.types.bot_command import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

scheduler = AsyncIOScheduler(timezone="Asia/Almaty")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# открытие conn

conn = sqlite3.connect("students.db")


# Определение состояний
class RegistrationState(StatesGroup):
    course = State()
    group = State()


class SetTimeState(StatesGroup):
    time = State()


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = await get_user(str(message.from_user.id))
    if user_id:
        await message.answer("Вы уже зарегистрированы!")
    else:
        await message.answer("Пройдите регистрацию")
        # Выбор курса
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="1", callback_data="course_1"),
                    types.InlineKeyboardButton(text="2", callback_data="course_2"),
                    types.InlineKeyboardButton(text="3", callback_data="course_3"),
                    types.InlineKeyboardButton(text="4", callback_data="course_4")
                ]
            ]
        )

        # Отправьте сообщение с инлайн-клавиатурой
        await message.answer("Выберите свой курс", reply_markup=kb)

        await state.set_state(RegistrationState.course)


@dp.callback_query(lambda c: c.data.startswith('course'))
async def choose_course(query: types.CallbackQuery, state: FSMContext):
    # Извлеките номер курса из данных обратного вызова
    course = int(query.data.split('_')[1])

    await state.update_data(course=course)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="ВМ", callback_data="group_ВМ"),
                types.InlineKeyboardButton(text="ММ", callback_data="group_ММ"),
                types.InlineKeyboardButton(text="Э", callback_data="group_Э"),
                types.InlineKeyboardButton(text="ФФ", callback_data="group_ФФ"),
                types.InlineKeyboardButton(text="ГГ", callback_data="group_ГГ")
            ]
        ]
    )

    await query.message.delete()

    await query.message.answer("Выберите свою группу", reply_markup=kb)

    await state.set_state(RegistrationState.group)


@dp.callback_query(lambda c: c.data.startswith('group'))
async def choose_group(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    course = data['course']
    group = query.data.split('_')[1]

    await add_user(str(query.from_user.id), course, group)

    await query.message.delete()

    await query.message.answer(f"Поздравляю! Вы успешно прошли регистрацию.\n"
                               f"Ваши данные:\n"
                               f"Course - {course}\n"
                               f"Group - {group}",
                               reply_markup=types.ReplyKeyboardRemove(),
                               )


# Хэндлер на команду /restart
@dp.message(Command("restart"))
async def cmd_reregistration(message: types.Message, state: FSMContext):
    await delete_user(str(message.from_user.id))
    await cmd_start(message, state)


# Добавление функции удаления пользователя
async def delete_user(user_id: str):
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    cur.close()


# Хэндлер на команду /set_time
@dp.message(Command("set_time"))
async def cmd_set_time(message: types.Message, state: FSMContext):
    await message.answer("Введите время в формате ЧЧ:ММ (например, 18:30):")
    await state.set_state(SetTimeState.time)  # Переход в состояние ожидания времени


# Хэндлер для получения времени от пользователя
@dp.message(SetTimeState.time)
async def set_time(message: types.Message, state: FSMContext):
    try:
        # Пытаемся преобразовать введенное время пользователя в объект datetime.time
        time = message.text.split(':')
        hour = time[0]
        minute = time[1]

        user_id = str(message.from_user.id)

        user_id, course, group, _, _, job_id = await get_user(user_id)

        await delete_job(user_id)
        scheduler.remove_job(job_id)
        job = scheduler.add_job(
            send_file,
            'cron',
            day_of_week='wed',
            hour=hour,
            minute=minute,
            args=[user_id, course, group]
        )
        await save_job(user_id, job.id, hour, minute)

        await message.answer(f"Время установлено на {hour}:{minute}")

    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 18:30)")

    finally:
        # Сбрасываем состояние FSM
        await state.clear()


# Обновленный хэндлер на команду /help с использованием инлайн-кнопок
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = "Доступные команды:\n" \
                "/start - начать процесс регистрации\n" \
                "/restart - зарегистрироваться заново\n" \
                "/send - отправить файл с расписанием (требуется предварительная регистрация)\n" \
                "/set_time - установить время отправки файла с расписанием"

    # Создаем инлайн-кнопку для вызова /set_time
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="Установить время", callback_data="set_time")
        ]]
    )

    await message.answer(help_text, reply_markup=keyboard)


# Проверка на наличие пользователя
async def get_user(user_id: str):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    # cur.execute(f"SELECT * FROM users WHERE user_id = {user_id}")
    return cur.fetchone()


async def add_user(user_id: str, course: int, group: str):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users
            (user_id, course, group_name, hour, minute)
            VALUES (?, ?, ?, ?, ?) 
    """, (user_id, course, group, '12', '00'))
    conn.commit()
    cur.close()


async def get_users():
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    return cur.fetchall()


async def save_job(user_id: str, job_id: str, hour: str, minute: str):
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET job_id = ?, hour = ?, minute = ?
        WHERE user_id = ?
    """, (job_id, hour, minute, user_id))
    conn.commit()
    cur.close()


async def delete_job(user_id: str):
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET job_id = NULL
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    cur.close()


async def send_file(user_id: str, course: int, group: str):
    file_name = f"schedule/course_{course}/{group}-{course}1.doc"
    await bot.send_document(user_id, types.FSInputFile(path=file_name))


# Хэндлер на команду /send
@dp.message(Command("send"))
async def cmd_send_file(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = await get_user(user_id)

    if not user_data:
        await message.answer("Вы не зарегистрированы! Используйте команду /start для регистрации.")
        return

    course, group = user_data[1], user_data[2]
    file_name = f"schedule/course_{course}/{group}-{course}1.doc"
    await bot.send_document(user_id, types.FSInputFile(path=file_name))
    await message.answer("Файл с расписанием отправлен.")


# Запуск процесса поллинга новых апдейтов
async def main():
    scheduler.start()

    for user_id, course, group, hour, minute, _ in await get_users():
        job = scheduler.add_job(
            send_file,
            'cron',
            day_of_week='wed',
            hour=hour,
            minute=minute,
            args=[user_id, course, group]
        )
        print(job)
        await save_job(user_id, job.id, hour, minute)

    await bot.set_my_commands(
        commands=[
            BotCommand(command='help', description='Help'),
            BotCommand(command='start', description='Start'),
            BotCommand(command='set_time', description='Устанавливает время отправки расписания'),
            BotCommand(command='restart', description='Повторная регистрация')
        ]
    )

    await dp.start_polling(bot)


# Планирование отправки файла в выбранное время
# scheduler.add_job(send_file, "cron", day_of_week="sat", hour=0, minute=6)

# поминутная отправка
# scheduler.add_job(send_file, "interval", minutes=1)

if __name__ == "__main__":
    asyncio.run(main())
