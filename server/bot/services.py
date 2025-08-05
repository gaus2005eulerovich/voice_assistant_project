import json
import logging
import requests
from .models import Message
from asgiref.sync import sync_to_async
from django.db import close_old_connections

logger = logging.getLogger(__name__)

PERPLEXITY_API_KEY = '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'
PERPLEXITY_URL = 'https://api.perplexity.ai/chat/completions'


class MessageProcessor:
    def __init__(self, user):
        self.user = user
        self._history = None

    async def get_history(self):
        if not self._history:
            self._history = await sync_to_async(lambda: self.user.history)()
        return self._history

    async def process_text(self, text: str, is_audio: bool = False):
        history = await self.get_history()
        context = await self.get_context(history)

        while context and context[-1]['role'] == 'user':
            context.pop()
        context.append({"role": "user", "content": text})

        try:
            response_text = await self.ask_perplexity(context)
            await self.save_message(history, 'user', text, is_audio)
            await self.save_message(history, 'assistant', response_text)
        except Exception as e:
            logger.error(f"Ошибка при вызове Perplexity API: {e}")
            response_text = "Произошла ошибка при получении ответа от нейросети."

        return response_text

    @staticmethod
    async def save_message(history, role: str, content: str, is_audio: bool = False):
        await sync_to_async(Message.objects.create)(
            history=history,
            role=role,
            content=content,
            is_audio=is_audio
        )
        close_old_connections()

    @staticmethod
    async def get_context(history, max_messages=10):
        qs = await sync_to_async(Message.objects.filter)(history=history)
        qs = qs.order_by('-created_at')[:max_messages]
        messages = await sync_to_async(list)(qs)
        valid_messages = [msg for msg in messages if msg.content and isinstance(msg.content, str)]
        return [{"role": msg.role, "content": msg.content} for msg in reversed(valid_messages)]


    @staticmethod
    async def ask_perplexity(context):
        print("Context to Perplexity:", context)
        data = {
            "model": "sonar-pro",
            "messages": context if context else [{"role": "user", "content": "Привет!"}]
        }
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
            "accept": "application/json",
        }

        def sync_call():
            logger.info(f"\n=== ОТПРАВЛЯЮ ЗАПРОС К Perplexity API ===\n{json.dumps(data, ensure_ascii=False, indent=2)}")
            try:
                resp = requests.post(PERPLEXITY_URL, headers=headers, json=data, timeout=60)
            except Exception as exc:
                logger.error(f"Ошибка при отправке запроса к Perplexity: {exc}", exc_info=True)
                raise

            logger.info(f"=== ОТВЕТ ОТ Perplexity ===\nКод: {resp.status_code}\nТело:\n{resp.text}")

            if resp.status_code >= 400:
                try:
                    err_json = resp.json()
                    logger.error(f"Ошибка Perplexity API: {err_json}")
                except Exception:
                    logger.error(f"Ошибка Perplexity без JSON: {resp.text}")
                resp.raise_for_status()

            try:
                json_resp = resp.json()
            except Exception as e:
                logger.error(f"Ошибка парсинга JSON ответа: {e}", exc_info=True)
                raise

            if "choices" not in json_resp or not json_resp["choices"]:
                logger.error(f"Неверный формат ответа API: {json_resp}")
                raise ValueError(f"Неверный формат ответа API: {json_resp}")

            return json_resp["choices"][0]["message"]["content"]

        return await sync_to_async(sync_call)()


