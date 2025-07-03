from django.urls import path
from .views import BusChatUploadView, BusChatListView, BusChatDetailView, BusChatAnalyzeView

app_name = 'business'

urlpatterns = [
    path('chat/', BusChatUploadView.as_view()),
    path('chat/<int:user_id>/', BusChatListView.as_view()),  # Assuming you want to list chats for a specific user
    path('chat/<int:chat_id>/delete', BusChatDetailView.as_view()),  # Assuming you want to delete a specific chat by ID
    path('chat/<int:chat_id>/analyze/', BusChatAnalyzeView.as_view()),  # Assuming you want to analyze a specific chat by ID
]