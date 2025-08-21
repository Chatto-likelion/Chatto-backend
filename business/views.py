from xmlrpc import client
from django.shortcuts import render

# Create your views here.

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .request_serializers import (
    ChatUploadRequestSerializerBus,
    ChatAnalysisRequestSerializerBus,
)
from .serializers import (
    AnalyseResponseSerializerBus,
    ChatSerializerBus,
    ContribResultSerializerBus,
    ContribAllSerializerBus
)

from .models import (
    ChatBus, 
    ResultBusContrib,
    ResultBusContribSpec,
    ResultBusContribSpecPersonal,
    ResultBusContribSpecPeriod,
)
from rest_framework.parsers import MultiPartParser, FormParser

from django.utils import timezone

import re
from google import genai
from django.conf import settings

from .utils import(
    extract_chat_title,
    count_chat_participants_with_gemini,
    contrib_analysis_with_gemini,
)

# Create your views here.
class BusChatView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    @swagger_auto_schema(
        operation_id="채팅 파일 업로드",
        operation_description="채팅 파일을 업로드합니다.",
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
        responses={201: ChatSerializerBus, 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        serializer = ChatUploadRequestSerializerBus(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data["file"]
            author = request.user
            
            if not author.is_authenticated:
                return Response(status=status.HTTP_401_UNAUTHORIZED,)

            # DB에 먼저 저장해서 경로를 얻는다
            chat = ChatBus.objects.create(
                title="임시 제목",
                file=file,
                people_num=12,  # 임시 값
                user=request.user,
            )

            # 파일 경로에서 제목 추출
            file_path = chat.file.path
            chat.title = extract_chat_title(file_path)

            # 참여 인원 수를 Gemini API로 계산
            num_of_people = count_chat_participants_with_gemini(file_path)
            chat.people_num = num_of_people

            chat.save()

            response = ChatSerializerBus(chat)

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
        responses={200: ChatSerializerBus(many=True), 401: "Unauthorized"},
    )
    def get(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        chats = ChatBus.objects.filter(user=author)
        
        # Serialize the chat data
        chat_data = [
            ChatSerializerBus(chat).data
            for chat in chats
        ]
        return Response(chat_data, status=status.HTTP_200_OK)



class BusChatDetailView(APIView):
    @swagger_auto_schema(
        operation_id="특정 채팅 삭제",
        operation_description="특정 채팅을 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={204: "No Content", 404: "Not Found", 403: "Forbidden", 401: "Unauthorized"},
    )
    def delete(self, request, chat_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            chat = ChatBus.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            chat.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatBus.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND
            )



###################################################################



class BusChatContribAnalyzeView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 기여 분석",
        operation_description="채팅 기여 데이터를 분석합니다.",
        request_body=ChatAnalysisRequestSerializerBus,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={
            201: AnalyseResponseSerializerBus,
            404: "Not Found",
            400: "Bad Request",
            403: "Forbidden",  # If the user does not have permission to analyze the chat
            401: "Unauthorized",  # If the user is not authenticated
        },
    )
    def post(self, request, chat_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED,)
        
        # Validate request data
        serializer = ChatAnalysisRequestSerializerBus(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            chat = ChatBus.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
        except ChatBus.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        project_type=serializer.validated_data["project_type"]
        team_type=serializer.validated_data["team_type"]
        analysis_start = serializer.validated_data["analysis_start"]
        analysis_end = serializer.validated_data["analysis_end"]

        analysis_option = {
            "project_type": project_type,
            "team_type": team_type,
            "start": analysis_start,
            "end": analysis_end,
        }

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        contrib_results = contrib_analysis_with_gemini(client, chat, analysis_option)

        result = ResultBusContrib.objects.create(
            type=1,
            title=chat.title,
            people_num=chat.people_num,
            is_saved=1,
            project_type=project_type,
            team_type=team_type,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            chat=chat,
            num_chat=contrib_results.get("num_chat", 0),
            user=author,
        )

        size = 5 if chat.people_num >= 5 else chat.people_num

        # 1. 전체 요약 분석 결과 (Summary Spec) 저장
        summary_data = contrib_results.get("summary_spec", {})
        spec = ResultBusContribSpec.objects.create(
            result=result,
            total_talks=summary_data.get("total_talks", 0),
            leader=summary_data.get("leader", "N/A"),
            avg_resp=summary_data.get("avg_resp", 0),
            insights=summary_data.get("insights", ""),
            recommendation=summary_data.get("recommendation", ""),
            analysis_size=len(contrib_results.get("personal_specs", [])),
        )

        # 2. 개인별 상세 분석 결과 (Personal Specs) 저장
        personal_specs = contrib_results.get("personal_specs", [])
        for person_data in personal_specs:
            ResultBusContribSpecPersonal.objects.create(
                spec=spec,
                name=person_data.get("name", "N/A"),
                rank=person_data.get("rank", 0),
                type=person_data.get("type", ""),
                participation=person_data.get("participation", 0),
                infoshare=person_data.get("infoshare", 0),
                probsolve=person_data.get("probsolve", 0),
                proposal=person_data.get("proposal", 0),
                resptime=person_data.get("resptime", 0),
            )

        # 3. 기간별 분석 결과 (Periodic Specs) 저장
        periodic_specs = contrib_results.get("periodic_specs", [])
        for period_data in periodic_specs:
            ResultBusContribSpecPeriod.objects.create(
                spec=spec,
                name=period_data.get("name", "N/A"),
                analysis=period_data.get("analysis", ""), # Gemini가 생성한 요약 문장
                period_1=period_data.get("period_1", 0),
                period_2=period_data.get("period_2", 0),
                period_3=period_data.get("period_3", 0),
                period_4=period_data.get("period_4", 0),
                period_5=period_data.get("period_5", 0),
                period_6=period_data.get("period_6", 0),
            )
        
        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )



###################################################################



class BusContribResultDetailView(APIView):
    @swagger_auto_schema(
        operation_id="특정 기여 분석 결과 조회",
        operation_description="특정 기여 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: ContribAllSerializerBus, 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request, result_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ResultBusContrib.objects.get(result_id=result_id)
            if result.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            
            spec = ResultBusContribSpec.objects.get(result=result)
            spec_personals = ResultBusContribSpecPersonal.objects.filter(spec=spec)
            spec_periods = ResultBusContribSpecPeriod.objects.filter(spec=spec)

            payload = {
                "result": result,
                "spec": spec,
                "spec_personal": list(spec_personals),
                "spec_period": list(spec_periods),
            }
            serializer = ContribAllSerializerBus(payload)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="특정 기여 분석 결과 삭제",
        operation_description="특정 기여 분석 결과를 삭제합니다.",
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
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ResultBusContrib.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultBusContrib.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)



###################################################################



class BusResultAllView(APIView):
    @swagger_auto_schema(
        operation_id="모든 분석 결과 조회",
        operation_description="로그인된 유저의 모든 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: "OK", 401: "Unauthorized"},
    )
    def get(self, request):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        contrib_results = ResultBusContrib.objects.filter(user=author)

        contrib_serialized = ContribResultSerializerBus(contrib_results, many=True).data

        combined = contrib_serialized

        results = sorted(combined, key=lambda x: x["created_at"], reverse=True)

        return Response(results, status=status.HTTP_200_OK)
