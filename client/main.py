import os
import logging
import asyncio
import aiofiles
from aiogram import Bot, Dispatcher, types
import requests
from aiogram.filters import CommandStart, Command
import aiohttp
from aiogram.types import FSInputFile



TOKEN = "7458164131:AAFARdF09zU1p5QI8V5HP5V-SDKJ-uUxYq0"
API_URL = "http://127.0.0.1:8000/bot/create_user/"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logger = logging.getLogger(__name__)

async def download_voice_file(file_id: str) -> str:
    file = await bot.get_file(file_id)
    file_path = f"temp/{file_id}.ogg"
    await bot.download_file(file.file_path, file_path)
    logger.info(f"Voice file saved: {file_path}")
    return file_path

async def download_audio_from_url(url: str, filename: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(filename, "wb") as f:
                    await f.write(await resp.read())
                return filename
    raise Exception(f"Failed to download audio from {url}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я голосовой ассистент. Отправь мне сообщение или голос!")

@dp.message()
async def handle_message(message: types.Message):
    try:
        content = message.text
        is_audio = False
        audio_path = None

        if message.content_type == "voice":
            audio_path = await download_voice_file(message.voice.file_id)
            is_audio = True
            content = None

        files = None
        if audio_path:
            file_handle = open(audio_path, 'rb')
            files = {'audio': (os.path.basename(audio_path), file_handle)}

        logger.info(f"Sending request to {API_URL}, is_audio={is_audio}")
        response = requests.post(
            API_URL,
            data={
                "user_id": message.from_user.id,
                "user_name": message.from_user.first_name,
                "role": "user",
                "content": content,
                "is_audio": is_audio
            },
            files=files
        )

        if audio_path and files:
            files['audio'][1].close()

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Temp file removed: {audio_path}")

        if response.status_code in (200, 201):
            try:
                data = response.json()

            except ValueError:
                await message.answer("Ошибка. Попробуйте позже.")
                logger.error(f"Invalid JSON response from server: {response.text}")
                return

            if "error" in data and data["error"]:
                await message.answer(f"Ошибка сервера: {data.get('message', 'Неизвестная ошибка')}")
                logger.error(f"Server error: {data}")
                return

            if "reply" in data:
                if data.get("is_audio", False) and "audio_url" in data:
                    audio_url = data["audio_url"]
                    audio_response_path = "temp/response.mp3"
                    try:
                        await download_audio_from_url(audio_url, audio_response_path)
                        await message.answer_voice(FSInputFile(audio_response_path))
                        os.unlink(audio_response_path)
                    except Exception as e:
                        logger.error(f"Failed to handle audio response: {e}", exc_info=True)
                        await message.answer("Не удалось отправить голосовое сообщение.")
                else:
                    if data["reply"]:
                        await message.answer(data["reply"])
            else:
                await message.answer(f"В ответе сервера нет поля 'reply': {data}")
        else:
            await message.answer(f"Ошибка сервера: {response.status_code}")
            logger.error(f"Server returned {response.status_code}: {response.text}")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке запроса")

async def main():
    if not os.path.exists("temp"):
        os.makedirs("temp")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


