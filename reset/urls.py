from django.urls import path
from . import views

urlpatterns = [
    path('password-reset-email/', views.password_reset_email_view, name='password_reset_email'),
    path('password-reset-new-password/', views.password_reset_new_password_view, name='password_reset_new_password'),
    path('password-reset-success/', views.password_reset_success_view, name='password_reset_success'),
]
