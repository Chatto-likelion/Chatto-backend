from django.urls import path
from .views import (
    PlayChatView, 
    PlayChatDetailView, 
    PlayChatChemAnalyzeView, 
    PlayChatSomeAnalyzeView,
    PlayChatMBTIAnalyzeView,
    PlayChemResultDetailView,
    PlaySomeResultDetailView,
    PlayMBTIResultDetailView,
    PlayResultAllView,
)
app_name = 'play'

urlpatterns = [
    path('chat/', PlayChatView.as_view()),
    path('chat/<int:chat_id>/delete/', PlayChatDetailView.as_view()),  
    path('chat/<int:chat_id>/analyze/chem/', PlayChatChemAnalyzeView.as_view()),  
    path('chat/<int:chat_id>/analyze/some/', PlayChatSomeAnalyzeView.as_view()),
    path('chat/<int:chat_id>/analyze/mbti/', PlayChatMBTIAnalyzeView.as_view()),  
    # path('analysis/chem/', PlayChemResultListView.as_view()), 
    # path('analysis/some/', PlaySomeResultListView.as_view()),
    # path('analysis/mbti/', PlayMBTIResultListView.as_view()), 
    path('analysis/chem/<int:result_id>/detail/', PlayChemResultDetailView.as_view()), 
    path('analysis/some/<int:result_id>/detail/', PlaySomeResultDetailView.as_view()), 
    path('analysis/mbti/<int:result_id>/detail/', PlayMBTIResultDetailView.as_view()), 
    path('analysis/all/', PlayResultAllView.as_view()),  
]