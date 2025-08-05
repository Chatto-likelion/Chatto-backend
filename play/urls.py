from django.urls import path
from .views import (
    PlayChatView, 
    PlayChatDetailView, 
    PlayChatChemAnalyzeView, 
    PlayChatSomeAnalyzeView,
    PlayChatMBTIAnalyzeView,
    PlayChemResultListView, 
    PlaySomeResultListView,
    PlayMBTIResultListView,
    PlayChemResultDetailView,
    PlaySomeResultDetailView,
    PlayMBTIResultDetailView,
)
app_name = 'play'

urlpatterns = [
    path('chat/', PlayChatView.as_view()),
    path('chat/<int:chat_id>/delete/', PlayChatDetailView.as_view()),  # Assuming you want to delete a specific chat by ID
    path('chat/<int:chat_id>/analyze/chem/', PlayChatChemAnalyzeView.as_view()),  # Assuming you want to analyze a specific chat by ID
    path('chat/<int:chat_id>/analyze/some/', PlayChatSomeAnalyzeView.as_view()),
    path('chat/<int:chat_id>/analyze/mbti/', PlayChatMBTIAnalyzeView.as_view()),  # Assuming you want to analyze a specific chat by ID
    path('analysis/chem/', PlayChemResultListView.as_view()),  # Assuming you want to list analysis results for the logged-in user
    path('analysis/some/', PlaySomeResultListView.as_view()),
    path('analysis/mbti/', PlayMBTIResultListView.as_view()),  # Assuming you want to list MBTI analysis results for the logged-in user
    path('analysis/chem/<int:result_id>/detail/', PlayChemResultDetailView.as_view()),  # Assuming you want to get details of a specific analysis result by ID')
    path('analysis/some/<int:result_id>/detail/', PlaySomeResultDetailView.as_view()),  # Assuming you want to get details of a specific analysis result by ID
    path('analysis/mbti/<int:result_id>/detail/', PlayMBTIResultDetailView.as_view()),  # Assuming you want to get details of a specific MBTI analysis result by ID
]