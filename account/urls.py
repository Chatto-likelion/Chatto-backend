from django.urls import path
from .views import SignUpView, LogOutView, LogInView, ProfileView

app_name = 'account'

urlpatterns = [
    path("signup/", SignUpView.as_view()),
    path("login/", LogInView.as_view()),
    path("logout/", LogOutView.as_view()),
    path("profile/", ProfileView.as_view()),  # Assuming this is a typo and should be "profile"
]