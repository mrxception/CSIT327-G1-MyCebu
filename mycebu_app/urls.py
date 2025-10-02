from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('landing/', views.landing_view, name='landing'),
    path('register/', views.register_view, name="register"),
    path('login/', views.login_view, name="login"),
    path('test/', views.chatbot_page, name='chatbot_page'),
    path('chat/', views.chat_view, name='chat_view'),
    # path('logout/', LogoutView.as_view(), name='logout'),
    # path('register/', views.register, name='register'),
    # path('dashboard/', views.dashboard, name='dashboard'),
]