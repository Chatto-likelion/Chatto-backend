from django.shortcuts import render

# Create your views here.
from django.contrib.auth.models import User
from django.contrib import auth
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import login

from business.request_serializers import ChatUploadRequestSerializer, ChatAnalysisRequestSerializer
from business.serializers import UploadResponseSerializer, ListResponseSerializer, UploadResponseSerializer, AnalyseResponseSerializer
from business.serializers import AllResultSerializer , DetailResultSerializer
from business.models import Chat

from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import logout

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication

from rest_framework.parsers import MultiPartParser, FormParser

from .models import ResultBusContrib
from django.utils import timezone



# Create your views here.
class BusChatUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    @swagger_auto_schema(
        operation_description="채팅 파일 업로드",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="유저 ID"
            ),
            openapi.Parameter(
                'file',
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="업로드할 채팅 파일"
            )
        ]
    )
    def post(self, request):
        serializer = ChatUploadRequestSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data["user_id"]
            file = serializer.validated_data["file"]

            # Assuming the file contains chat data in a specific format
            # Here you would parse the file and extract chat details
            # For simplicity, let's assume we create a dummy chat entry
            chat = Chat.objects.create(
                title="Dummy Chat",
                content=file,  
                people_num = 14,  # Assuming one person for now
                user_id=User.objects.get(id=user_id)
            )

            response_serializer = UploadResponseSerializer({"chat_id_bus_contrib": chat.chat_id_bus_contrib})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class BusChatListView(APIView):

    @swagger_auto_schema(
        operation_id="채팅 목록 조회",
        operation_description="채팅 목록을 조회합니다.",
        responses={200: ListResponseSerializer, 404: "Not Found", 400: "Bad Request"},
    )
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            chats = Chat.objects.filter(user_id=user)

            # Serialize the chat data
            chat_data = [{"chat_id_bus_contrib": chat.chat_id_bus_contrib,
                           "title": chat.title,
                           "people_num": chat.people_num,
                           "uploaded_at": chat.updated_at} for chat in chats]
            return Response(chat_data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
class BusChatDetailView(APIView):

    @swagger_auto_schema(
        operation_id="채팅 목록 조회",
        operation_description="채팅 목록을 조회합니다.",
        responses={200: ListResponseSerializer, 404: "Not Found", 400: "Bad Request"},
    )
    def delete(self, request, chat_id):
        try:
            chat = Chat.objects.get(chat_id_bus_contrib=chat_id)
            chat.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)
        
class BusChatAnalyzeView(APIView):
    """
    View to analyze chat data.
    """
    @swagger_auto_schema(
        operation_id="채팅 분석",
        operation_description="채팅 데이터를 분석합니다.",
        request_body=ChatAnalysisRequestSerializer,
        responses={200: AnalyseResponseSerializer, 404: "Not Found", 400: "Bad Request"},
    )
    def post(self, request, chat_id):
        people_num = request.data.get('people_num')
        rel = request.data.get('rel')
        situation = request.data.get('situation')
        analysis_start = request.data.get('analysis_start')
        analysis_end = request.data.get('analysis_end')

        if not all([people_num, rel, situation, analysis_start, analysis_end]):
            return Response(
                {"detail": "[people_num, rel, situation, analysis_start, analysis_end] fields are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            chat = Chat.objects.get(chat_id_bus_contrib=chat_id)
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)
        
        analysis_result_text = (
            f"분석 대상 인원: {people_num}명\n"
            f"관계: {rel}\n"
            f"상황: {situation}\n"
            f"분석 구간: {analysis_start} ~ {analysis_end}"
        )

        result = ResultBusContrib.objects.create(
            content=analysis_result_text,
            is_saved=1,
            analysis_date=timezone.now().date(),
            analysis_type="개인별 기여도 분석",
            chat_id_bus_contrib=chat
        )

        return Response({
            "result_id_bus_contrib": result.result_id_bus_contrib,
        }, status=status.HTTP_201_CREATED) 

class BusResultListView(APIView):

    @swagger_auto_schema(
        operation_id="채팅 분석",
        operation_description="채팅 데이터를 분석합니다.",
        responses={200: AllResultSerializer, 404: "Not Found", 400: "Bad Request"},
    )
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            results = ResultBusContrib.objects.filter(chat_id_bus_contrib__user_id=user)

            result_data = [{"result_id_bus_contrib": result.result_id_bus_contrib,
                            "analysis_date": result.analysis_date,
                            "content": result.content,
                            "analysis_type": result.analysis_type,
                            "analysis_date": result.analysis_date} for result in results]
            return Response(result_data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
class BusResultDetailView(APIView):

    @swagger_auto_schema(
        operation_id="분석 결과 조회",
        operation_description="특정 분석 결과를 조회합니다.",
        responses={200: DetailResultSerializer, 404: "Not Found", 400: "Bad Request"},
    )
    def get(self, request, result_id):
        try:
            result = ResultBusContrib.objects.get(result_id_bus_contrib=result_id)
            
            return Response({"content": result.content}, status=status.HTTP_200_OK)
        except ResultBusContrib.DoesNotExist:
            return Response({"error": "Analysis result not found"}, status=status.HTTP_404_NOT_FOUND)
        
    @swagger_auto_schema(
        operation_id="분석 결과 삭제",
        operation_description="특정 분석 결과를 삭제합니다.",
        responses={204: "No Content", 404: "Not Found"},
    )
    def delete(self, request, result_id):
        try:
            result = ResultBusContrib.objects.get(result_id_bus_contrib=result_id)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultBusContrib.DoesNotExist:
            return Response({"error": "Analysis result not found"}, status=status.HTTP_404_NOT_FOUND)
        


        

