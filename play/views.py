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
    ChemQuizStartRequestSerializerPlay,
    ChemQuizResultViewRequestSerializerPlay,
    ChemQuizPersonalViewRequestSerializerPlay,
    ChemQuizModifyRequestSerializerPlay,
    ChemQuizSubmitRequestSerializerPlay,
    ChatTitleModifyRequestSerializerPlay,
    SomeQuizStartRequestSerializerPlay,
    SomeQuizPersonalViewRequestSerializerPlay,
    SomeQuizResultViewRequestSerializerPlay,
    SomeQuizModifyRequestSerializerPlay,
    SomeQuizSubmitRequestSerializerPlay,
    MBTIQuizStartRequestSerializerPlay,
    MBTIQuizPersonalViewRequestSerializerPlay,
    MBTIQuizResultViewRequestSerializerPlay,
    MBTIQuizModifyRequestSerializerPlay,
    MBTIQuizSubmitRequestSerializerPlay,
)
from .serializers import (
    AnalyseResponseSerializerPlay,
    ChatSerializerPlay,
    ChemResultSerializerPlay,
    SomeResultSerializerPlay,
    MBTIResultSerializerPlay,
    SomeAllSerializerPlay,
    MBTIAllSerializerPlay,
    ChemAllSerializerPlay,
    QuizCreatedSerializerPlay,
    ChemQuizQuestionSerializerPlay,
    ChemQuizInfoSerializerPlay,
    ChemQuizPersonalSerializerPlay,
    ChemQuizQuestionDetailSerializerPlay,
    ChemQuizPersonalDetailSerializerPlay,
    SomeQuizQuestionDetailSerializerPlay,
    SomeQuizQuestionSerializerPlay,
    SomeQuizInfoSerializerPlay,
    SomeQuizPersonalSerializerPlay,
    SomeQuizPersonalDetailSerializerPlay,
    MBTIQuizQuestionSerializerPlay,
    MBTIQuizQuestionDetailSerializerPlay,
    MBTIQuizInfoSerializerPlay,
    MBTIQuizPersonalSerializerPlay,
    MBTIQuizPersonalDetailSerializerPlay,
)

