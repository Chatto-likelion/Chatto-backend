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

from business.request_serializers import (
    ChatUploadRequestSerializer,
    ChatAnalysisRequestSerializer,
)
from business.serializers import (
    UploadResponseSerializer,
    ListResponseSerializer,
    UploadResponseSerializer,
    AnalyseResponseSerializer,
)
from business.serializers import AllResultSerializer, DetailResultSerializer
from business.models import Chat

from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import logout

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication

from rest_framework.parsers import MultiPartParser, FormParser

from .models import ResultBusContrib
from django.utils import timezone

import re


def extract_chat_title(path: str) -> str:
    """
    텍스트 파일 path의 첫 줄에서
    “~님과” 앞부분만 가져옵니다.
    """
    with open(path, "r", encoding="utf-8") as f:
        first_line = (
            f.readline().strip()
        )  # ex: "🦁멋사 13기 잡담방🦁 님과 카카오톡 대화"

    # '(.*?)' : 가능한 한 짧게 매칭, '님과' 앞까지 캡쳐
    match = re.match(r"^(.*?)\s*님과", first_line)
    if match:
        return match.group(1)
    else:
        # “님과” 패턴이 없으면 줄 전체를 리턴하거나 빈 문자열
        return first_line


# Create your views here.
class BusChatView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    @swagger_auto_schema(
        operation_description="채팅 파일 업로드",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
            openapi.Parameter(
                "file",
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="업로드할 채팅 파일",
            ),
        ],
        responses={201: UploadResponseSerializer, 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        serializer = ChatUploadRequestSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data["file"]
            author = request.user
            
            if not author.is_authenticated:
                return Response(
                    {"error": "User not authenticated"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # DB에 먼저 저장해서 경로를 얻는다
            chat = Chat.objects.create(
                title="임시 제목",
                content=file,
                people_num=12,  # 임시 값
                user=request.user,
            )

            # 파일 경로에서 제목 추출
            file_path = chat.content.path
            chat.title = extract_chat_title(file_path)
            chat.save()

            response = UploadResponseSerializer(
                {"chat_id": chat.chat_id}
            )
            return Response(response.data, status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_id="채팅 목록 조회",
        operation_description="로그인된 유저의 채팅 목록을 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: ListResponseSerializer(many=True), 404: "Not Found", 401: "Unauthorized"},
    )
    def get(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        chats = Chat.objects.filter(user=author)
        if not chats:
            return Response(
                {"error": "No chats found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Serialize the chat data
        chat_data = [
            {
                "chat_id": chat.chat_id,
                "title": chat.title,
                "people_num": chat.people_num,
                "uploaded_at": chat.updated_at,
            }
            for chat in chats
        ]
        return Response(chat_data, status=status.HTTP_200_OK)



class BusChatDetailView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 삭제",
        operation_description="채팅을 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={204: "No Content", 404: "Not Found", 400: "Bad Request"},
    )
    def delete(self, request, chat_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        try:
            chat = Chat.objects.get(chat_id=chat_id, user=author)
            chat.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND
            )


class BusChatAnalyzeView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 분석",
        operation_description="채팅 데이터를 분석합니다.",
        request_body=ChatAnalysisRequestSerializer,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={
            200: AnalyseResponseSerializer,
            404: "Not Found",
            400: "Bad Request",
            403: "Forbidden"  # If the user does not have permission to analyze the chat
        },
    )
    def post(self, request, chat_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Validate request data
        serializer = ChatAnalysisRequestSerializer(data=request.data)
        if serializer.is_valid() is False:
            return Response(
                {"error": "Invalid request data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            people_num = serializer.validated_data["people_num"]
            rel = serializer.validated_data["rel"]
            situation = serializer.validated_data["situation"]
            analysis_start = serializer.validated_data["analysis_start"]
            analysis_end = serializer.validated_data["analysis_end"]

        try:
            chat = Chat.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(
                    {"error": "You do not have permission to analyze this chat"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND
            )

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
            chat=chat,
        )

        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )


class BusResultListView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 분석 결과 리스트 조회",
        operation_description="로그인된 유저의 채팅 분석 결과 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: AllResultSerializer, 404: "Not Found", 400: "Bad Request"},
    )
    def get(self, request):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Get all analysis results for the logged-in user
        try:
            results = ResultBusContrib.objects.filter(chat__user = author)
            result_data = [
                {
                    "result_id": result.result_id,
                    "analysis_date": result.analysis_date,
                    "content": result.content,
                    "analysis_type": result.analysis_type,
                    "analysis_date": result.analysis_date,
                }
                for result in results
            ]
            return Response(result_data, status=status.HTTP_200_OK)
        except ResultBusContrib.DoesNotExist:
            return Response(
                {"error": "No analysis results found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )


class BusResultDetailView(APIView):

    @swagger_auto_schema(
        operation_id="분석 결과 조회",
        operation_description="특정 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: DetailResultSerializer, 404: "Not Found", 400: "Bad Request", 401: "Unauthorized"},
    )
    def get(self, request, result_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            result = ResultBusContrib.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(
                    {"error": "You do not have permission to view this analysis result"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response({"content": result.content}, status=status.HTTP_200_OK)
        except ResultBusContrib.DoesNotExist:
            return Response(
                {"error": "Analysis result not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_id="분석 결과 삭제",
        operation_description="특정 분석 결과를 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={204: "No Content", 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
    )
    def delete(self, request, result_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            result = ResultBusContrib.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(
                    {"error": "You do not have permission to delete this analysis result"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultBusContrib.DoesNotExist:
            return Response(
                {"error": "Analysis result not found"}, status=status.HTTP_404_NOT_FOUND
            )
