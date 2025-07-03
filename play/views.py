from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ChatsPlayChem, ResultPlayChem
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser

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


class ChatView(APIView):
    parser_classes = [MultiPartParser, FormParser]  # 반드시 필요

    @swagger_auto_schema(
        operation_description="채팅 파일 업로드",
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_FORM,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="유저 ID",
            ),
            openapi.Parameter(
                "file",
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="업로드할 채팅 파일",
            ),
        ],
    )
    def post(self, request):
        user_id = request.data.get("user_id")
        file = request.FILES.get("file")

        if not user_id or not file:
            return Response(
                {"detail": "[user_id, file] fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chat = ChatsPlayChem.objects.create(
            title="Example Chat Title",
            file=file,
            people_num=2,
            uploaded_at=timezone.now(),
            user_id=user_id,
        )

        file_path = chat.file.path
        chat.title = extract_chat_title(file_path)
        chat.save()

        return Response(
            {"chat_id": chat.chat_id_play_chem, "file_url": chat.file.url},
            status=status.HTTP_201_CREATED,
        )


class ChatListView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="유저 ID",
            )
        ],
        operation_description="특정 사용자의 업로드된 채팅 목록 조회",
    )
    def get(self, request, user_id):
        if not user_id:
            return Response(
                {"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        chats = ChatsPlayChem.objects.filter(user_id=user_id)
        content = [
            {
                "id": chat.chat_id_play_chem,
                "title": chat.title,
                "people_num": chat.people_num,
                "uploaded_at": chat.uploaded_at,
            }
            for chat in chats
        ]
        return Response(content, status=status.HTTP_200_OK)


class ChatDetailView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "chat_id",
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="채팅 ID",
            )
        ],
        operation_description="특정 채팅 삭제",
    )
    def delete(self, request, chat_id):
        try:
            chat = ChatsPlayChem.objects.get(chat_id_play_chem=chat_id)
        except ChatsPlayChem.DoesNotExist:
            return Response(
                {"detail": "Chat not found."}, status=status.HTTP_404_NOT_FOUND
            )

        chat.delete()
        return Response(
            {"detail": "Chat deleted successfully."}, status=status.HTTP_204_NO_CONTENT
        )


class ChatAnalyzeView(APIView):
    @swagger_auto_schema(
        operation_description="채팅 분석 요청",
        manual_parameters=[
            openapi.Parameter(
                "chat_id",
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description="채팅 ID",
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "people_num",
                "rel",
                "situation",
                "analysis_start",
                "analysis_end",
            ],
            properties={
                "people_num": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="대화 참여 인원"
                ),
                "rel": openapi.Schema(type=openapi.TYPE_STRING, description="관계"),
                "situation": openapi.Schema(
                    type=openapi.TYPE_STRING, description="상황 설명"
                ),
                "analysis_start": openapi.Schema(
                    type=openapi.TYPE_STRING, description="분석 시작 시간"
                ),
                "analysis_end": openapi.Schema(
                    type=openapi.TYPE_STRING, description="분석 종료 시간"
                ),
            },
        ),
    )
    def post(self, request, chat_id):
        people_num = request.data.get("people_num")
        rel = request.data.get("rel")
        situation = request.data.get("situation")
        analysis_start = request.data.get("analysis_start")
        analysis_end = request.data.get("analysis_end")

        if not all([people_num, rel, situation, analysis_start, analysis_end]):
            return Response(
                {
                    "detail": "[people_num, rel, situation, analysis_start, analysis_end] fields are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            chat = ChatsPlayChem.objects.get(chat_id_play_chem=chat_id)
        except ChatsPlayChem.DoesNotExist:
            return Response(
                {"detail": f"Chat with id {chat_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        analysis_result_text = (
            f"분석 대상 인원: {people_num}명\n"
            f"관계: {rel}\n"
            f"상황: {situation}\n"
            f"분석 구간: {analysis_start} ~ {analysis_end}"
        )

        result = ResultPlayChem.objects.create(
            content=analysis_result_text,
            is_saved=0,
            analysis_date=timezone.now().date(),
            analysis_type="상황 기반 분석",
            chat_id_play_chem=chat,
        )

        return Response(
            {
                "result_id": result.result_id_play_chem,
                "content": result.content,
                "analysis_type": result.analysis_type,
            },
            status=status.HTTP_201_CREATED,
        )


class AnalysisListView(APIView):
    def get(self, request, user_id):
        analyses = ResultPlayChem.objects.filter(chat_id_play_chem__user_id=user_id)
        content = [
            {
                "result_id": analysis.result_id_play_chem,
                "content": analysis.content,
                "analysis_type": analysis.analysis_type,
            }
            for analysis in analyses
        ]
        return Response(content, status=status.HTTP_200_OK)


class AnalysisDetailView(APIView):
    def get(self, request, result_id):
        try:
            analysis = ResultPlayChem.objects.get(result_id_play_chem=result_id)
        except ResultPlayChem.DoesNotExist:
            return Response(
                {"detail": "Analysis not found."}, status=status.HTTP_404_NOT_FOUND
            )

        content = {
            "result_id": analysis.result_id_play_chem,
            "content": analysis.content,
            "analysis_type": analysis.analysis_type,
            "analysis_date": analysis.analysis_date,
        }
        return Response(content, status=status.HTTP_200_OK)

    def delete(self, request, result_id):
        try:
            analysis = ResultPlayChem.objects.get(result_id_play_chem=result_id)
        except ResultPlayChem.DoesNotExist:
            return Response(
                {"detail": "Analysis not found."}, status=status.HTTP_404_NOT_FOUND
            )

        analysis.delete()
        return Response(
            {"detail": "Analysis deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
