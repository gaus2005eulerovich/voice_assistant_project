from django.urls import path
from . import views

urlpatterns = [
    #path('webhook/<str:token>/', views.user_handler, name='webhook'),
    path('create_user/', views.user_handler, name='create_user'),
]
