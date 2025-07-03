from django.urls import path
from .views import BusChatUploadView, BusChatListView, BusChatDetailView, BusChatAnalyzeView, BusResultListView, BusResultDetailView

app_name = 'business'

urlpatterns = [
    path('chat/', BusChatUploadView.as_view()),
    path('chat/<int:user_id>/', BusChatListView.as_view()),  # Assuming you want to list chats for a specific user
    path('chat/<int:chat_id>/delete', BusChatDetailView.as_view()),  # Assuming you want to delete a specific chat by ID
    path('chat/<int:chat_id>/analyze/', BusChatAnalyzeView.as_view()),  # Assuming you want to analyze a specific chat by ID
    
    path('analysis/<int:user_id>/', BusResultListView.as_view()),  # Assuming you want to list analysis results for a specific user
    path('analysis/<int:result_id>/detail/', BusResultDetailView.as_view()),  # Assuming you want to get details of a specific analysis result by ID')
]