
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, MessageHistory, Message
import json

@csrf_exempt
def telegram_webhook(request, token):
    if request.method == 'POST':
        # Обработка вебхука от Telegram
        data = json.loads(request.body)
        # Ваша логика обработки сообщения
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def create_user(request):
    # Логика создания пользователя
    return JsonResponse({"status": "user created"})

