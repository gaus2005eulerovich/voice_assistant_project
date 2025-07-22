from django.db import models

class MessageHistory(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    history = models.OneToOneField(
        MessageHistory,
        on_delete=models.CASCADE,
        related_name='user'
    )
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    history = models.ForeignKey(
        MessageHistory,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    is_audio = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

