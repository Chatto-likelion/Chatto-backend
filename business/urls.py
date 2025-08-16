from django.urls import path
from .views import BusChatView, BusChatDetailView, BusChatContribAnalyzeView, BusResultAllView, BusContribResultDetailView

app_name = 'business'

urlpatterns = [
    path('chat/', BusChatView.as_view()),
    path('chat/<int:chat_id>/delete/', BusChatDetailView.as_view()),  
    path('chat/<int:chat_id>/analyze/contrib/', BusChatContribAnalyzeView.as_view()),  
    path('analysis/all/', BusResultAllView.as_view()),  
    path('analysis/<int:result_id>/detail/', BusContribResultDetailView.as_view()),  
]