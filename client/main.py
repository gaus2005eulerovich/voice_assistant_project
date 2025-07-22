import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import requests

# Настройки
TOKEN = os.getenv("7458164131:AAFARdF09zU1p5QI8V5HP5V-SDKJ-uUxYq0")
SERVER_URL = "https://wfxf1i-62-217-184-194.ru.tuna.am"

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я голосовой ассистент. Отправь мне сообщение!")


@dp.message()
async def handle_message(message: types.Message):
    try:
        # Отправляем сообщение на сервер
        response = requests.post(
            SERVER_URL,
            json={
                "text": message.text,
                "user_id": message.from_user.id,
                "username": message.from_user.username
            }
        )

        # Обрабатываем ответ сервера
        if response.status_code == 201:
            await message.answer("Сообщение сохранено на сервере!")
        else:
            await message.answer(f"Ошибка сервера: {response.status_code}")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при обработке запроса")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import asyncio

    asyncio.run(main())


