from django.urls import path

from .views import ChatView, ChatListView, ChatDetailView, ChatAnalyzeView

app_name = 'play'

urlpatterns = [
    path('chats/', ChatView.as_view()),
    path('chats/<int:user_id>/', ChatListView.as_view()),
    path('chats/<int:chat_id>/delete/', ChatDetailView.as_view()),
    path('chats/<int:chat_id>/analyze/', ChatAnalyzeView.as_view()),
]