from .models import(
    ChatPlay, 
    ResultPlayChem,
    ResultPlaySome,
    ResultPlayMBTI,
    ResultPlaySomeSpec,
    ResultPlayMBTISpec,
    ResultPlayMBTISpecPersonal,
    ResultPlayChemSpec,
    ResultPlayChemSpecTable,
    ChemQuiz,
    ChemQuizQuestion,
    ChemQuizPersonal,
    ChemQuizPersonalDetail,
    SomeQuiz,
    SomeQuizQuestion,
    SomeQuizPersonal,
    SomeQuizPersonalDetail,
    MBTIQuiz,
    MBTIQuizQuestion,
    MBTIQuizPersonal,
    MBTIQuizPersonalDetail,
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
            chat = ChatPlay.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            chat.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="특정 채팅 제목 수정",
        operation_description="특정 채팅의 제목을 수정합니다.",
        request_body=ChatTitleModifyRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def put(self, request, chat_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            chat = ChatPlay.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        request_serializer = ChatTitleModifyRequestSerializerPlay(data=request.data)
        if request_serializer.is_valid() is False:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        chat.title = request_serializer.validated_data["title"]
        chat.save()

        return Response(status=status.HTTP_200_OK)

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


        result = ResultPlayChem.objects.create(
            type=1,
            is_saved=1,
            title=chat.title,
            people_num=chat.people_num,
            relationship=relationship,
            situation=situation,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            chat=chat,
        )

        if result.people_num >= 5:
            size = 5
        else:
            size = result.people_num

        spec = ResultPlayChemSpec.objects.create(
            result=result,
            score_main=0,
            summary_main="",
            tablesize=size,
            top1_A="",
            top1_B="",
            top1_score=0,
            top1_comment="",
            top2_A="",
            top2_B="",
            top2_score=0,
            top2_comment="",
            top3_A="",
            top3_B="",
            top3_score=0,
            top3_comment="",
            tone_pos=0,
            tone_humer=0,
            tone_else=0,
            tone_ex="",
            resp_time=0,
            resp_ratio=0,
            ignore=0,
            resp_analysis="",
            topic1="",
            topic1_ratio=0,
            topic2="",
            topic2_ratio=0,
            topic3="",
            topic3_ratio=0,
            topic4="",
            topic4_ratio=0,
            topicelse_ratio=0,
            chatto_analysis="",
            chatto_levelup="",
            chatto_levelup_tips="",
            name_0="",
            name_1="",
            name_2="",
            name_3="",
            name_4="",
        )

        for i in range(spec.tablesize):
            for j in range(spec.tablesize):
                if i == j:
                    val = 0
                else:
                    val = 1
                ResultPlayChemSpecTable.objects.create(
                    spec=spec,
                    row=i,
                    column=j,
                    interaction=val,
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


        result = ResultPlaySome.objects.create(
            type=2,
            title=chat.title,
            people_num=chat.people_num,
            is_saved=1,
            relationship=relationship,
            age=age,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            chat=chat,
        )

        ResultPlaySomeSpec.objects.create(
            result=result,
            score_main=0,
            comment_main="",
            score_A=0,
            score_B=0,
            trait_A="",
            trait_B="",
            summary="",
            tone=0,
            tone_desc="",
            tone_ex="",
            emo=0,
            emo_desc="",
            emo_ex="",
            addr=0,
            addr_desc="",
            addr_ex="",
            reply_A = 0,
            reply_B = 0,
            reply_A_desc = "",
            reply_B_desc = "",
            rec_A = 0,
            rec_B = 0,
            rec_A_desc = "",
            rec_B_desc = "",
            rec_A_ex = "",
            rec_B_ex = "",
            atti_A = 0,
            atti_B = 0,
            atti_A_desc = "",
            atti_B_desc = "",
            atti_A_ex = "",
            atti_B_ex = "",
            pattern_analysis = "",
            chatto_coundel = "",
            chatto_coundel_tips = "",
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


        result = ResultPlayMBTI.objects.create(
            type=3,
            title=chat.title,
            people_num=chat.people_num,
            is_saved=1,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            chat=chat,
        )

        spec = ResultPlayMBTISpec.objects.create(
            result=result,
            total_I=0,
            total_E=0,
            total_S=0,
            total_N=0,
            total_F=0,
            total_T=0,
            total_J=0,
            total_P=0,
        )

        for _ in range (chat.people_num):
            ResultPlayMBTISpecPersonal.objects.create(
                spec=spec,
                name="이름",
                MBTI="",
                summary="",
                desc="",
                position="",
                personality="",
                style="",
                moment_ex="",
                moment_desc="",
                momentIE_ex="",
                momentIE_desc="",
                momentSN_ex="",
                momentSN_desc="",
                momentFT_ex="",
                momentFT_desc="",
                momentJP_ex="",
                momentJP_desc="",
            )

        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )



##################################################################



class PlayChemResultDetailView(APIView):
    @swagger_auto_schema(
        operation_id="특정 케미 분석 결과 조회",
        operation_description="특정 케미 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: ChemAllSerializerPlay, 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
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
            
            spec = ResultPlayChemSpec.objects.get(result=result)
            spec_tables = ResultPlayChemSpecTable.objects.filter(spec=spec)
            payload = {
                "result": result,
                "spec": spec,
                "spec_table": list(spec_tables),
            }
            serializer = ChemAllSerializerPlay(payload)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="특정 케미 분석 결과 삭제",
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
        operation_id="특정 썸 분석 결과 조회",
        operation_description="특정 썸 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: SomeAllSerializerPlay, 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
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
            
            spec = ResultPlaySomeSpec.objects.get(result=result)

            payload = {
                "result": result,
                "spec": spec,
            }

            serializer = SomeAllSerializerPlay(payload)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="특정 썸 분석 결과 삭제",
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
        operation_id="특정 MBTI 분석 결과 조회",
        operation_description="특정 MBTI 분석 결과를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: MBTIAllSerializerPlay, 404: "Not Found", 401: "Unauthorized", 403: "Forbidden"},
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
            
            spec = ResultPlayMBTISpec.objects.get(result=result)
            spec_personals = ResultPlayMBTISpecPersonal.objects.filter(spec=spec)
            
            payload = {
                "result": result,
                "spec": spec,
                "spec_personal": list(spec_personals),
            }

            serializer = MBTIAllSerializerPlay(payload)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_id="특정 MBTI 분석 결과 삭제",
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



###################################################################



class PlayResultAllView(APIView):
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
        responses={
            200: "OK",
            401: "Unauthorized"
        },
    )
    def get(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        chem_results = ResultPlayChem.objects.filter(chat__user=author)
        some_results = ResultPlaySome.objects.filter(chat__user=author)
        mbti_results = ResultPlayMBTI.objects.filter(chat__user=author)

        # 모델별 직렬화 
        chem_serialized = ChemResultSerializerPlay(chem_results, many=True).data
        some_serialized = SomeResultSerializerPlay(some_results, many=True).data
        mbti_serialized = MBTIResultSerializerPlay(mbti_results, many=True).data

        # 하나의 리스트로 합치기
        combined = chem_serialized + some_serialized + mbti_serialized

        # created_at 기준 내림차순 정렬
        results = sorted(combined, key=lambda x: x["created_at"], reverse=True)

        return Response(results, status=status.HTTP_200_OK)
    


###################################################################


# 케미 퀴즈 생성, 케미 퀴즈 조회, 케미 퀴즈 삭제
class PlayChemQuizView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 생성",
        operation_description="특정 케미 분석 결과에 대한 퀴즈를 생성합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: QuizCreatedSerializerPlay(many=True),
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def post(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
        except ResultPlayChem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if result.chat.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        # spec과 spec_tables을 가져온 이유: 이거 보고 퀴즈 생성! (물론 chat의 내용도 보고)
        spec = ResultPlayChemSpec.objects.get(result=result)
        spec_tables = ResultPlayChemSpecTable.objects.filter(spec=spec)

        if ChemQuiz.objects.filter(result=result).exists():
            return Response({"detail": "이미 해당 분석 결과에 대한 퀴즈가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        quiz = ChemQuiz.objects.create(
            result=result,
            question_num=3,
            solved_num=0,
            avg_score=0,
        )

        for i in range(quiz.question_num):
            ChemQuizQuestion.objects.create(
                quiz=quiz,
                question_index=i,
                question=f"{i}번째 질문 내용",
                choice1="선택지 1",
                choice2="선택지 2",
                choice3="선택지 3",
                choice4="선택지 4",
                answer=1,
                correct_num=0,
                count1=0,
                count2=0,
                count3=0,
                count4=0,
            )
        
        return Response(
            {
                "quiz_id": quiz.quiz_id,
            },
            status=status.HTTP_201_CREATED,
        )


    @swagger_auto_schema(
        operation_id="케미 퀴즈 조회",
        operation_description="특정 케미 분석 결과에 대한 퀴즈를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: ChemQuizInfoSerializerPlay,
            401: "Unauthorized",
            404: "Not Found",
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = ChemQuizInfoSerializerPlay(quiz)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id="케미 퀴즈 삭제",
        operation_description="특정 케미 분석 결과에 대한 퀴즈를 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            204: "No Content",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def delete(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if result.chat.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)

        quiz.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# 케미 퀴즈 문제 리스트 상세 조회
class PlayChemQuizQuestionListDetailView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 문제 리스트 상세 조회",
        operation_description="특정 케미 분석 결과에 대한 퀴즈의 문제 리스트를 상세 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: ChemQuizQuestionDetailSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            questions = ChemQuizQuestion.objects.filter(quiz=quiz)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = ChemQuizQuestionDetailSerializerPlay(questions, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# 케미 퀴즈 문제 리스트 조회
class PlayChemQuizQuestionListView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 문제 리스트 조회",
        operation_description="특정 케미 분석 결과에 대한 퀴즈의 문제 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: ChemQuizQuestionSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            questions = ChemQuizQuestion.objects.filter(quiz=quiz).order_by('question_index')
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = ChemQuizQuestionSerializerPlay(questions, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    

# 케미 퀴즈 풀이 시작
class PlayChemQuizStartView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 풀이 시작",
        operation_description="케미 퀴즈 풀이를 시작합니다.",
        request_body=ChemQuizStartRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def post(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer = ChemQuizStartRequestSerializerPlay(data=request.data)
        
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        name = serializer.validated_data["name"]

        if ChemQuizPersonal.objects.filter(quiz__result__result_id=result_id, name=name).exists():
            return Response({"detail": "이미 해당 이름의 퀴즈 풀이가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        ChemQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        return Response(status=status.HTTP_201_CREATED)


# 케미 퀴즈 결과 (문제별 리스트) 한 사람 조회, 케미 퀴즈 결과 한 사람 삭제
class PlayChemQuizPersonalView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 결과 (문제별 리스트) 한 사람 조회",
        operation_description="케미 퀴즈 결과를 한 사람 기준으로 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: ChemQuizPersonalSerializerPlay,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(quiz=quiz, name=name)
            quiz_personal_details = ChemQuizPersonalDetail.objects.filter(QP=quiz_personal)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = ChemQuizPersonalDetailSerializerPlay(quiz_personal_details, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="케미 퀴즈 결과 한 사람 삭제",
        operation_description="케미 퀴즈 결과를 한 사람 기준으로 삭제합니다.",
        request_body=ChemQuizPersonalViewRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def delete(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(quiz=quiz, name=name)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        quiz_personal.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# 케미 퀴즈 풀이 제출 (여러 문제 답변을 한 번에 제출)
class PlayChemQuizSubmitView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 제출",
        operation_description="케미 퀴즈 풀이를 제출합니다. (여러 문제 답변을 한 번에 제출)",
        request_body=ChemQuizSubmitRequestSerializerPlay(many=True),
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def post(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        request_serializer = ChemQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(quiz=quiz, name=name)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        answers = request_serializer.validated_data

        if len(answers) != quiz.question_num:
            return Response({"detail": "제출한 답변의 수가 문제 수와 일치하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        i = 0
        for answer in answers:
            response = int(answer['answer'])

            try:
                question = ChemQuizQuestion.objects.get(quiz=quiz, question_index=i)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)

            if response == 1:
                question.count1 += 1
            elif response == 2:
                question.count2 += 1
            elif response == 3:
                question.count3 += 1
            elif response == 4:
                question.count4 += 1
            else: 
                return Response(status=status.HTTP_400_BAD_REQUEST)

            question.save()

            # QP(quiz_personal) 조작
            result_correct = (question.answer == response)
            if result_correct:
                quiz_personal.score += 1
            quiz_personal.save()

            # QPD(quiz_personal_detail) 생성
            ChemQuizPersonalDetail.objects.create(
                QP=quiz_personal,
                question=question,
                response=response,
                result=result_correct,
            )

            i += 1

        return Response(status=status.HTTP_200_OK)

        
# 케미 퀴즈 결과 여러 사람 리스트 조회
class PlayChemQuizResultListView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 결과 여러사람 리스트 조회",
        operation_description="케미 퀴즈 풀이 결과 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: ChemQuizPersonalSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personals = ChemQuizPersonal.objects.filter(quiz=quiz)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ChemQuizPersonalSerializerPlay(quiz_personals, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
            

# 케미 퀴즈 문제 수정
class PlayChemQuizModifyView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 문제 수정",
        operation_description="케미 퀴즈의 특정 문제를 수정합니다.",
        request_body=ChemQuizModifyRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def put(self, request, result_id, question_index):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            question = ChemQuizQuestion.objects.get(quiz=quiz, question_index=question_index)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        request_serializer = ChemQuizModifyRequestSerializerPlay(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 해당 문제의 선지와 정답을 수정
        question.question = request.data.get("question", question.question)
        question.choice1 = request.data.get("choice1", question.choice1)
        question.choice2 = request.data.get("choice2", question.choice2)
        question.choice3 = request.data.get("choice3", question.choice3)
        question.choice4 = request.data.get("choice4", question.choice4)
        question.answer = request.data.get("answer", question.answer)
        question.save()

        # 해당 문제가 속하는 퀴즈의 statistics를 초기화
        quiz.solved_num = 0
        quiz.avg_score = 0
        quiz.save()

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = ChemQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        ChemQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_200_OK)
    


###################################################################


# 썸 퀴즈 생성, 썸 퀴즈 조회, 썸 퀴즈 삭제
class PlaySomeQuizView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 생성",
        operation_description="특정 썸 분석 결과에 대한 퀴즈를 생성합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: QuizCreatedSerializerPlay(many=True),
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def post(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if result.chat.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        # spec과 가져온 이유: 이거 보고 퀴즈 생성! (물론 chat의 내용도 보고)
        spec = ResultPlaySomeSpec.objects.get(result=result)

        if SomeQuiz.objects.filter(result=result).exists():
            return Response({"detail": "이미 해당 분석 결과에 대한 퀴즈가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        quiz = SomeQuiz.objects.create(
            result=result,
            question_num=3,
            solved_num=0,
            avg_score=0,
        )

        for i in range(quiz.question_num):
            SomeQuizQuestion.objects.create(
                quiz=quiz,
                question_index=i,
                question=f"{i}번째 질문 내용",
                choice1="선택지 1",
                choice2="선택지 2",
                choice3="선택지 3",
                choice4="선택지 4",
                answer=1,
                correct_num=0,
                count1=0,
                count2=0,
                count3=0,
                count4=0,
            )
        
        return Response(
            {
                "quiz_id": quiz.quiz_id,
            },
            status=status.HTTP_201_CREATED,
        )


    @swagger_auto_schema(
        operation_id="썸 퀴즈 조회",
        operation_description="특정 썸 분석 결과에 대한 퀴즈를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: SomeQuizInfoSerializerPlay,
            401: "Unauthorized",
            404: "Not Found",
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = SomeQuizInfoSerializerPlay(quiz)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id="썸 퀴즈 삭제",
        operation_description="특정 썸 분석 결과에 대한 퀴즈를 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            204: "No Content",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def delete(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if result.chat.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)

        quiz.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# 썸 퀴즈 문제 리스트 상세 조회
class PlaySomeQuizQuestionListDetailView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 문제 리스트 상세 조회",
        operation_description="특정 썸 분석 결과에 대한 퀴즈의 문제 리스트를 상세 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: SomeQuizQuestionDetailSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            questions = SomeQuizQuestion.objects.filter(quiz=quiz)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = SomeQuizQuestionDetailSerializerPlay(questions, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# 썸 퀴즈 문제 리스트 조회
class PlaySomeQuizQuestionListView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 문제 리스트 조회",
        operation_description="특정 썸 분석 결과에 대한 퀴즈의 문제 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: SomeQuizQuestionSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            questions = SomeQuizQuestion.objects.filter(quiz=quiz).order_by('question_index')
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = SomeQuizQuestionSerializerPlay(questions, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    

# 썸 퀴즈 풀이 시작
class PlaySomeQuizStartView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 풀이 시작",
        operation_description="썸 퀴즈 풀이를 시작합니다.",
        request_body=SomeQuizStartRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def post(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer = SomeQuizStartRequestSerializerPlay(data=request.data)
        
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        name = serializer.validated_data["name"]

        if SomeQuizPersonal.objects.filter(quiz__result__result_id=result_id, name=name).exists():
            return Response({"detail": "이미 해당 이름의 퀴즈 풀이가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        SomeQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        return Response(status=status.HTTP_201_CREATED)


# 썸 퀴즈 결과 (문제별 리스트) 한 사람 조회, 썸 퀴즈 결과 한 사람 삭제
class PlaySomeQuizPersonalView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 결과 (문제별 리스트) 한 사람 조회",
        operation_description="썸 퀴즈 결과를 한 사람 기준으로 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: SomeQuizPersonalSerializerPlay,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(quiz=quiz, name=name)
            quiz_personal_details = SomeQuizPersonalDetail.objects.filter(QP=quiz_personal)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = SomeQuizPersonalDetailSerializerPlay(quiz_personal_details, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="썸 퀴즈 결과 한 사람 삭제",
        operation_description="썸 퀴즈 결과를 한 사람 기준으로 삭제합니다.",
        request_body=SomeQuizPersonalViewRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def delete(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(quiz=quiz, name=name)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        quiz_personal.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# 썸 퀴즈 풀이 제출 (여러 문제 답변을 한 번에 제출)
class PlaySomeQuizSubmitView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 제출",
        operation_description="썸 퀴즈 풀이를 제출합니다. (여러 문제 답변을 한 번에 제출)",
        request_body=SomeQuizSubmitRequestSerializerPlay(many=True),
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def post(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        request_serializer = SomeQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(quiz=quiz, name=name)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        answers = request_serializer.validated_data

        if len(answers) != quiz.question_num:
            return Response({"detail": "제출한 답변의 수가 문제 수와 일치하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        i = 0
        for answer in answers:
            response = int(answer['answer'])

            try:
                question = SomeQuizQuestion.objects.get(quiz=quiz, question_index=i)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)

            if response == 1:
                question.count1 += 1
            elif response == 2:
                question.count2 += 1
            elif response == 3:
                question.count3 += 1
            elif response == 4:
                question.count4 += 1
            else: 
                return Response(status=status.HTTP_400_BAD_REQUEST)

            question.save()

            # QP(quiz_personal) 조작
            result_correct = (question.answer == response)
            if result_correct:
                quiz_personal.score += 1
            quiz_personal.save()

            # QPD(quiz_personal_detail) 생성
            SomeQuizPersonalDetail.objects.create(
                QP=quiz_personal,
                question=question,
                response=response,
                result=result_correct,
            )

            i += 1

        return Response(status=status.HTTP_200_OK)

        
# 썸 퀴즈 결과 여러 사람 리스트 조회
class PlaySomeQuizResultListView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 결과 여러사람 리스트 조회",
        operation_description="썸 퀴즈 풀이 결과 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: SomeQuizPersonalSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personals = SomeQuizPersonal.objects.filter(quiz=quiz)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = SomeQuizPersonalSerializerPlay(quiz_personals, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
            

# 썸 퀴즈 문제 수정
class PlaySomeQuizModifyView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 문제 수정",
        operation_description="썸 퀴즈의 특정 문제를 수정합니다.",
        request_body=SomeQuizModifyRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def put(self, request, result_id, question_index):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            question = SomeQuizQuestion.objects.get(quiz=quiz, question_index=question_index)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        request_serializer = SomeQuizModifyRequestSerializerPlay(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 해당 문제의 선지와 정답을 수정
        question.question = request.data.get("question", question.question)
        question.choice1 = request.data.get("choice1", question.choice1)
        question.choice2 = request.data.get("choice2", question.choice2)
        question.choice3 = request.data.get("choice3", question.choice3)
        question.choice4 = request.data.get("choice4", question.choice4)
        question.answer = request.data.get("answer", question.answer)
        question.save()

        # 해당 문제가 속하는 퀴즈의 statistics를 초기화
        quiz.solved_num = 0
        quiz.avg_score = 0
        quiz.save()

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = SomeQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        SomeQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_200_OK)
    


###################################################################


# MBTI 퀴즈 생성, MBTI 퀴즈 조회, MBTI 퀴즈 삭제
class PlayMBTIQuizView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 생성",
        operation_description="특정 MBTi 분석 결과에 대한 퀴즈를 생성합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: QuizCreatedSerializerPlay(many=True),
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def post(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if result.chat.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        # spec과 spec_personals 가져온 이유: 이거 보고 퀴즈 생성! (물론 chat의 내용도 보고)
        spec = ResultPlayMBTISpec.objects.get(result=result)
        spec_personals = ResultPlayMBTISpecPersonal.objects.filter(spec=spec)

        if MBTIQuiz.objects.filter(result=result).exists():
            return Response({"detail": "이미 해당 분석 결과에 대한 퀴즈가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        quiz = MBTIQuiz.objects.create(
            result=result,
            question_num=3,
            solved_num=0,
            avg_score=0,
        )

        for i in range(quiz.question_num):
            MBTIQuizQuestion.objects.create(
                quiz=quiz,
                question_index=i,
                question=f"{i}번째 질문 내용",
                choice1="MBTI 1",
                choice2="MBTI 2",
                choice3="MBTI 3",
                choice4="MBTI 4",
                answer=1,
                correct_num=0,
                count1=0,
                count2=0,
                count3=0,
                count4=0,
            )
        
        return Response(
            {
                "quiz_id": quiz.quiz_id,
            },
            status=status.HTTP_201_CREATED,
        )


    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 조회",
        operation_description="특정 MBTI 분석 결과에 대한 퀴즈를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: MBTIQuizInfoSerializerPlay,
            401: "Unauthorized",
            404: "Not Found",
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = MBTIQuizInfoSerializerPlay(quiz)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 삭제",
        operation_description="특정 MBTI 분석 결과에 대한 퀴즈를 삭제합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            204: "No Content",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def delete(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if result.chat.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)

        quiz.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# MBTI 퀴즈 문제 리스트 상세 조회
class PlayMBTIQuizQuestionListDetailView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 문제 리스트 상세 조회",
        operation_description="특정 MBTI 분석 결과에 대한 퀴즈의 문제 리스트를 상세 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: MBTIQuizQuestionDetailSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            questions = MBTIQuizQuestion.objects.filter(quiz=quiz)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = MBTIQuizQuestionDetailSerializerPlay(questions, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# MBTI 퀴즈 문제 리스트 조회
class PlayMBTIQuizQuestionListView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 문제 리스트 조회",
        operation_description="특정 MBTI 분석 결과에 대한 퀴즈의 문제 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: MBTIQuizQuestionSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            questions = MBTIQuizQuestion.objects.filter(quiz=quiz).order_by('question_index')
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = MBTIQuizQuestionSerializerPlay(questions, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    

# MBTI 퀴즈 풀이 시작
class PlayMBTIQuizStartView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 풀이 시작",
        operation_description="MBTI 퀴즈 풀이를 시작합니다.",
        request_body=MBTIQuizStartRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def post(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer = MBTIQuizStartRequestSerializerPlay(data=request.data)
        
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        name = serializer.validated_data["name"]

        if MBTIQuizPersonal.objects.filter(quiz__result__result_id=result_id, name=name).exists():
            return Response({"detail": "이미 해당 이름의 퀴즈 풀이가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        MBTIQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        return Response(status=status.HTTP_201_CREATED)


# MBTI 퀴즈 결과 (문제별 리스트) 한 사람 조회, MBTI 퀴즈 결과 한 사람 삭제
class PlayMBTIQuizPersonalView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 결과 (문제별 리스트) 한 사람 조회",
        operation_description="MBTI 퀴즈 결과를 한 사람 기준으로 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: MBTIQuizPersonalSerializerPlay,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(quiz=quiz, name=name)
            quiz_personal_details = MBTIQuizPersonalDetail.objects.filter(QP=quiz_personal)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = MBTIQuizPersonalDetailSerializerPlay(quiz_personal_details, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 결과 한 사람 삭제",
        operation_description="MBTI 퀴즈 결과를 한 사람 기준으로 삭제합니다.",
        request_body=MBTIQuizPersonalViewRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def delete(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(quiz=quiz, name=name)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        quiz_personal.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# MBTI 퀴즈 풀이 제출 (여러 문제 답변을 한 번에 제출)
class PlayMBTIQuizSubmitView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 제출",
        operation_description="MBTI 퀴즈 풀이를 제출합니다. (여러 문제 답변을 한 번에 제출)",
        request_body=MBTIQuizSubmitRequestSerializerPlay(many=True),
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def post(self, request, result_id, name):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        request_serializer = MBTIQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(quiz=quiz, name=name)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        answers = request_serializer.validated_data

        if len(answers) != quiz.question_num:
            return Response({"detail": "제출한 답변의 수가 문제 수와 일치하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        i = 0
        for answer in answers:
            response = int(answer['answer'])

            try:
                question = MBTIQuizQuestion.objects.get(quiz=quiz, question_index=i)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)

            if response == 1:
                question.count1 += 1
            elif response == 2:
                question.count2 += 1
            elif response == 3:
                question.count3 += 1
            elif response == 4:
                question.count4 += 1
            else: 
                return Response(status=status.HTTP_400_BAD_REQUEST)

            question.save()

            # QP(quiz_personal) 조작
            result_correct = (question.answer == response)
            if result_correct:
                quiz_personal.score += 1
            quiz_personal.save()

            # QPD(quiz_personal_detail) 생성
            MBTIQuizPersonalDetail.objects.create(
                QP=quiz_personal,
                question=question,
                response=response,
                result=result_correct,
            )

            i += 1

        return Response(status=status.HTTP_200_OK)

        
# MBTI 퀴즈 결과 여러 사람 리스트 조회
class PlayMBTIQuizResultListView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 결과 여러사람 리스트 조회",
        operation_description="MBTI 퀴즈 풀이 결과 리스트를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: MBTIQuizPersonalSerializerPlay(many=True),
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personals = MBTIQuizPersonal.objects.filter(quiz=quiz)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = MBTIQuizPersonalSerializerPlay(quiz_personals, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
            

# MBTI 퀴즈 문제 수정
class PlayMBTIQuizModifyView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 문제 수정",
        operation_description="MBTI 퀴즈의 특정 문제를 수정합니다.",
        request_body=MBTIQuizModifyRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def put(self, request, result_id, question_index):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            question = MBTIQuizQuestion.objects.get(quiz=quiz, question_index=question_index)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        request_serializer = MBTIQuizModifyRequestSerializerPlay(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 해당 문제의 선지와 정답을 수정
        question.question = request.data.get("question", question.question)
        question.choice1 = request.data.get("choice1", question.choice1)
        question.choice2 = request.data.get("choice2", question.choice2)
        question.choice3 = request.data.get("choice3", question.choice3)
        question.choice4 = request.data.get("choice4", question.choice4)
        question.answer = request.data.get("answer", question.answer)
        question.save()

        # 해당 문제가 속하는 퀴즈의 statistics를 초기화
        quiz.solved_num = 0
        quiz.avg_score = 0
        quiz.save()

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = MBTIQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        MBTIQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_200_OK)
    