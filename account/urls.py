from django.urls import path
from .views import SignUpView, LogoutView, LogInView

app_name = 'account'

urlpatterns = [
    path("signup/", SignUpView.as_view()),
    path("login/", LogInView.as_view()),
    path("logout/", LogoutView.as_view()),
]