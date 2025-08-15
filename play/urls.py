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
    PlayChemQuizView,
    PlayChemQuizQuestionListDetailView,
    PlayChemQuizQuestionListView,
    PlayChemQuizStartView,
    # PlayChemQuizSolveDetailView,
    # PlayChemQuizSubmissionView,
    PlayChemQuizResultListView,
    PlayChemQuizPersonalView,
    PlayChemQuizModifyView,
    PlayChemQuizSubmitView,
)
app_name = 'play'

urlpatterns = [
    path('chat/', PlayChatView.as_view()),
    path('chat/<int:chat_id>/', PlayChatDetailView.as_view()),
    path('chat/<int:chat_id>/analyze/chem/', PlayChatChemAnalyzeView.as_view()),  
    path('chat/<int:chat_id>/analyze/some/', PlayChatSomeAnalyzeView.as_view()),
    path('chat/<int:chat_id>/analyze/mbti/', PlayChatMBTIAnalyzeView.as_view()),  
    path('analysis/chem/<int:result_id>/detail/', PlayChemResultDetailView.as_view()), 
    path('analysis/some/<int:result_id>/detail/', PlaySomeResultDetailView.as_view()), 
    path('analysis/mbti/<int:result_id>/detail/', PlayMBTIResultDetailView.as_view()), 
    path('analysis/all/', PlayResultAllView.as_view()),  

    path("quiz/chem/<int:result_id>", PlayChemQuizView.as_view()),
    path("quiz/chem/<int:result_id>/questions/", PlayChemQuizQuestionListView.as_view()),
    path("quiz/chem/<int:result_id>/questions/detail/", PlayChemQuizQuestionListDetailView.as_view()),
    path('quiz/chem/<int:result_id>/start/', PlayChemQuizStartView.as_view()),
    path('quiz/chem/<int:result_id>/personal/<str:name>/', PlayChemQuizPersonalView.as_view()),
    path('quiz/chem/<int:result_id>/result/', PlayChemQuizResultListView.as_view()),
    path('quiz/chem/<int:result_id>/modify/<int:question_index>', PlayChemQuizModifyView.as_view()),
    path('quiz/chem/<int:result_id>/submit/<str:name>', PlayChemQuizSubmitView.as_view()),
]