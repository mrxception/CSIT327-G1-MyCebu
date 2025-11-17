from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name="register"),
    path('login/', views.login_view, name="login"),
    path('register-success/', views.register_success_view, name='register_success'),
]
