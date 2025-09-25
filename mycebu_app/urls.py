from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name="login"),
    path('register/', views.register_view, name="register"),
    path('login/', views.login_view, name="login"),
    # path('logout/', LogoutView.as_view(), name='logout'),
    # path('register/', views.register, name='register'),
    # path('dashboard/', views.dashboard, name='dashboard'),
]