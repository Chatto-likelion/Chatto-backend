from django.urls import path
from .views import BusChatView, BusChatDetailView, BusChatAnalyzeView, BusResultListView, BusResultDetailView

app_name = 'play'

urlpatterns = [
    path('chat/', BusChatView.as_view()),
    path('chat/<int:chat_id>/delete', BusChatDetailView.as_view()),  # Assuming you want to delete a specific chat by ID
    path('chat/<int:chat_id>/analyze/', BusChatAnalyzeView.as_view()),  # Assuming you want to analyze a specific chat by ID
    path('analysis/', BusResultListView.as_view()),  # Assuming you want to list analysis results for the logged-in user
    path('analysis/<int:result_id>/detail/', BusResultDetailView.as_view()),  # Assuming you want to get details of a specific analysis result by ID')
]