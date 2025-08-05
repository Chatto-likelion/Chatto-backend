from django.shortcuts import render

# Create your views here.

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .request_serializers import (
    ChatUploadRequestSerializerPlay,
    ChatChemAnalysisRequestSerializerPlay,
    ChatSomeAnalysisRequestSerializerPlay,
    ChatMBTIAnalysisRequestSerializerPlay,
)
from .serializers import (
    AnalyseResponseSerializerPlay,
    ChatSerializerPlay,
    ChemResultSerializerPlay,
    SomeResultSerializerPlay,
    MBTIResultSerializerPlay,
)

from .models import(
    ChatPlay, 
    ResultPlayChem,
    ResultPlaySome,
    ResultPlayMBTI,
)

from rest_framework.parsers import MultiPartParser, FormParser

from django.utils import timezone

import re
from google import genai
from django.conf import settings


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

def count_chat_participants_with_gemini(file_path: str) -> int:
    """
    Gemini API를 사용해 채팅 로그 파일의 참여 인원 수를 계산합니다.
    - file_path: 분석할 채팅 파일의 절대 경로
    - 반환값: 계산된 인원 수 (정수)
    """
    try:
        # 파일이 매우 클 경우를 대비해 앞부분 일부만 읽는 것이 효율적입니다.
        with open(file_path, "r", encoding="utf-8") as f:
            # 여기서는 최대 500줄만 읽도록 제한 (성능 및 비용 최적화)
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        # Gemini API 클라이언트 초기화
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                "당신은 카카오톡 채팅 로그 분석 전문가입니다. \
                주어진 채팅 내용에서 고유한 참여자(사람 이름)가 총 몇 명인지 세어주세요. \
                아래 채팅 내용을 보고, 다른 부가적인 설명은 일절 하지 말고, 오직 최종 인원 수를 나타내는 정수 숫자만 답변해주세요."]
            + [chat_content_sample]
        )

        # Gemini의 응답(e.g., "15" 또는 "총 15명")에서 숫자만 추출하여 정수로 변환
        numbers = re.findall(r'\d+', response.text)
        if numbers:
            return int(numbers[0])
        else:
            # 숫자를 찾지 못한 경우 기본값 반환
            return 1

    except Exception as e:
        # API 호출 실패, 응답 파싱 실패 등 예외 발생 시
        print(f"Gemini로 인원 수 분석 중 에러 발생: {e}")
        # 기본값 혹은 에러 처리에 맞는 값을 반환합니다. 여기서는 1을 반환.
        return 1
    
