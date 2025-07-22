from django.urls import path
from . import views

urlpatterns = [
    path('webhook/<str:token>/', views.telegram_webhook, name='webhook'),
    path('create_user/', views.create_user, name='create_user'),
]
