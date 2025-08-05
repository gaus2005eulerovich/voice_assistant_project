from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, MessageHistory, Message
from .services import MessageProcessor
from asgiref.sync import async_to_sync
import json
import whisper
import tempfile
import os
import pyttsx3
import uuid
from django.conf import settings  # ← ДОБАВЛЕНО


@csrf_exempt
def user_handler(request):
    if request.method != 'POST':
        return JsonResponse({
            'user_id': '',
            'reply': '',
            'error': True,
            'message': 'Метод не поддерживается, используйте POST.'
        })

    telegram_id = request.POST.get('user_id')
    user_name = request.POST.get('user_name')
    role = request.POST.get('role')
    content = request.POST.get('content')
    is_audio = request.POST.get('is_audio', False)

    if is_audio == "True":
        audio_file = request.FILES.get('audio', None)
    else:
        audio_file = None

    if is_audio and audio_file:
        try:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, audio_file.name)
            with open(temp_path, 'wb+') as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)

            print(f"Транскрибируем файл: {temp_path}")
            model = whisper.load_model("small")
            result = model.transcribe(temp_path)
            content = result["text"]
            print(f"Результат транскрипции: '{content}'")

            os.remove(temp_path)
        except Exception as e:
            print(f"Ошибка Whisper: {e}")
            return JsonResponse({
                'error': True,
                'message': f'Ошибка при обработке аудио: {e}'
            })

    if not telegram_id or not user_name:
        return JsonResponse({
            'error': True,
            'message': 'user_id и user_name обязательны.'
        })

    if role not in ('user', 'assistant'):
        return JsonResponse({
            'error': True,
            'message': 'role должен быть "user" или "assistant".'
        })

    if not is_audio and (not content or not isinstance(content, str)):
        return JsonResponse({
            'error': True,
            'message': 'Текстовое сообщение обязательно, если не прислан голос'
        })

    if is_audio and (not content or not isinstance(content, str)):
        return JsonResponse({
            'error': True,
            'message': 'Не удалось распознать текст из голосового сообщения'
        })

    user_exists = User.objects.filter(telegram_id=telegram_id).exists()

    if not user_exists:
        history = MessageHistory.objects.create()
        user, created = User.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                'user_name': user_name,
                'history': history,
            }
        )
    else:
        user, created = User.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                'user_name': user_name,
            }
        )

    processor = MessageProcessor(user)
    try:
        reply = async_to_sync(processor.process_text)(content, is_audio)
    except Exception as e:
        return JsonResponse({
            "error": True,
            "message": f"Ошибка при генерации ответа: {e}"
        })

    def generate_speech_pyttsx3(text):
        try:
            audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio_responses')
            os.makedirs(audio_dir, exist_ok=True)
            audio_file_name = f"{uuid.uuid4().hex}.wav"
            audio_file_path = os.path.join(audio_dir, audio_file_name)

            print(f"Генерируем речь в файл: {audio_file_path}")
            print(f"Текст для генерации: {text}")

            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break

            engine.setProperty('rate', 150)
            engine.save_to_file(text, audio_file_path)
            engine.runAndWait()

            if os.path.exists(audio_file_path):
                print(f"Файл создан: {audio_file_path}")
                return audio_file_path
            else:
                print(f"pyttsx3: файл не создан!")
                raise Exception("pyttsx3 не создал файл")
        except Exception as e:
            print(f"Ошибка при генерации речи: {e}")
            raise

    if is_audio == "True":
        try:
            audio_file_path = generate_speech_pyttsx3(reply)
            if audio_file_path:
                if not os.path.exists(audio_file_path):
                    print(f"Файл {audio_file_path} не найден!")
                else:
                    print(f"Файл {audio_file_path} существует, размер: {os.path.getsize(audio_file_path)} байт")

                relative_path = os.path.relpath(audio_file_path, settings.MEDIA_ROOT)
                audio_url = f"{settings.MEDIA_URL}{relative_path.replace(os.path.sep, '/')}"
                print(f"Audio URL: {audio_url}")

                return JsonResponse({
                    'status': 'created' if created else 'updated',
                    'user_id': user.telegram_id,
                    'reply': '',
                    'is_audio': True,
                    'audio_url': request.build_absolute_uri(audio_url),
                    'error': False
                })
            else:
                return JsonResponse({
                    'status': 'created' if created else 'updated',
                    'user_id': user.telegram_id,
                    'reply': reply,
                    'is_audio': False,
                    'error': False
                })
        except Exception as e:
            print(f"Ошибка TTS: {e}")
            return JsonResponse({
                'status': 'created' if created else 'updated',
                'user_id': user.telegram_id,
                'reply': reply,
                'is_audio': False,
                'error': False
            })
    else:
        return JsonResponse({
            'status': 'created' if created else 'updated',
            'user_id': user.telegram_id,
            'reply': reply,
            'is_audio': False,
            'error': False
        })