# Create your views here.
class PlayChatView(APIView):
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
        responses={201: ChatSerializerPlay, 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        serializer = ChatUploadRequestSerializerPlay(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data["file"]
            author = request.user
            
            if not author.is_authenticated:
                return Response(status=status.HTTP_401_UNAUTHORIZED)

            # DB에 먼저 저장해서 경로를 얻는다
            chat = ChatPlay.objects.create(
                title="임시 제목",
                file=file,
                people_num=2,  # 초기값은 2로 설정
                user=request.user,
            )

            # 파일 경로에서 제목과 인원 수를 추출
            file_path = chat.file.path

            # 1. 파일 경로에서 제목 추출
            chat.title = extract_chat_title(file_path)

            # 2. Gemini API를 호출하여 인원 수 계산
            num_of_people = count_chat_participants_with_gemini(file_path)
            chat.people_num = num_of_people
            
            # 3. 변경된 제목과 인원 수를 함께 DB에 최종 저장
            chat.save()

            response = ChatSerializerPlay(chat)

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
        responses={200: ChatSerializerPlay(many=True), 401: "Unauthorized"},
    )
    def get(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        chats = ChatPlay.objects.filter(user=author)
        
        # Serialize the chat data
        chat_data = [
            ChatSerializerPlay(chat).data
            for chat in chats
        ]
        return Response(chat_data, status=status.HTTP_200_OK)



class PlayChatDetailView(APIView):
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
        responses={204: "No Content", 404: "Not Found", 403: "Forbidden", 401: "Unauthorized"},
    )
    def delete(self, request, chat_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            chat = ChatPlay.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            chat.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)



##################################################################



class PlayChatChemAnalyzeView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 케미 분석",
        operation_description="채팅 케미 데이터를 분석합니다.",
        request_body=ChatChemAnalysisRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={
            201: AnalyseResponseSerializerPlay,
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
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        # Validate request data
        serializer = ChatChemAnalysisRequestSerializerPlay(data=request.data)
        if serializer.is_valid() is False:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        relationship = serializer.validated_data["relationship"]
        situation = serializer.validated_data["situation"]
        analysis_start = serializer.validated_data["analysis_start"]
        analysis_end = serializer.validated_data["analysis_end"]

        try:
            chat = ChatPlay.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        analysis_result_text = (
            f"관계: {relationship}\n"
            f"상황: {situation}\n"
            f"분석 구간: {analysis_start} ~ {analysis_end}"
        )

        result = ResultPlayChem.objects.create(
            content=analysis_result_text,
            is_saved=1,
            relationship=relationship,
            situation=situation,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            chat=chat,
        )

        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )



class PlayChatSomeAnalyzeView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 썸 분석",
        operation_description="채팅 썸 데이터를 분석합니다.",
        request_body=ChatSomeAnalysisRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={
            201: AnalyseResponseSerializerPlay,
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
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        # Validate request data
        serializer = ChatSomeAnalysisRequestSerializerPlay(data=request.data)
        if serializer.is_valid() is False:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        relationship = serializer.validated_data["relationship"]
        age = serializer.validated_data["age"]
        analysis_start = serializer.validated_data["analysis_start"]
        analysis_end = serializer.validated_data["analysis_end"]

        try:
            chat = ChatPlay.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        analysis_result_text = (
            f"관계: {relationship}\n"
            f"나이: {age}\n"
            f"분석 구간: {analysis_start} ~ {analysis_end}"
        )

        result = ResultPlaySome.objects.create(
            content=analysis_result_text,
            is_saved=1,
            relationship=relationship,
            age=age,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            chat=chat,
        )

        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )



class PlayChatMBTIAnalyzeView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 MBTI 분석",
        operation_description="채팅 MBTI 데이터를 분석합니다.",
        request_body=ChatMBTIAnalysisRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={
            201: AnalyseResponseSerializerPlay,
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
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        # Validate request data
        serializer = ChatMBTIAnalysisRequestSerializerPlay(data=request.data)
        if serializer.is_valid() is False:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        analysis_start = serializer.validated_data["analysis_start"]
        analysis_end = serializer.validated_data["analysis_end"]

        try:
            chat = ChatPlay.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        analysis_result_text = (
            f"분석 구간: {analysis_start} ~ {analysis_end}"
        )

        result = ResultPlayMBTI.objects.create(
            content=analysis_result_text,
            is_saved=1,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            chat=chat,
        )

        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )



##################################################################



class PlayChemResultListView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 케미 분석 결과 리스트 조회",
        operation_description="로그인된 유저의 채팅 케미 분석 결과 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: ChemResultSerializerPlay(many=True), 401: "Unauthorized"},
    )
    def get(self, request):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        # Get all analysis results for the logged-in user
        results = ResultPlayChem.objects.filter(chat__user = author)
        serializer = ChemResultSerializerPlay(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class PlaySomeResultListView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 썸 분석 결과 리스트 조회",
        operation_description="로그인된 유저의 채팅 썸 분석 결과 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: SomeResultSerializerPlay(many=True), 401: "Unauthorized"},
    )
    def get(self, request):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        # Get all analysis results for the logged-in user
        results = ResultPlaySome.objects.filter(chat__user = author)
        serializer = SomeResultSerializerPlay(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class PlayMBTIResultListView(APIView):
    @swagger_auto_schema(
        operation_id="채팅 MBTI 분석 결과 리스트 조회",
        operation_description="로그인된 유저의 채팅 MBTI 분석 결과 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: MBTIResultSerializerPlay(many=True), 401: "Unauthorized"},
    )
    def get(self, request):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        # Get all analysis results for the logged-in user
        results = ResultPlayMBTI.objects.filter(chat__user = author)
        serializer = MBTIResultSerializerPlay(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



##################################################################



class PlayChemResultDetailView(APIView):
    @swagger_auto_schema(
        operation_id="케미 분석 결과 조회",
        operation_description="특정 케미 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: ChemResultSerializerPlay, 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request, result_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            serializer = ChemResultSerializerPlay(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ResultPlayChem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="케미 분석 결과 삭제",
        operation_description="특정 케미 분석 결과를 삭제합니다.",
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
            result = ResultPlayChem.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultPlayChem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


     
class PlaySomeResultDetailView(APIView):
    @swagger_auto_schema(
        operation_id="썸 분석 결과 조회",
        operation_description="특정 썸 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: SomeResultSerializerPlay, 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request, result_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            serializer = SomeResultSerializerPlay(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ResultPlaySome.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="썸 분석 결과 삭제",
        operation_description="특정 썸 분석 결과를 삭제합니다.",
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
            result = ResultPlaySome.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultPlaySome.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)



class PlayMBTIResultDetailView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 분석 결과 조회",
        operation_description="특정 MBTI 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: MBTIResultSerializerPlay, 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request, result_id):
        # authenticated user check
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            serializer = MBTIResultSerializerPlay(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ResultPlayMBTI.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="MBTI 분석 결과 삭제",
        operation_description="특정 MBTI 분석 결과를 삭제합니다.",
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
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            if result.chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultPlayMBTI.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)