from .models import Message, MessageHistory
from asgiref.sync import sync_to_async
from django.db import close_old_connections

class MessageProcessor:
    def __init__(self, user):
        self.user = user
        self._history = None

    async def get_history(self):
        if not self._history:
            self._history = await sync_to_async(lambda: self.user.history)()
        return self._history

    async def process_text(self, text: str, is_audio: bool = False):
        # Получаем историю асинхронно
        history = await self.get_history()

        # Сохраняем входящее сообщение
        await self.save_message(history, 'user', text, is_audio)

        # Получаем контекст для ИИ
        context = await self.get_context(history)

        # Генерируем ответ
        response_text = f"Вы сказали: {text}"

        # Сохраняем ответ ассистента
        await self.save_message(history, 'assistant', response_text)

        return response_text

    @staticmethod
    async def save_message(history, role: str, content: str, is_audio: bool = False):
        """Асинхронное сохранение сообщения"""
        # Используем sync_to_async для обертки синхронной операции
        await sync_to_async(Message.objects.create)(
            history=history,
            role=role,
            content=content,
            is_audio=is_audio
        )
        close_old_connections()  # Закрываем соединения

    @staticmethod
    async def get_context(history, max_messages=10):
        """Асинхронное получение контекста"""
        # Получаем QuerySet асинхронно
        qs = await sync_to_async(Message.objects.filter)(history=history)
        # Применяем сортировку и ограничение
        qs = qs.order_by('-created_at')[:max_messages]
        # Преобразуем в список
        messages = await sync_to_async(list)(qs)

        return [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

    @staticmethod
    async def text_to_speech(text: str) -> bytes:
        """Заглушка для конвертации текста в аудио"""
        # Временная реализация - возвращаем пустые байты
        return b''

