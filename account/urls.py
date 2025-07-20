from django.urls import path
from .views import SignUpView, LogOutView, LogInView, ProfileView, TokenRefreshView

app_name = 'account'

urlpatterns = [
    path("signup/", SignUpView.as_view()),
    path("login/", LogInView.as_view()),
    path("logout/", LogOutView.as_view()),
    path("profile/", ProfileView.as_view()), 
    path("refresh/", TokenRefreshView.as_view()),
]