from django.urls import path

from .views import ChatView, ChatListView, ChatDetailView, ChatAnalyzeView
from .views import AnalysisListView, AnalysisDetailView

app_name = 'play'

urlpatterns = [
    path('chats/', ChatView.as_view()),
    path('chats/<int:user_id>/', ChatListView.as_view()),
    path('chats/<int:chat_id>/delete/', ChatDetailView.as_view()),
    path('chats/<int:chat_id>/analyze/', ChatAnalyzeView.as_view()),

    path('analysis/<int:user_id>/', AnalysisListView.as_view()),
    path('analysis/<int:result_id>/detail/', AnalysisDetailView.as_view()),
]