from django.urls import path
from .views import SignUpView, LogoutView, LogInView, ProfileView

app_name = 'account'

urlpatterns = [
    path("signup/", SignUpView.as_view()),
    path("login/", LogInView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("<int:user_id>/", ProfileView.as_view()),  # Assuming this is a typo and should be "profile"
]