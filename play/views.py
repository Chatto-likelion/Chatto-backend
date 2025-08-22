from django.shortcuts import render

# Create your views here.

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import uuid

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
    UuidRequestSerializerPlay,
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
    ChemUuidSerializerPlay,
    MBTIUuidSerializerPlay,
    SomeUuidSerializerPlay,
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
    UuidChem,
    UuidSome,
    UuidMBTI,
)   

from rest_framework.parsers import MultiPartParser, FormParser

from django.utils import timezone

import re
from google import genai
from django.conf import settings

from .utils import (
    extract_chat_title,
    count_chat_participants_with_gemini,
    some_analysis_with_gemini,
    mbti_analysis_with_gemini,
    chem_analysis_with_gemini,
    parse_response,
)

    
# 채팅 파일 업로드, 채팅 목록 조회
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


# 특정 채팅 삭제, 특정 채팅 제목 수정
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
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if chat.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        chem_results = ResultPlayChem.objects.filter(chat=chat)
        some_results = ResultPlaySome.objects.filter(chat=chat)
        mbti_results = ResultPlayMBTI.objects.filter(chat=chat)

        for result in chem_results:
            result.chat = None  
            result.save()
        for result in some_results:
            result.chat = None  
            result.save()
        for result in mbti_results:
            result.chat = None  
            result.save()

        chat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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


# 채팅 케미 분석
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

        print(analysis_start, analysis_end)
        try:
            chat = ChatPlay.objects.get(chat_id=chat_id)
            if chat.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
        except ChatPlay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        analysis_option = {
            "start": analysis_start,
            "end": analysis_end,
            "relationship": relationship,
            "situation": situation,
        }

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        chem_results = chem_analysis_with_gemini(chat, client, analysis_option)

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
            num_chat=chem_results.get("num_chat", 0),
            user=author, 
        )

        if "error_message" in chem_results:
            result.delete()
            return Response(
                {"detail": chem_results["error_message"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
        size = 5 if result.people_num >= 5 else result.people_num

        spec = ResultPlayChemSpec.objects.create(
            result=result,
            score_main=chem_results.get("score_main", 0),
            summary_main=chem_results.get("summary_main", ""),
            tablesize=size,
            top1_A=chem_results.get("top1_A", ""),
            top1_B=chem_results.get("top1_B", ""),
            top1_score=chem_results.get("top1_score", 0),
            top1_comment=chem_results.get("top1_comment", ""),
            top2_A=chem_results.get("top2_A", ""),
            top2_B=chem_results.get("top2_B", ""),
            top2_score=chem_results.get("top2_score", 0),
            top2_comment=chem_results.get("top2_comment", ""),
            top3_A=chem_results.get("top3_A", ""),
            top3_B=chem_results.get("top3_B", ""),
            top3_score=chem_results.get("top3_score", 0),
            top3_comment=chem_results.get("top3_comment", ""),
            tone_pos=chem_results.get("tone_pos", 0),
            tone_humer=chem_results.get("tone_humer", 0),
            tone_crit=chem_results.get("tone_crit", 0),
            tone_else=chem_results.get("tone_else", 0),
            tone_ex1=chem_results.get("tone_ex1", ""),
            tone_ex2=chem_results.get("tone_ex2", ""),
            tone_ex3=chem_results.get("tone_ex3", ""),
            tone_analysis=chem_results.get("tone_analysis", ""),
            resp_time=chem_results.get("resp_time", 0),
            resp_ratio=chem_results.get("resp_ratio", 0),
            ignore=chem_results.get("ignore", 0),
            resp_analysis=chem_results.get("resp_analysis", ""),
            topic1=chem_results.get("topic1", ""),
            topic1_ratio=chem_results.get("topic1_ratio", 0),
            topic2=chem_results.get("topic2", ""),
            topic2_ratio=chem_results.get("topic2_ratio", 0),
            topic3=chem_results.get("topic3", ""),
            topic3_ratio=chem_results.get("topic3_ratio", 0),
            topic4=chem_results.get("topic4", ""),
            topic4_ratio=chem_results.get("topic4_ratio", 0),
            topicelse_ratio=chem_results.get("topicelse_ratio", 0),
            chatto_analysis=chem_results.get("chatto_analysis", ""),
            chatto_levelup=chem_results.get("chatto_levelup", ""),
            chatto_levelup_tips=chem_results.get("chatto_levelup_tips", ""),
            name_0=chem_results.get("name_0", ""),
            name_1=chem_results.get("name_1", ""),
            name_2=chem_results.get("name_2", ""),
            name_3=chem_results.get("name_3", ""),
            name_4=chem_results.get("name_4", ""),
        )

        names = [name for name in [
            chem_results.get("name_0"), chem_results.get("name_1"),
            chem_results.get("name_2"), chem_results.get("name_3"),
            chem_results.get("name_4")
        ] if name] # 이름이 있는 경우에만 리스트에 추가
        
        interaction_matrix = chem_results.get("interaction_matrix", {})

        for i, name_row in enumerate(names):
            for j, name_col in enumerate(names):
                if i == j:
                    val = 0 # 자기 자신과의 상호작용은 0
                else:
                    # 'A-B' 형식의 키로 점수 조회
                    key = f"{name_row}-{name_col}"
                    val = interaction_matrix.get(key, 0) # 값이 없으면 0점

                ResultPlayChemSpecTable.objects.create(
                    spec=spec,
                    row=i,
                    column=j,
                    interaction=val,
                )

        return Response(
            {"result_id": result.result_id},
            status=status.HTTP_201_CREATED,
        )

      
# 채팅 썸 분석
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


        # Gemini API 클라이언트를 사용하여 대화 내용을 분석
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # 분석에 필요한 모든 옵션을 딕셔너리로 구성
        analysis_option = {
            "start": analysis_start,
            "end": analysis_end,
            "relationship": relationship,
            "age": age,
        }

        some_results = some_analysis_with_gemini(chat, client, analysis_option)

        result = ResultPlaySome.objects.create(
            type=2,
            title=chat.title,
            people_num=chat.people_num,
            is_saved=1,
            relationship=relationship,
            age=age,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            num_chat=some_results.get("num_chat", 0),
            chat=chat,
            user=author,
        )

        ResultPlaySomeSpec.objects.create(
            result=result,
            name_A=some_results.get("name_A", ""),
            name_B=some_results.get("name_B", ""),
            score_main=some_results.get("score_main", 0),    # score_A + score_B / 2 로 해도 좋을 듯
            comment_main=some_results.get("comment_main", ""),
            score_A=some_results.get("score_A", 0),
            score_B=some_results.get("score_B", 0),
            trait_A=some_results.get("trait_A", ""),
            trait_B=some_results.get("trait_B", ""),
            summary=some_results.get("summary", ""),
            tone=some_results.get("tone_score", 0),
            tone_desc=some_results.get("tone_desc", ""),
            tone_ex=some_results.get("tone_ex", ""),
            emo=some_results.get("emo_score", 0),
            emo_desc=some_results.get("emo_desc", ""),
            emo_ex=some_results.get("emo_ex", ""),
            addr=some_results.get("addr_score", 0),
            addr_desc=some_results.get("addr_desc", ""),
            addr_ex=some_results.get("addr_ex", ""),
            reply_A=some_results.get("reply_A", 0),
            reply_B=some_results.get("reply_B", 0),
            reply_A_desc=some_results.get("reply_A_desc", ""),
            reply_B_desc=some_results.get("reply_B_desc", ""),
            rec_A=some_results.get("rec_A", 0),
            rec_B=some_results.get("rec_B", 0),
            rec_A_desc=some_results.get("rec_A_desc", ""),
            rec_B_desc=some_results.get("rec_B_desc", ""),
            rec_A_ex=some_results.get("rec_A_ex", ""),
            rec_B_ex=some_results.get("rec_B_ex", ""),
            atti_A=some_results.get("atti_A", 0),
            atti_B=some_results.get("atti_B", 0),
            atti_A_desc=some_results.get("atti_A_desc", ""),
            atti_B_desc = some_results.get("atti_B_desc", ""),
            atti_A_ex = some_results.get("atti_A_ex", ""),
            atti_B_ex = some_results.get("atti_B_ex", ""),
            len_A=some_results.get("len_A", 0),
            len_B=some_results.get("len_B", 0),
            len_A_desc=some_results.get("len_A_desc", ""),
            len_B_desc=some_results.get("len_B_desc", ""),
            len_A_ex=some_results.get("len_A_ex", ""),
            len_B_ex=some_results.get("len_B_ex", ""),
            pattern_analysis = some_results.get("pattern_analysis", ""),
            chatto_counsel = some_results.get("chatto_counsel", ""),
            chatto_counsel_tips = some_results.get("chatto_counsel_tips", ""),
        )

        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )


# 채팅 MBTI 분석
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


        # 1. Gemini API 클라이언트 초기화 및 MBTI 분석 함수 호출
        analysis_option = {
            "start": analysis_start,
            "end": analysis_end
        }
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        mbti_results, num_chat = mbti_analysis_with_gemini(chat, client, analysis_option)

        # 2. ResultPlayMBTI 객체 생성
        result = ResultPlayMBTI.objects.create(
            type=3,
            title=chat.title,
            people_num=chat.people_num,
            is_saved=1,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            num_chat=num_chat,
            chat=chat,
            user=author,
        )

        # 3. 분석 결과가 비어있거나 에러가 있는 경우 처리
        if not mbti_results or "error_message" in mbti_results[0]:
            # 에러 상황에 맞게 응답 처리
            return Response({"error": "MBTI 분석에 실패했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. 분석 결과를 바탕으로 DB 업데이트
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
            cnt_INTJ=0,
            cnt_INTP=0,
            cnt_ENTJ=0,
            cnt_ENTP=0,
            cnt_INFJ=0,
            cnt_INFP=0,
            cnt_ENFJ=0,
            cnt_ENFP=0,
            cnt_ISTJ=0,
            cnt_ISFJ=0,
            cnt_ESTJ=0,
            cnt_ESFJ=0,
            cnt_ISTP=0,
            cnt_ISFP=0,
            cnt_ESTP=0,
            cnt_ESFP=0
        )
        totals = {
            'I': 0, 'E': 0, 'S': 0, 'N': 0, 'F': 0, 'T': 0, 'J': 0, 'P': 0,
            'INTJ': 0, 'INTP': 0, 'ENTJ': 0, 'ENTP': 0,
            'INFJ': 0, 'INFP': 0, 'ENFJ': 0, 'ENFP': 0, 
            'ISTJ': 0, 'ISFJ': 0, 'ESTJ': 0, 'ESFJ': 0, 
            'ISTP': 0, 'ISFP': 0, 'ESTP': 0, 'ESFP': 0
        }

        # 각 참여자별 분석 결과를 ResultPlayMBTISpecPersonal에 저장
        for person_data in mbti_results[:-1]:
            ResultPlayMBTISpecPersonal.objects.create(
                spec=spec,
                name=person_data.get("name", ""),
                MBTI=person_data.get("MBTI", ""),
                summary=person_data.get("summary", ""),
                desc=person_data.get("desc", ""),
                position=person_data.get("position", ""),
                personality=person_data.get("personality", ""),
                style=person_data.get("style", ""),
                moment_ex=person_data.get("moment_ex", ""),
                moment_desc=person_data.get("moment_desc", ""),
                momentIE_ex=person_data.get("momentIE_ex", ""),
                momentIE_desc=person_data.get("momentIE_desc", ""),
                momentSN_ex=person_data.get("momentSN_ex", ""),
                momentSN_desc=person_data.get("momentSN_desc", ""),
                momentFT_ex=person_data.get("momentFT_ex", ""),
                momentFT_desc=person_data.get("momentFT_desc", ""),
                momentJP_ex=person_data.get("momentJP_ex", ""),
                momentJP_desc=person_data.get("momentJP_desc", ""),
            )
            # MBTI 지표별 카운트 업데이트
            mbti = person_data.get("MBTI", "")
            for char in mbti:
                if char in totals:
                    totals[char] += 1
            # MBTI 유형별 카운트 업데이트
            if mbti in totals:
                totals[mbti] += 1

        # spec 객체에 전체 카운트 업데이트
        spec.total_I = totals['I']
        spec.total_E = totals['E']
        spec.total_S = totals['S']
        spec.total_N = totals['N']
        spec.total_F = totals['F']
        spec.total_T = totals['T']
        spec.total_J = totals['J']
        spec.total_P = totals['P']
        spec.cnt_INTJ = totals['INTJ']
        spec.cnt_INTP = totals['INTP']
        spec.cnt_ENTJ = totals['ENTJ']
        spec.cnt_ENTP = totals['ENTP']
        spec.cnt_INFJ = totals['INFJ']
        spec.cnt_INFP = totals['INFP']
        spec.cnt_ENFJ = totals['ENFJ']
        spec.cnt_ENFP = totals['ENFP']
        spec.cnt_ISTJ = totals['ISTJ']
        spec.cnt_ISFJ = totals['ISFJ']
        spec.cnt_ESTJ = totals['ESTJ']
        spec.cnt_ESFJ = totals['ESFJ']
        spec.cnt_ISTP = totals['ISTP']
        spec.cnt_ISFP = totals['ISFP']
        spec.cnt_ESTP = totals['ESTP']
        spec.cnt_ESFP = totals['ESFP']
        spec.save()

        return Response(
            {
                "result_id": result.result_id,
            },
            status=status.HTTP_201_CREATED,
        )



##################################################################


# 특정 케미 분석 결과 조회, 특정 케미 분석 결과 삭제
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
            if result.user != author:
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
            if result.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultPlayChem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


# 특정 썸 분석 결과 조회, 특정 썸 분석 결과 삭제
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
            if result.user != author:
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
            if result.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultPlaySome.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


# 특정 MBTI 분석 결과 조회, 특정 MBTI 분석 결과 삭제
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

            if result.user != author:
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
            if result.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ResultPlayMBTI.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)



###################################################################


# 모든 분석 결과 조회
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

        chem_results = ResultPlayChem.objects.filter(user=author)
        some_results = ResultPlaySome.objects.filter(user=author)
        mbti_results = ResultPlayMBTI.objects.filter(user=author)

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


# 게스트용 특정 케미 분석 결과 조회
class PlayChemResultDetailViewGuest(APIView):
    @swagger_auto_schema(
        operation_id="게스트용 특정 케미 분석 결과 조회",
        operation_description="게스트(비로그인) 사용자가 공유된 UUID로 특정 케미 분석 결과를 조회합니다.",
        responses={200: ChemAllSerializerPlay, 404: "Not Found"},
    )
    def get(self, request, uuid):
        try:
            share = UuidChem.objects.get(uuid=uuid)
            result = ResultPlayChem.objects.get(result_id=share.result.result_id)       
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


# 게스트용 특정 썸 분석 결과 조회
class PlaySomeResultDetailViewGuest(APIView):
    @swagger_auto_schema(
        operation_id="게스트용 특정 썸 분석 결과 조회",
        operation_description="게스트(비로그인) 사용자가 공유된 UUID로 특정 썸 분석 결과를 조회합니다.",
        responses={200: SomeAllSerializerPlay, 404: "Not Found"},
    )
    def get(self, request, uuid):
        try:
            share = UuidSome.objects.get(uuid=uuid)
            result = ResultPlaySome.objects.get(result_id=share.result.result_id)
            spec = ResultPlaySomeSpec.objects.get(result=result)
            payload = {
                "result": result,
                "spec": spec,
            }
            serializer = SomeAllSerializerPlay(payload)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)


# 게스트용 특정 MBTI 분석 결과 조회
class PlayMBTIResultDetailViewGuest(APIView):
    @swagger_auto_schema(
        operation_id="게스트용 특정 MBTI 분석 결과 조회",
        operation_description="게스트(비로그인) 사용자가 공유된 UUID로 특정 MBTI 분석 결과를 조회합니다.",
        responses={200: MBTIAllSerializerPlay, 404: "Not Found"},
    )
    def get(self, request, uuid):
        try:
            share = UuidMBTI.objects.get(uuid=uuid)
            result = ResultPlayMBTI.objects.get(result_id=share.result.result_id)
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


###################################################################


# UUID 생성
class GenerateUUIDView(APIView):
    @swagger_auto_schema(
        operation_id="UUID 생성",
        operation_description="특정 분석 결과(chem/some/mbti)에 대한 공유용 UUID를 생성합니다.",
        request_body=UuidRequestSerializerPlay,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: ChemUuidSerializerPlay,
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
        },
    )
    def post(self, request, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        new_uuid = str(uuid.uuid4())

        request_serializer = UuidRequestSerializerPlay(data=request.data)
        if request_serializer.is_valid() is False:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        type = request_serializer.validated_data["type"]

        if type == "chem":
            try:
                result = ResultPlayChem.objects.get(result_id=result_id)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if result.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            share = UuidChem.objects.create(
                result=result,
                uuid=new_uuid,
            )
            serializer = ChemUuidSerializerPlay(share)

        elif type == "some":
            try:
                result = ResultPlaySome.objects.get(result_id=result_id)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if result.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            share = UuidSome.objects.create(
                result=result,
                uuid=new_uuid,
            )
            serializer = SomeUuidSerializerPlay(share)

        elif type == "mbti":
            try:
                result = ResultPlayMBTI.objects.get(result_id=result_id)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if result.user != author:
                return Response(status=status.HTTP_403_FORBIDDEN)
            share = UuidMBTI.objects.create(
                result=result,
                uuid=new_uuid,
            )
            serializer = SomeUuidSerializerPlay(share)

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# UUID --> 케미/썸/MBTI 변환
class UuidToTypeView(APIView):
    @swagger_auto_schema(
        operation_id="UUID로 타입 조회",
        operation_description="UUID를 통해 해당 결과가 chem/some/mbti 중 어떤 타입인지 반환합니다.",
        manual_parameters=[
            openapi.Parameter(
                "uuid",
                openapi.IN_PATH,
                description="공유용 UUID",
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                description="타입 반환 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(type=openapi.TYPE_STRING, description="결과 타입 (chem/some/mbti)"),
                    },
                ),
            ),
            404: openapi.Response(
                description="UUID에 해당하는 타입 없음",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "type": openapi.Schema(type=openapi.TYPE_STRING, description="None"),
                    },
                ),
            ),
        },
    )
    def get(self, request, uuid):
        if UuidChem.objects.filter(uuid=uuid).exists():
            return Response({"type": "chem"}, status=status.HTTP_200_OK)
        elif UuidSome.objects.filter(uuid=uuid).exists():
            return Response({"type": "some"}, status=status.HTTP_200_OK)
        elif UuidMBTI.objects.filter(uuid=uuid).exists():
            return Response({"type": "mbti"}, status=status.HTTP_200_OK)
        else:
            return Response({"type": None}, status=status.HTTP_404_NOT_FOUND)
                

# 타입 + resultid --> UUID 조회
class TypeResultIdToUuidView(APIView):
    @swagger_auto_schema(
        operation_id="타입+resultid로 UUID 조회",
        operation_description="타입(chem/some/mbti)과 result_id로 해당 결과의 공유용 UUID를 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="UUID 반환 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "uuid": openapi.Schema(type=openapi.TYPE_STRING, description="공유용 UUID"),
                    },
                ),
            ),
            401: "Unauthorized",
            404: "Not Found",
            400: "Bad Request",
        },
    )
    def get(self, request, type, result_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        if type == "chem":
            try:
                result = ResultPlayChem.objects.get(result_id=result_id)
                share = UuidChem.objects.filter(result=result).first()
                return Response({"uuid": share.uuid}, status=status.HTTP_200_OK)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)

        elif type == "some":
            try:
                result = ResultPlaySome.objects.get(result_id=result_id)
                share = UuidSome.objects.filter(result=result).first()
                return Response({"uuid": share.uuid}, status=status.HTTP_200_OK)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)

        elif type == "mbti":
            try:
                result = ResultPlayMBTI.objects.get(result_id=result_id)
                share = UuidMBTI.objects.filter(result=result).first()
                return Response({"uuid": share.uuid}, status=status.HTTP_200_OK)
            except:
                return Response(status=status.HTTP_404_NOT_FOUND)

        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)



###################################################################


client = genai.Client(api_key=settings.GEMINI_API_KEY)

def generate_ChemQuiz(result: ResultPlayChem, client: genai.Client) -> dict:
    
    # 퀴즈 생성에 참고할 자료들 가져오기
    chat = result.chat
    if not chat.file:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    try:
        spec = ResultPlayChemSpec.objects.get(result=result)
    except:
        return {"detail": "케미 분석 결과가 존재하지 않습니다."}
    
    # 채팅 파일 열기
    file_path = chat.file.path
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chat_content = f.read()  # 파일 전체 내용 읽기
    except FileNotFoundError:
        return {"detail": "채팅 파일이 존재하지 않습니다."}

    names = [spec.name_0, spec.name_1, spec.name_2, spec.name_3, spec.name_4]
    scores = [[0 for _ in range(spec.tablesize)] for _ in range(spec.tablesize)]
    for i in range(spec.tablesize):
        for j in range(spec.tablesize):
            if i == j:
                scores[i][j] = 0
            else:
                x = ResultPlayChemSpecTable.objects.get(spec=spec, row=i, column=j)
                scores[i][j] = x.interaction

    prompt = f"""
        당신은 카카오톡 대화 파일을 분석하여 대화참여자들 사이의 케미를 평가하는 전문가입니다.
        주어진 채팅 대화 내용과 케미 분석 결과를 바탕으로 두 사람에 대한 케미 퀴즈 10개를 생성해주세요.
        썸 퀴즈는 4지선다형으로, 정답은 1개입니다.

        주어진 채팅 대화 내용: 
        {chat_content}

        케미 분석 결과: 
        본 대화에는 총 {result.people_num}명의 참여자가 있으며, 톡방 제목은 '{chat.title}'입니다.
        참가자들은 {result.relationship} 관계이며, 상황은 {result.situation}입니다.

        케미 분석 세부 결과:
        종합케미점수는 {spec.score_main}점, 그에 대한 요약은 {spec.summary_main}입니다.
        총 {result.people_num}명의 참여자 중 상위 {spec.tablesize}명에 대한 분석이 중심이 됩니다.
        상위 {spec.tablesize}명의 이름은 순서대로 {[name for name in names[:spec.tablesize]]}입니다.
        상위 {spec.tablesize}명의 서로에 대한 케미 점수는 다음과 같습니다.
        {spec.name_0} --> {spec.name_1} 케미 점수: {scores[0][1]}
        {spec.name_0} --> {spec.name_2} 케미 점수: {scores[0][2]}
        {spec.name_0} --> {spec.name_3} 케미 점수: {scores[0][3]}
        {spec.name_0} --> {spec.name_4} 케미 점수: {scores[0][4]}
        {spec.name_1} --> {spec.name_0} 케미 점수: {scores[1][0]}
        {spec.name_1} --> {spec.name_2} 케미 점수: {scores[1][2]}
        {spec.name_1} --> {spec.name_3} 케미 점수: {scores[1][3]}
        {spec.name_1} --> {spec.name_4} 케미 점수: {scores[1][4]}
        {spec.name_2} --> {spec.name_0} 케미 점수: {scores[2][0]}
        {spec.name_2} --> {spec.name_1} 케미 점수: {scores[2][1]}
        {spec.name_2} --> {spec.name_3} 케미 점수: {scores[2][3]}
        {spec.name_2} --> {spec.name_4} 케미 점수: {scores[2][4]}
        {spec.name_3} --> {spec.name_0} 케미 점수: {scores[3][0]}
        {spec.name_3} --> {spec.name_1} 케미 점수: {scores[3][1]}
        {spec.name_3} --> {spec.name_2} 케미 점수: {scores[3][2]}
        {spec.name_3} --> {spec.name_4} 케미 점수: {scores[3][4]}
        {spec.name_4} --> {spec.name_0} 케미 점수: {scores[4][0]}
        {spec.name_4} --> {spec.name_1} 케미 점수: {scores[4][1]}
        {spec.name_4} --> {spec.name_2} 케미 점수: {scores[4][2]}
        {spec.name_4} --> {spec.name_3} 케미 점수: {scores[4][3]}
        해당 케미점수 결과에서 케미 점수가 0점이거나 이름이 비어있는 경우는 무시해주세요.

        케미 순위 1위는 {spec.top1_A}와 {spec.top1_B}이며, 이들의 케미 점수는 {spec.top1_score}점입니다.
        케미 순위 1위에 대한 간단한 설명은 {spec.top1_comment}입니다.
        케미 순위 2위는 {spec.top2_A}와 {spec.top2_B}이며, 이들의 케미 점수는 {spec.top2_score}점입니다.
        케미 순위 2위에 대한 간단한 설명은 {spec.top2_comment}입니다.
        케미 순위 3위는 {spec.top3_A}와 {spec.top3_B}이며, 이들의 케미 점수는 {spec.top3_score}점입니다.
        케미 순위 3위에 대한 간단한 설명은 {spec.top3_comment}입니다.

        대화 톤의 비율은, 긍정적인 표현이 {spec.tone_pos}%, 농담/유머가 {spec.tone_humer}%, 기타가 {100-spec.tone_pos-spec.tone_humer}%입니다.
        예시대화로는 {spec.tone_ex1}, {spec.tone_ex2}, {spec.tone_ex3}가 있습니다. 이에 대한 설명은 {spec.tone_analysis}입니다.

        응답 패턴으로는, 우선 평균 {spec.resp_time}분의 응답 시간을 보였으며, 즉각 응답 비율은 {spec.resp_ratio}%,
        읽씹 발생률은 {spec.ignore}%입니다. 그에 대한 분석은 {spec.resp_analysis}입니다.

        대화 주세의 비율은, {spec.topic1}가 {spec.topic1_ratio}%, {spec.topic2}가 {spec.topic2_ratio}%,
        {spec.topic3}가 {spec.topic3_ratio}%, {spec.topic4}가 {spec.topic4_ratio}%입니다.
        
        종합적인 사람들 간의 분석 결과는 {spec.chatto_analysis}입니다.
        케미를 더 올리기 위한 분석과 팁은 {spec.chatto_levelup}, {spec.chatto_levelup_tips}입니다.

        당신은 지금까지 제공된 위의 정보를 바탕으로 다음과 같은 케미 퀴즈 10개를 생성해야 합니다:
        당신의 응답은 다음과 반드시 같은 형식을 따라야 합니다:

        문제1: [문제 내용]
        선택지1-1: [선택지 1 내용]
        선택지1-2: [선택지 2 내용]
        선택지1-3: [선택지 3 내용]
        선택지1-4: [선택지 4 내용]
        정답1: [정답 선택지 번호 (1, 2, 3, 4)]
        문제2: [문제 내용]
        선택지2-1: [선택지 1 내용]
        선택지2-2: [선택지 2 내용]
        선택지2-3: [선택지 3 내용]
        선택지2-4: [선택지 4 내용]
        정답2: [정답 선택지 번호 (1, 2, 3, 4)]
        문제3: [문제 내용]
        선택지3-1: [선택지 1 내용]  
        선택지3-2: [선택지 2 내용]
        선택지3-3: [선택지 3 내용]
        선택지3-4: [선택지 4 내용]
        정답3: [정답 선택지 번호 (1, 2, 3, 4)]
        문제4: [문제 내용]
        선택지4-1: [선택지 1 내용]
        선택지4-2: [선택지 2 내용]
        선택지4-3: [선택지 3 내용]
        선택지4-4: [선택지 4 내용]
        정답4: [정답 선택지 번호 (1, 2, 3, 4)]
        문제5: [문제 내용]
        선택지5-1: [선택지 1 내용]
        선택지5-2: [선택지 2 내용]
        선택지5-3: [선택지 3 내용]
        선택지5-4: [선택지 4 내용]
        정답5: [정답 선택지 번호 (1, 2, 3, 4)]
        문제6: [문제 내용]
        선택지6-1: [선택지 1 내용]
        선택지6-2: [선택지 2 내용]
        선택지6-3: [선택지 3 내용]
        선택지6-4: [선택지 4 내용]
        정답6: [정답 선택지 번호 (1, 2, 3, 4)]
        문제7: [문제 내용]
        선택지7-1: [선택지 1 내용]
        선택지7-2: [선택지 2 내용]
        선택지7-3: [선택지 3 내용]
        선택지7-4: [선택지 4 내용]
        정답7: [정답 선택지 번호 (1, 2, 3, 4)]
        문제8: [문제 내용]
        선택지8-1: [선택지 1 내용]
        선택지8-2: [선택지 2 내용]
        선택지8-3: [선택지 3 내용]
        선택지8-4: [선택지 4 내용]
        정답8: [정답 선택지 번호 (1, 2, 3, 4)]
        문제9: [문제 내용]
        선택지9-1: [선택지 1 내용]
        선택지9-2: [선택지 2 내용]
        선택지9-3: [선택지 3 내용]
        선택지9-4: [선택지 4 내용]
        정답9: [정답 선택지 번호 (1, 2, 3, 4)]
        문제10: [문제 내용]
        선택지10-1: [선택지 1 내용]
        선택지10-2: [선택지 2 내용]
        선택지10-3: [선택지 3 내용]
        선택지10-4: [선택지 4 내용]
        정답10: [정답 선택지 번호 (1, 2, 3, 4)]
        """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    response_text = response.text
    
    print(f"Gemini로 생성된 케미 퀴즈 응답: {response_text}")

    return {
        "question1": parse_response(r"문제1:\s*(.+)", response_text),
        "choice1-1": parse_response(r"선택지1-1:\s*(.+)", response_text),
        "choice1-2": parse_response(r"선택지1-2:\s*(.+)", response_text),
        "choice1-3": parse_response(r"선택지1-3:\s*(.+)", response_text),
        "choice1-4": parse_response(r"선택지1-4:\s*(.+)", response_text),
        "answer1": parse_response(r"정답1:\s*(\d+)", response_text, is_int=True),
        "question2": parse_response(r"문제2:\s*(.+)", response_text),
        "choice2-1": parse_response(r"선택지2-1:\s*(.+)", response_text),
        "choice2-2": parse_response(r"선택지2-2:\s*(.+)", response_text),
        "choice2-3": parse_response(r"선택지2-3:\s*(.+)", response_text),
        "choice2-4": parse_response(r"선택지2-4:\s*(.+)", response_text),
        "answer2": parse_response(r"정답2:\s*(\d+)", response_text, is_int=True),
        "question3": parse_response(r"문제3:\s*(.+)", response_text),
        "choice3-1": parse_response(r"선택지3-1:\s*(.+)", response_text),
        "choice3-2": parse_response(r"선택지3-2:\s*(.+)", response_text),
        "choice3-3": parse_response(r"선택지3-3:\s*(.+)", response_text),
        "choice3-4": parse_response(r"선택지3-4:\s*(.+)", response_text),
        "answer3": parse_response(r"정답3:\s*(\d+)", response_text, is_int=True),
        "question4": parse_response(r"문제4:\s*(.+)", response_text),
        "choice4-1": parse_response(r"선택지4-1:\s*(.+)", response_text),
        "choice4-2": parse_response(r"선택지4-2:\s*(.+)", response_text),
        "choice4-3": parse_response(r"선택지4-3:\s*(.+)", response_text),
        "choice4-4": parse_response(r"선택지4-4:\s*(.+)", response_text),
        "answer4": parse_response(r"정답4:\s*(\d+)", response_text, is_int=True),
        "question5": parse_response(r"문제5:\s*(.+)", response_text),
        "choice5-1": parse_response(r"선택지5-1:\s*(.+)", response_text),
        "choice5-2": parse_response(r"선택지5-2:\s*(.+)", response_text),
        "choice5-3": parse_response(r"선택지5-3:\s*(.+)", response_text),
        "choice5-4": parse_response(r"선택지5-4:\s*(.+)", response_text),
        "answer5": parse_response(r"정답5:\s*(\d+)", response_text, is_int=True),
        "question6": parse_response(r"문제6:\s*(.+)", response_text),
        "choice6-1": parse_response(r"선택지6-1:\s*(.+)", response_text),
        "choice6-2": parse_response(r"선택지6-2:\s*(.+)", response_text),
        "choice6-3": parse_response(r"선택지6-3:\s*(.+)", response_text),
        "choice6-4": parse_response(r"선택지6-4:\s*(.+)", response_text),
        "answer6": parse_response(r"정답6:\s*(\d+)", response_text, is_int=True),
        "question7": parse_response(r"문제7:\s*(.+)", response_text),
        "choice7-1": parse_response(r"선택지7-1:\s*(.+)", response_text),
        "choice7-2": parse_response(r"선택지7-2:\s*(.+)", response_text),
        "choice7-3": parse_response(r"선택지7-3:\s*(.+)", response_text),
        "choice7-4": parse_response(r"선택지7-4:\s*(.+)", response_text),
        "answer7": parse_response(r"정답7:\s*(\d+)", response_text, is_int=True),
        "question8": parse_response(r"문제8:\s*(.+)", response_text),
        "choice8-1": parse_response(r"선택지8-1:\s*(.+)", response_text),
        "choice8-2": parse_response(r"선택지8-2:\s*(.+)", response_text),
        "choice8-3": parse_response(r"선택지8-3:\s*(.+)", response_text),
        "choice8-4": parse_response(r"선택지8-4:\s*(.+)", response_text),
        "answer8": parse_response(r"정답8:\s*(\d+)", response_text, is_int=True),
        "question9": parse_response(r"문제9:\s*(.+)", response_text),
        "choice9-1": parse_response(r"선택지9-1:\s*(.+)", response_text),
        "choice9-2": parse_response(r"선택지9-2:\s*(.+)", response_text),
        "choice9-3": parse_response(r"선택지9-3:\s*(.+)", response_text),
        "choice9-4": parse_response(r"선택지9-4:\s*(.+)", response_text),
        "answer9": parse_response(r"정답9:\s*(\d+)", response_text, is_int=True),
        "question10": parse_response(r"문제10:\s*(.+)", response_text),
        "choice10-1": parse_response(r"선택지10-1:\s*(.+)", response_text),
        "choice10-2": parse_response(r"선택지10-2:\s*(.+)", response_text),
        "choice10-3": parse_response(r"선택지10-3:\s*(.+)", response_text),
        "choice10-4": parse_response(r"선택지10-4:\s*(.+)", response_text),
        "answer10": parse_response(r"정답10:\s*(\d+)", response_text, is_int=True),
    }

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

        if ChemQuiz.objects.filter(result=result).exists():
            return Response({"detail": "이미 해당 분석 결과에 대한 퀴즈가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 케미 퀴즈 생성
        quiz_data = generate_ChemQuiz(result, client)

        if quiz_data == {"detail": "채팅 파일이 존재하지 않습니다."}:
            return Response({"detail": "채팅 파일이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)
        elif quiz_data == {"detail": "케미 분석 결과가 존재하지 않습니다."}:
            return Response({"detail": "케미 분석 결과가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        quiz = ChemQuiz.objects.create(
            result=result,
            question_num=10,
            solved_num=0,
            avg_score=0,
        )

        for i in range(quiz.question_num):
            ChemQuizQuestion.objects.create(
                quiz=quiz,
                question_index=i,
                question=quiz_data[f"question{i+1}"],
                choice1=quiz_data[f"choice{i+1}-1"],
                choice2=quiz_data[f"choice{i+1}-2"],
                choice3=quiz_data[f"choice{i+1}-3"],
                choice4=quiz_data[f"choice{i+1}-4"],
                answer=quiz_data[f"answer{i+1}"],
                correct_num=0,
                count1=0,
                count2=0,
                count3=0,
                count4=0,
            )
        
        result.is_quized = True
        result.save()
        
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

        result.is_quized = False
        result.save()

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


# 케미 퀴즈 문제 리스트 조회 (게스트용)
class PlayChemQuizQuestionListGuestView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 문제 리스트 조회 (게스트용)",
        operation_description="특정 케미 분석 결과에 대한 퀴즈의 문제 리스트를 조회합니다. (게스트용)",
        responses={
            200: ChemQuizQuestionSerializerPlay(many=True),
            404: "Not Found"
        },
    )
    def get(self, request, uuid):
        try:
            share = UuidChem.objects.get(uuid=uuid)
            result_id = share.result.result_id
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
            201: ChemQuizPersonalSerializerPlay,
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
        
        QP = ChemQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        serializer = ChemQuizPersonalSerializerPlay(QP)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# 케미 퀴즈 풀이 시작 (게스트용)
class PlayChemQuizStartGuestView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 풀이 시작 (게스트용)",
        operation_description="케미 퀴즈 풀이를 게스트로 시작합니다.",
        request_body=ChemQuizStartRequestSerializerPlay,
        responses={
            201: ChemQuizPersonalSerializerPlay,
            400: "Bad Request",
            404: "Not Found"
        },
    )
    def post(self, request, uuid):
        serializer = ChemQuizStartRequestSerializerPlay(data=request.data)
        
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        name = serializer.validated_data["name"]

        try:
            share = UuidChem.objects.get(uuid=uuid)
            result_id = share.result.result_id
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if ChemQuizPersonal.objects.filter(quiz__result__result_id=result_id, name=name).exists():
            return Response({"detail": "이미 해당 이름의 퀴즈 풀이가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        QP = ChemQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        serializer = ChemQuizPersonalSerializerPlay(QP)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
            200: ChemQuizPersonalDetailSerializerPlay,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(QP_id=QP_id)
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
    def delete(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(QP_id=QP_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        quiz_personal.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# 케미 퀴즈 결과 (문제별 리스트) 한 사람 조회 (게스트용)
class PlayChemQuizPersonalGuestView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 결과 (문제별 리스트) 한 사람 조회 (게스트용)",
        operation_description="케미 퀴즈 결과를 게스트로 한 사람 기준으로 조회합니다.",
        responses={
            200: ChemQuizPersonalDetailSerializerPlay,
            404: "Not Found"
        },
    )
    def get(self, request, uuid, QP_id):
        try:
            share = UuidChem.objects.get(uuid=uuid)
            result_id = share.result.result_id
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(QP_id=QP_id)
            quiz_personal_details = ChemQuizPersonalDetail.objects.filter(QP=quiz_personal)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = ChemQuizPersonalDetailSerializerPlay(quiz_personal_details, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


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
            404: "Not Found",
        },
    )
    def post(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        request_serializer = ChemQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(QP_id=QP_id)
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

        # 퀴즈 통계 업데이트
        quiz.solved_num += 1
        quiz.avg_score = (
            (quiz.avg_score * (quiz.solved_num - 1) + quiz_personal.score) / quiz.solved_num
        )
        quiz.save()

        # 각 문제별 정답 통계 업데이트
        for idx in range(quiz.question_num):
            try:
                question = ChemQuizQuestion.objects.get(quiz=quiz, question_index=idx)
                # 해당 문제에 대한 정답자 수 업데이트
                correct_count = ChemQuizPersonalDetail.objects.filter(
                    QP=quiz_personal, question=question, result=True
                ).count()
                if correct_count:
                    question.correct_num += 1
                    question.save()
            except ChemQuizQuestion.DoesNotExist:
                continue

        return Response(status=status.HTTP_200_OK)


# 케미 퀴즈 풀이 제출 (게스트용) (여러 문제 답변을 한 번에 제출)
class PlayChemQuizSubmitGuestView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 제출 (게스트용)",
        operation_description="케미 퀴즈 풀이를 게스트로 제출합니다. (여러 문제 답변을 한 번에 제출)",
        request_body=ChemQuizSubmitRequestSerializerPlay(many=True),
        responses={
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
        },
    )
    def post(self, request, uuid, QP_id):
        request_serializer = ChemQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            share = UuidChem.objects.get(uuid=uuid)
            result_id = share.result.result_id
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            quiz_personal = ChemQuizPersonal.objects.get(QP_id=QP_id)
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
        
        # 퀴즈 통계 업데이트
        quiz.solved_num += 1
        quiz.avg_score = (
            (quiz.avg_score * (quiz.solved_num - 1) + quiz_personal.score) / quiz.solved_num
        )
        quiz.save()

        # 각 문제별 정답 통계 업데이트
        for idx in range(quiz.question_num):
            try:
                question = ChemQuizQuestion.objects.get(quiz=quiz, question_index=idx)
                # 해당 문제에 대한 정답자 수 업데이트
                correct_count = ChemQuizPersonalDetail.objects.filter(
                    QP=quiz_personal, question=question, result=True
                ).count()
                if correct_count:
                    question.correct_num += 1
                    question.save()
            except ChemQuizQuestion.DoesNotExist:
                continue

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
            

# 케미 퀴즈 문제 수정, 삭제
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
            403: "Forbidden",
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
        
        if quiz.result.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
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
 
    @swagger_auto_schema(
        operation_id="케미 퀴즈 문제 삭제",
        operation_description="케미 퀴즈의 특정 문제를 삭제합니다.",
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
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found"
        },
    )
    def delete(self, request, result_id, question_index):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayChem.objects.get(result_id=result_id)
            quiz = ChemQuiz.objects.get(result=result)
            question = ChemQuizQuestion.objects.get(quiz=quiz, question_index=question_index)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if quiz.result.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        index = question.question_index

        # 해당 문제 삭제
        question.delete()

        # 해당 문제가 속하는 퀴즈의 문제 수 감소
        quiz.question_num -= 1

        # 문제 삭제 후 퀴즈 통계 초기화
        quiz.solved_num = 0  
        quiz.avg_score = 0
        quiz.save()

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = ChemQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            if q.question_index > index:
                q.question_index -= 1
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        ChemQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_200_OK)


def generate_OneChemQuiz(result: ResultPlayChem, client: genai.Client) -> dict:
    
    # 퀴즈 생성에 참고할 자료들 가져오기
    chat = result.chat
    if not chat.file:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    try:
        spec = ResultPlayChemSpec.objects.get(result=result)
    except:
        return {"detail": "케미 분석 결과가 존재하지 않습니다."}
    
    # 채팅 파일 열기
    file_path = chat.file.path
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chat_content = f.read()  # 파일 전체 내용 읽기
    except FileNotFoundError:
        return {"detail": "채팅 파일이 존재하지 않습니다."}

    names = [spec.name_0, spec.name_1, spec.name_2, spec.name_3, spec.name_4]
    scores = [[0 for _ in range(spec.tablesize)] for _ in range(spec.tablesize)]
    for i in range(spec.tablesize):
        for j in range(spec.tablesize):
            if i == j:
                scores[i][j] = 0
            else:
                x = ResultPlayChemSpecTable.objects.get(spec=spec, row=i, column=j)
                scores[i][j] = x.interaction

    prompt = f"""
        당신은 카카오톡 대화 파일을 분석하여 대화참여자들 사이의 케미를 평가하는 전문가입니다.
        주어진 채팅 대화 내용과 케미 분석 결과를 바탕으로 두 사람에 대한 케미 퀴즈 1개를 생성해주세요.
        썸 퀴즈는 4지선다형으로, 정답은 1개입니다.

        주어진 채팅 대화 내용: 
        {chat_content}

        케미 분석 결과: 
        본 대화에는 총 {result.people_num}명의 참여자가 있으며, 톡방 제목은 '{chat.title}'입니다.
        참가자들은 {result.relationship} 관계이며, 상황은 {result.situation}입니다.

        케미 분석 세부 결과:
        종합케미점수는 {spec.score_main}점, 그에 대한 요약은 {spec.summary_main}입니다.
        총 {result.people_num}명의 참여자 중 상위 {spec.tablesize}명에 대한 분석이 중심이 됩니다.
        상위 {spec.tablesize}명의 이름은 순서대로 {[name for name in names[:spec.tablesize]]}입니다.
        상위 {spec.tablesize}명의 서로에 대한 케미 점수는 다음과 같습니다.
        {spec.name_0} --> {spec.name_1} 케미 점수: {scores[0][1]}
        {spec.name_0} --> {spec.name_2} 케미 점수: {scores[0][2]}
        {spec.name_0} --> {spec.name_3} 케미 점수: {scores[0][3]}
        {spec.name_0} --> {spec.name_4} 케미 점수: {scores[0][4]}
        {spec.name_1} --> {spec.name_0} 케미 점수: {scores[1][0]}
        {spec.name_1} --> {spec.name_2} 케미 점수: {scores[1][2]}
        {spec.name_1} --> {spec.name_3} 케미 점수: {scores[1][3]}
        {spec.name_1} --> {spec.name_4} 케미 점수: {scores[1][4]}
        {spec.name_2} --> {spec.name_0} 케미 점수: {scores[2][0]}
        {spec.name_2} --> {spec.name_1} 케미 점수: {scores[2][1]}
        {spec.name_2} --> {spec.name_3} 케미 점수: {scores[2][3]}
        {spec.name_2} --> {spec.name_4} 케미 점수: {scores[2][4]}
        {spec.name_3} --> {spec.name_0} 케미 점수: {scores[3][0]}
        {spec.name_3} --> {spec.name_1} 케미 점수: {scores[3][1]}
        {spec.name_3} --> {spec.name_2} 케미 점수: {scores[3][2]}
        {spec.name_3} --> {spec.name_4} 케미 점수: {scores[3][4]}
        {spec.name_4} --> {spec.name_0} 케미 점수: {scores[4][0]}
        {spec.name_4} --> {spec.name_1} 케미 점수: {scores[4][1]}
        {spec.name_4} --> {spec.name_2} 케미 점수: {scores[4][2]}
        {spec.name_4} --> {spec.name_3} 케미 점수: {scores[4][3]}
        해당 케미점수 결과에서 케미 점수가 0점이거나 이름이 비어있는 경우는 무시해주세요.

        케미 순위 1위는 {spec.top1_A}와 {spec.top1_B}이며, 이들의 케미 점수는 {spec.top1_score}점입니다.
        케미 순위 1위에 대한 간단한 설명은 {spec.top1_comment}입니다.
        케미 순위 2위는 {spec.top2_A}와 {spec.top2_B}이며, 이들의 케미 점수는 {spec.top2_score}점입니다.
        케미 순위 2위에 대한 간단한 설명은 {spec.top2_comment}입니다.
        케미 순위 3위는 {spec.top3_A}와 {spec.top3_B}이며, 이들의 케미 점수는 {spec.top3_score}점입니다.
        케미 순위 3위에 대한 간단한 설명은 {spec.top3_comment}입니다.

        대화 톤의 비율은, 긍정적인 표현이 {spec.tone_pos}%, 농담/유머가 {spec.tone_humer}%, 기타가 {100-spec.tone_pos-spec.tone_humer}%입니다.
        예시대화로는 {spec.tone_ex1}, {spec.tone_ex2}, {spec.tone_ex3}가 있습니다. 이에 대한 설명은 {spec.tone_analysis}입니다.

        응답 패턴으로는, 우선 평균 {spec.resp_time}분의 응답 시간을 보였으며, 즉각 응답 비율은 {spec.resp_ratio}%,
        읽씹 발생률은 {spec.ignore}%입니다. 그에 대한 분석은 {spec.resp_analysis}입니다.

        대화 주세의 비율은, {spec.topic1}가 {spec.topic1_ratio}%, {spec.topic2}가 {spec.topic2_ratio}%,
        {spec.topic3}가 {spec.topic3_ratio}%, {spec.topic4}가 {spec.topic4_ratio}%입니다.
        
        종합적인 사람들 간의 분석 결과는 {spec.chatto_analysis}입니다.
        케미를 더 올리기 위한 분석과 팁은 {spec.chatto_levelup}, {spec.chatto_levelup_tips}입니다.

        당신은 지금까지 제공된 위의 정보를 바탕으로 다음과 같은 케미 퀴즈 1개를 생성해야 합니다:
        당신의 응답은 다음과 반드시 같은 형식을 따라야 합니다:

        문제: [문제 내용]
        선택지1: [선택지 1 내용]
        선택지2: [선택지 2 내용]
        선택지3: [선택지 3 내용]
        선택지4: [선택지 4 내용]
        정답: [정답 선택지 번호 (1, 2, 3, 4)]
        """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    response_text = response.text
    
    print(f"Gemini로 생성된 케미 퀴즈 응답: {response_text}")

    return {
        "question": parse_response(r"문제:\s*(.+)", response_text),
        "choice1": parse_response(r"선택지1:\s*(.+)", response_text),
        "choice2": parse_response(r"선택지2:\s*(.+)", response_text),
        "choice3": parse_response(r"선택지3:\s*(.+)", response_text),
        "choice4": parse_response(r"선택지4:\s*(.+)", response_text),
        "answer": parse_response(r"정답:\s*(\d+)", response_text, is_int=True),
    }            


# 케미 퀴즈 문제 추가 생성
class PlayChemQuizAddView(APIView):
    @swagger_auto_schema(
        operation_id="케미 퀴즈 문제 추가생성",
        operation_description="케미 퀴즈에 새로운 문제를 추가 생성합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "Created",
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
            quiz = ChemQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if quiz.result.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # 새로운 문제를 추가
        question_index = quiz.question_num  # 현재 문제 수를 인덱스로 사용

        quiz_data = generate_OneChemQuiz(result, client)

        ChemQuizQuestion.objects.create(
            quiz=quiz,
            question_index=question_index,
            question=quiz_data["question"],
            choice1=quiz_data["choice1"],
            choice2=quiz_data["choice2"],
            choice3=quiz_data["choice3"],
            choice4=quiz_data["choice4"],
            answer=quiz_data["answer"],
            correct_num=0,
            count1=0,
            count2=0,
            count3=0,
            count4=0,
        )

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = ChemQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 
        
        quiz.question_num += 1  # 문제 수 증가
        quiz.solved_num = 0  # 문제 추가 후 퀴즈 통계 초기화
        quiz.avg_score = 0
        quiz.save()

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        ChemQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_200_OK)


###################################################################


def generate_SomeQuiz(result: ResultPlaySome, client: genai.Client) -> dict:
    
    # 퀴즈 생성에 참고할 자료들 가져오기
    chat = result.chat
    if not chat.file:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    try:
        spec = ResultPlaySomeSpec.objects.get(result=result)
    except:
        return {"detail": "해당 분석 결과의 스펙이 존재하지 않습니다."}
    
    # 채팅 파일 열기
    file_path = chat.file.path
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chat_content = f.read()  # 파일 전체 내용 읽기
    except FileNotFoundError:
        return {"detail": "채팅 파일이 존재하지 않습니다."}

    prompt = f"""
        당신은 카카오톡 대화 파일을 분석하여 두 사람 사이의 썸 기류를 평가하는 전문가입니다.
        주어진 채팅 대화 내용과 썸 분석 결과를 바탕으로 두 사람에 대한 썸 퀴즈 10개를 생성해주세요.
        썸 퀴즈는 4지선다형으로, 정답은 1개입니다.

        주어진 채팅 대화 내용: 
        {chat_content}

        썸 분석 결과: 
        두 사람 {spec.name_A}와 {spec.name_B} 사이의 대화입니다. 
        대화 참여자는 {result.age} 정도의 나이를 가지고 있고, {result.relationship}의 관계를 가지고 있습니다.

        썸 분석 자세한 결과: 
        해당 대화의 썸 지수는 {spec.score_main}입니다.
        대화를 분석한 결과, {spec.comment_main}의 조언이 제안되었습니다.
        {spec.name_A}에서 {spec.name_B}에게 향하는 호감점수는 {spec.score_A}이며, {spec.trait_A}의 특징을 가집니다.
        {spec.name_B}에서 {spec.name_A}에게 향하는 호감점수는 {spec.score_B}이며, {spec.trait_B}의 특징을 가집니다.
        
        요약하자면, {spec.summary}

        말투와 감정을 분석한 결과, 
        어색한 정도는 {spec.tone}점이고, {spec.tone_desc}의 특징을 보입니다. 예를 들자면, {spec.tone_ex}가 있습니다.
        감정표현의 정도는 {spec.emo}점이고, {spec.emo_desc}의 특징을 보입니다. 예를 들자면, {spec.emo_ex}가 있습니다.
        서로에 대한 호칭이 부드러운 정도는 {spec.addr}점이고, {spec.addr_desc}의 특징을 보입니다. 예를 들자면, {spec.addr_ex}가 있습니다.

        대화 패턴을 분석한 결과, {spec.pattern_analysis}의 특징을 보입니다.
        더 자세히 설명하자면,
        평균 답장 시간은 {spec.name_A}와 {spec.name_B}가 각각 {spec.reply_A}초, {spec.reply_B}초입니다.
        평균 답장 시간에 대한 간략한 설명은 각각 {spec.reply_A_desc}와 {spec.reply_B_desc}입니다.
        약속제안횟수는 {spec.name_A}가 {spec.rec_A}회, {spec.name_B}가 {spec.rec_B}회입니다.
        약속제안횟수에 대한 간략한 설명은 각각 {spec.rec_A_desc}와 {spec.rec_B_desc}입니다.
        약속제안횟수에 대한 예시는 각각 {spec.rec_A_ex}와 {spec.rec_B_ex}입니다.
        주제시작비율은 {spec.name_A}가 {spec.atti_A}%, {spec.name_B}가 {spec.atti_B}%입니다.
        주제시작비율에 대한 간략한 설명은 각각 {spec.atti_A_desc}와 {spec.atti_B_desc}입니다.
        주제시작비율에 대한 예시는 각각 {spec.atti_A_ex}와 {spec.atti_B_ex}입니다.
        평균 메시지 길이는 {spec.name_A}가 {spec.len_A}자, {spec.name_B}가 {spec.len_B}자입니다.
        평균 메시지 길이에 대한 간략한 설명은 각각 {spec.len_A_desc}와 {spec.len_B_desc}입니다.
        평균 메시지 길이에 대한 예시는 각각 {spec.len_A_ex}와 {spec.len_B_ex}입니다.
        
        종합적인 연애상담결과는 다음과 같습니다:
        {spec.chatto_counsel}
        {spec.chatto_counsel_tips}

        당신은 지금까지 제공된 위의 정보를 바탕으로 다음과 같은 썸 퀴즈를 10개 생성해야 합니다:

        당신의 응답은 다음과 반드시 같은 형식을 따라야 합니다:

        문제1: [문제 내용]
        선택지1-1: [선택지 1 내용]
        선택지1-2: [선택지 2 내용]
        선택지1-3: [선택지 3 내용]
        선택지1-4: [선택지 4 내용]
        정답1: [정답 선택지 번호 (1, 2, 3, 4)]
        문제2: [문제 내용]
        선택지2-1: [선택지 1 내용]
        선택지2-2: [선택지 2 내용]
        선택지2-3: [선택지 3 내용]
        선택지2-4: [선택지 4 내용]
        정답2: [정답 선택지 번호 (1, 2, 3, 4)]
        문제3: [문제 내용]
        선택지3-1: [선택지 1 내용]  
        선택지3-2: [선택지 2 내용]
        선택지3-3: [선택지 3 내용]
        선택지3-4: [선택지 4 내용]
        정답3: [정답 선택지 번호 (1, 2, 3, 4)]
        문제4: [문제 내용]
        선택지4-1: [선택지 1 내용]
        선택지4-2: [선택지 2 내용]
        선택지4-3: [선택지 3 내용]
        선택지4-4: [선택지 4 내용]
        정답4: [정답 선택지 번호 (1, 2, 3, 4)]
        문제5: [문제 내용]
        선택지5-1: [선택지 1 내용]
        선택지5-2: [선택지 2 내용]
        선택지5-3: [선택지 3 내용]
        선택지5-4: [선택지 4 내용]
        정답5: [정답 선택지 번호 (1, 2, 3, 4)]
        문제6: [문제 내용]
        선택지6-1: [선택지 1 내용]
        선택지6-2: [선택지 2 내용]
        선택지6-3: [선택지 3 내용]
        선택지6-4: [선택지 4 내용]
        정답6: [정답 선택지 번호 (1, 2, 3, 4)]
        문제7: [문제 내용]
        선택지7-1: [선택지 1 내용]
        선택지7-2: [선택지 2 내용]
        선택지7-3: [선택지 3 내용]
        선택지7-4: [선택지 4 내용]
        정답7: [정답 선택지 번호 (1, 2, 3, 4)]
        문제8: [문제 내용]
        선택지8-1: [선택지 1 내용]
        선택지8-2: [선택지 2 내용]
        선택지8-3: [선택지 3 내용]
        선택지8-4: [선택지 4 내용]
        정답8: [정답 선택지 번호 (1, 2, 3, 4)]
        문제9: [문제 내용]
        선택지9-1: [선택지 1 내용]
        선택지9-2: [선택지 2 내용]
        선택지9-3: [선택지 3 내용]
        선택지9-4: [선택지 4 내용]
        정답9: [정답 선택지 번호 (1, 2, 3, 4)]
        문제10: [문제 내용]
        선택지10-1: [선택지 1 내용]
        선택지10-2: [선택지 2 내용]
        선택지10-3: [선택지 3 내용]
        선택지10-4: [선택지 4 내용]
        정답10: [정답 선택지 번호 (1, 2, 3, 4)]
        """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    response_text = response.text
    
    print(f"Gemini로 생성된 썸 퀴즈 응답: {response_text}")

    return {
        "question1": parse_response(r"문제1:\s*(.+)", response_text),
        "choice1-1": parse_response(r"선택지1-1:\s*(.+)", response_text),
        "choice1-2": parse_response(r"선택지1-2:\s*(.+)", response_text),
        "choice1-3": parse_response(r"선택지1-3:\s*(.+)", response_text),
        "choice1-4": parse_response(r"선택지1-4:\s*(.+)", response_text),
        "answer1": parse_response(r"정답1:\s*(\d+)", response_text, is_int=True),
        "question2": parse_response(r"문제2:\s*(.+)", response_text),
        "choice2-1": parse_response(r"선택지2-1:\s*(.+)", response_text),
        "choice2-2": parse_response(r"선택지2-2:\s*(.+)", response_text),
        "choice2-3": parse_response(r"선택지2-3:\s*(.+)", response_text),
        "choice2-4": parse_response(r"선택지2-4:\s*(.+)", response_text),
        "answer2": parse_response(r"정답2:\s*(\d+)", response_text, is_int=True),
        "question3": parse_response(r"문제3:\s*(.+)", response_text),
        "choice3-1": parse_response(r"선택지3-1:\s*(.+)", response_text),
        "choice3-2": parse_response(r"선택지3-2:\s*(.+)", response_text),
        "choice3-3": parse_response(r"선택지3-3:\s*(.+)", response_text),
        "choice3-4": parse_response(r"선택지3-4:\s*(.+)", response_text),
        "answer3": parse_response(r"정답3:\s*(\d+)", response_text, is_int=True),
        "question4": parse_response(r"문제4:\s*(.+)", response_text),
        "choice4-1": parse_response(r"선택지4-1:\s*(.+)", response_text),
        "choice4-2": parse_response(r"선택지4-2:\s*(.+)", response_text),
        "choice4-3": parse_response(r"선택지4-3:\s*(.+)", response_text),
        "choice4-4": parse_response(r"선택지4-4:\s*(.+)", response_text),
        "answer4": parse_response(r"정답4:\s*(\d+)", response_text, is_int=True),
        "question5": parse_response(r"문제5:\s*(.+)", response_text),
        "choice5-1": parse_response(r"선택지5-1:\s*(.+)", response_text),
        "choice5-2": parse_response(r"선택지5-2:\s*(.+)", response_text),
        "choice5-3": parse_response(r"선택지5-3:\s*(.+)", response_text),
        "choice5-4": parse_response(r"선택지5-4:\s*(.+)", response_text),
        "answer5": parse_response(r"정답5:\s*(\d+)", response_text, is_int=True),
        "question6": parse_response(r"문제6:\s*(.+)", response_text),
        "choice6-1": parse_response(r"선택지6-1:\s*(.+)", response_text),
        "choice6-2": parse_response(r"선택지6-2:\s*(.+)", response_text),
        "choice6-3": parse_response(r"선택지6-3:\s*(.+)", response_text),
        "choice6-4": parse_response(r"선택지6-4:\s*(.+)", response_text),
        "answer6": parse_response(r"정답6:\s*(\d+)", response_text, is_int=True),
        "question7": parse_response(r"문제7:\s*(.+)", response_text),
        "choice7-1": parse_response(r"선택지7-1:\s*(.+)", response_text),
        "choice7-2": parse_response(r"선택지7-2:\s*(.+)", response_text),
        "choice7-3": parse_response(r"선택지7-3:\s*(.+)", response_text),
        "choice7-4": parse_response(r"선택지7-4:\s*(.+)", response_text),
        "answer7": parse_response(r"정답7:\s*(\d+)", response_text, is_int=True),
        "question8": parse_response(r"문제8:\s*(.+)", response_text),
        "choice8-1": parse_response(r"선택지8-1:\s*(.+)", response_text),
        "choice8-2": parse_response(r"선택지8-2:\s*(.+)", response_text),
        "choice8-3": parse_response(r"선택지8-3:\s*(.+)", response_text),
        "choice8-4": parse_response(r"선택지8-4:\s*(.+)", response_text),
        "answer8": parse_response(r"정답8:\s*(\d+)", response_text, is_int=True),
        "question9": parse_response(r"문제9:\s*(.+)", response_text),
        "choice9-1": parse_response(r"선택지9-1:\s*(.+)", response_text),
        "choice9-2": parse_response(r"선택지9-2:\s*(.+)", response_text),
        "choice9-3": parse_response(r"선택지9-3:\s*(.+)", response_text),
        "choice9-4": parse_response(r"선택지9-4:\s*(.+)", response_text),
        "answer9": parse_response(r"정답9:\s*(\d+)", response_text, is_int=True),
        "question10": parse_response(r"문제10:\s*(.+)", response_text),
        "choice10-1": parse_response(r"선택지10-1:\s*(.+)", response_text),
        "choice10-2": parse_response(r"선택지10-2:\s*(.+)", response_text),
        "choice10-3": parse_response(r"선택지10-3:\s*(.+)", response_text),
        "choice10-4": parse_response(r"선택지10-4:\s*(.+)", response_text),
        "answer10": parse_response(r"정답10:\s*(\d+)", response_text, is_int=True),
    }

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

        if SomeQuiz.objects.filter(result=result).exists():
            return Response({"detail": "이미 해당 분석 결과에 대한 퀴즈가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 썸 퀴즈 생성
        quiz_data = generate_SomeQuiz(result, client)

        if quiz_data == {"detail": "채팅 파일이 존재하지 않습니다."}:
            return Response({"detail": "채팅 파일이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)
        elif quiz_data == {"detail": "해당 분석 결과의 스펙이 존재하지 않습니다."}:
            return Response({"detail": "해당 분석 결과의 스펙이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        quiz = SomeQuiz.objects.create(
            result=result,
            question_num=10,
            solved_num=0,
            avg_score=0,
        )

        for i in range(quiz.question_num):
            SomeQuizQuestion.objects.create(
                quiz=quiz,
                question_index=i,
                question=quiz_data[f"question{i+1}"],
                choice1=quiz_data[f"choice{i+1}-1"],
                choice2=quiz_data[f"choice{i+1}-2"],
                choice3=quiz_data[f"choice{i+1}-3"],
                choice4=quiz_data[f"choice{i+1}-4"],
                answer=quiz_data[f"answer{i+1}"],
                correct_num=0,
                count1=0,
                count2=0,
                count3=0,
                count4=0,
            )

        result.is_quized = True
        result.save()
        
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

        result.is_quized = False
        result.save()

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


# 썸 퀴즈 문제 리스트 조회 (게스트용)
class PlaySomeQuizQuestionListView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 문제 리스트 조회 (게스트용)",
        operation_description="특정 썸 분석 결과에 대한 퀴즈의 문제 리스트를 조회합니다. (게스트용)",
        responses={
            200: SomeQuizQuestionSerializerPlay(many=True),
            404: "Not Found"
        },
    )
    def get(self, request, uuid):        
        try:
            share = UuidSome.objects.get(uuid=uuid)
            result_id = share.result_id
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
            201: SomeQuizPersonalSerializerPlay,
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
        
        QP = SomeQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        serializer = SomeQuizPersonalSerializerPlay(QP)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# 썸 퀴즈 풀이 시작 (게스트용)
class PlaySomeQuizStartGuestView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 풀이 시작 (게스트용)",
        operation_description="썸 퀴즈 풀이를 시작합니다. (게스트용)",
        request_body=SomeQuizStartRequestSerializerPlay,
        responses={
            201: SomeQuizPersonalSerializerPlay,
            400: "Bad Request",
            404: "Not Found"
        },
    )
    def post(self, request, uuid):
        serializer = SomeQuizStartRequestSerializerPlay(data=request.data)
        
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        name = serializer.validated_data["name"]
        
        try:
            share = UuidSome.objects.get(uuid=uuid)
            result_id = share.result.result_id
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if SomeQuizPersonal.objects.filter(quiz__result__result_id=result_id, name=name).exists():
            return Response({"detail": "이미 해당 이름의 퀴즈 풀이가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        QP = SomeQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        serializer = SomeQuizPersonalSerializerPlay(QP)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
    def get(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(QP_id=QP_id)
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
    def delete(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(QP_id=QP_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        quiz_personal.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# 썸 퀴즈 결과 (문제별 리스트) 한 사람 조회 (게스트용)
class PlaySomeQuizPersonalGuestView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 결과 (문제별 리스트) 한 사람 조회 (게스트용)",
        operation_description="썸 퀴즈 결과를 한 사람 기준으로 조회합니다. (게스트용)",
        responses={
            200: SomeQuizPersonalSerializerPlay,
            404: "Not Found"
        },
    )
    def get(self, request, uuid, QP_id):
        try:
            share = UuidSome.objects.get(uuid=uuid)
            result_id = share.result_id
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(QP_id=QP_id)
            quiz_personal_details = SomeQuizPersonalDetail.objects.filter(QP=quiz_personal)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = SomeQuizPersonalDetailSerializerPlay(quiz_personal_details, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


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
    def post(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        request_serializer = SomeQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(QP_id=QP_id)
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

        # 퀴즈 통계 업데이트
        quiz.solved_num += 1
        quiz.avg_score = (
            (quiz.avg_score * (quiz.solved_num - 1) + quiz_personal.score) / quiz.solved_num
        )
        quiz.save()

        # 각 문제별 정답 통계 업데이트
        for idx in range(quiz.question_num):
            try:
                question = SomeQuizQuestion.objects.get(quiz=quiz, question_index=idx)
                # 해당 문제에 대한 정답자 수 업데이트
                correct_count = SomeQuizPersonalDetail.objects.filter(
                    QP=quiz_personal, question=question, result=True
                ).count()
                if correct_count:
                    question.correct_num += 1
                    question.save()
            except SomeQuizQuestion.DoesNotExist:
                continue

        return Response(status=status.HTTP_200_OK)


# 썸 퀴즈 풀이 제출 (여러 문제 답변을 한 번에 제출) (게스트용)
class PlaySomeQuizSubmitGuestView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 제출 (게스트용)",
        operation_description="썸 퀴즈 풀이를 제출합니다. (여러 문제 답변을 한 번에 제출) (게스트용)",
        request_body=SomeQuizSubmitRequestSerializerPlay(many=True),
        responses={
            200: "OK",
            400: "Bad Request",
            404: "Not Found"
        },
    )
    def post(self, request, uuid, QP_id):
        request_serializer = SomeQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            share = UuidSome.objects.get(uuid=uuid)
            result_id = share.result_id
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            quiz_personal = SomeQuizPersonal.objects.get(QP_id=QP_id)
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
                result=result_correct
            )

            i += 1

        # 퀴즈 통계 업데이트
        quiz.solved_num += 1
        quiz.avg_score = (
            (quiz.avg_score * (quiz.solved_num - 1) + quiz_personal.score) / quiz.solved_num
        )
        quiz.save()

        # 각 문제별 정답 통계 업데이트
        for idx in range(quiz.question_num):
            try:
                question = SomeQuizQuestion.objects.get(quiz=quiz, question_index=idx)
                # 해당 문제에 대한 정답자 수 업데이트
                correct_count = SomeQuizPersonalDetail.objects.filter(
                    QP=quiz_personal, question=question, result=True
                ).count()
                if correct_count:
                    question.correct_num += 1
                    question.save()
            except SomeQuizQuestion.DoesNotExist:
                continue
        
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
            

# 썸 퀴즈 문제 수정, 삭제
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
    
    @swagger_auto_schema(
        operation_id="썸 퀴즈 문제 삭제",
        operation_description="썸 퀴즈의 특정 문제를 삭제합니다.",
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
    def delete(self, request, result_id, question_index):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlaySome.objects.get(result_id=result_id)
            quiz = SomeQuiz.objects.get(result=result)
            question = SomeQuizQuestion.objects.get(quiz=quiz, question_index=question_index)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if quiz.result.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        index = question.question_index

        # 해당 문제 삭제
        question.delete()

        # 해당 문제가 속하는 퀴즈의 statistics를 초기화
        quiz.question_num -= 1
        quiz.solved_num = 0
        quiz.avg_score = 0
        quiz.save()

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = SomeQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            if q.question_index > index:
                q.question_index -= 1
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        SomeQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    

def generate_OneSomeQuiz(result: ResultPlaySome, client: genai.Client) -> dict:
    
    # 퀴즈 생성에 참고할 자료들 가져오기
    chat = result.chat
    if not chat.file:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    try:
        spec = ResultPlaySomeSpec.objects.get(result=result)
    except:
        return {"detail": "해당 분석 결과의 스펙이 존재하지 않습니다."}
    
    # 채팅 파일 열기
    file_path = chat.file.path
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chat_content = f.read()  # 파일 전체 내용 읽기
    except FileNotFoundError:
        return {"detail": "채팅 파일이 존재하지 않습니다."}

    prompt = f"""
        당신은 카카오톡 대화 파일을 분석하여 두 사람 사이의 썸 기류를 평가하는 전문가입니다.
        주어진 채팅 대화 내용과 썸 분석 결과를 바탕으로 두 사람에 대한 썸 퀴즈 1개를 생성해주세요.
        썸 퀴즈는 4지선다형으로, 정답은 1개입니다.

        주어진 채팅 대화 내용: 
        {chat_content}

        썸 분석 결과: 
        두 사람 {spec.name_A}와 {spec.name_B} 사이의 대화입니다. 
        대화 참여자는 {result.age} 정도의 나이를 가지고 있고, {result.relationship}의 관계를 가지고 있습니다.

        썸 분석 자세한 결과: 
        해당 대화의 썸 지수는 {spec.score_main}입니다.
        대화를 분석한 결과, {spec.comment_main}의 조언이 제안되었습니다.
        {spec.name_A}에서 {spec.name_B}에게 향하는 호감점수는 {spec.score_A}이며, {spec.trait_A}의 특징을 가집니다.
        {spec.name_B}에서 {spec.name_A}에게 향하는 호감점수는 {spec.score_B}이며, {spec.trait_B}의 특징을 가집니다.
        
        요약하자면, {spec.summary}

        말투와 감정을 분석한 결과, 
        어색한 정도는 {spec.tone}점이고, {spec.tone_desc}의 특징을 보입니다. 예를 들자면, {spec.tone_ex}가 있습니다.
        감정표현의 정도는 {spec.emo}점이고, {spec.emo_desc}의 특징을 보입니다. 예를 들자면, {spec.emo_ex}가 있습니다.
        서로에 대한 호칭이 부드러운 정도는 {spec.addr}점이고, {spec.addr_desc}의 특징을 보입니다. 예를 들자면, {spec.addr_ex}가 있습니다.

        대화 패턴을 분석한 결과, {spec.pattern_analysis}의 특징을 보입니다.
        더 자세히 설명하자면,
        평균 답장 시간은 {spec.name_A}와 {spec.name_B}가 각각 {spec.reply_A}초, {spec.reply_B}초입니다.
        평균 답장 시간에 대한 간략한 설명은 각각 {spec.reply_A_desc}와 {spec.reply_B_desc}입니다.
        약속제안횟수는 {spec.name_A}가 {spec.rec_A}회, {spec.name_B}가 {spec.rec_B}회입니다.
        약속제안횟수에 대한 간략한 설명은 각각 {spec.rec_A_desc}와 {spec.rec_B_desc}입니다.
        약속제안횟수에 대한 예시는 각각 {spec.rec_A_ex}와 {spec.rec_B_ex}입니다.
        주제시작비율은 {spec.name_A}가 {spec.atti_A}%, {spec.name_B}가 {spec.atti_B}%입니다.
        주제시작비율에 대한 간략한 설명은 각각 {spec.atti_A_desc}와 {spec.atti_B_desc}입니다.
        주제시작비율에 대한 예시는 각각 {spec.atti_A_ex}와 {spec.atti_B_ex}입니다.
        평균 메시지 길이는 {spec.name_A}가 {spec.len_A}자, {spec.name_B}가 {spec.len_B}자입니다.
        평균 메시지 길이에 대한 간략한 설명은 각각 {spec.len_A_desc}와 {spec.len_B_desc}입니다.
        평균 메시지 길이에 대한 예시는 각각 {spec.len_A_ex}와 {spec.len_B_ex}입니다.
        
        종합적인 연애상담결과는 다음과 같습니다:
        {spec.chatto_counsel}
        {spec.chatto_counsel_tips}

        당신은 지금까지 제공된 위의 정보를 바탕으로 다음과 같은 썸 퀴즈를 1개 생성해야 합니다:

        당신의 응답은 다음과 반드시 같은 형식을 따라야 합니다:

        문제: [문제 내용]
        선택지1: [선택지 1 내용]
        선택지2: [선택지 2 내용]
        선택지3: [선택지 3 내용]
        선택지4: [선택지 4 내용]
        정답: [정답 선택지 번호 (1, 2, 3, 4)]
        """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    response_text = response.text
    
    print(f"Gemini로 생성된 썸 퀴즈 응답: {response_text}")

    return {
        "question": parse_response(r"문제:\s*(.+)", response_text),
        "choice1": parse_response(r"선택지1:\s*(.+)", response_text),
        "choice2": parse_response(r"선택지2:\s*(.+)", response_text),
        "choice3": parse_response(r"선택지3:\s*(.+)", response_text),
        "choice4": parse_response(r"선택지4:\s*(.+)", response_text),
        "answer": parse_response(r"정답:\s*(\d+)", response_text, is_int=True),
    }


# 썸 퀴즈 문제 추가 생성
class PlaySomeQuizAddView(APIView):
    @swagger_auto_schema(
        operation_id="썸 퀴즈 문제 추가생성",
        operation_description="썸 퀴즈에 새로운 문제를 추가 생성합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="access token",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "Created",
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
            quiz = SomeQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if quiz.result.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # 새로운 문제를 추가
        question_index = quiz.question_num  # 현재 문제 수를 인덱스로 사용

        quiz_data = generate_OneSomeQuiz(result, client)

        SomeQuizQuestion.objects.create(
            quiz=quiz,
            question_index=question_index,
            question=quiz_data["question"],
            choice1=quiz_data["choice1"],
            choice2=quiz_data["choice2"],
            choice3=quiz_data["choice3"],
            choice4=quiz_data["choice4"],
            answer=quiz_data["answer"],
            correct_num=0,
            count1=0,
            count2=0,
            count3=0,
            count4=0,
        )

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = SomeQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 

        quiz.question_num += 1  
        quiz.solved_num = 0
        quiz.avg_score = 0
        quiz.save()

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        SomeQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_200_OK)


###################################################################


def generate_MBTIQuiz(result: ResultPlayMBTI, client: genai.Client) -> dict:
    
    # 퀴즈 생성에 참고할 자료들 가져오기
    chat = result.chat
    if not chat.file:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    try:
        spec = ResultPlayMBTISpec.objects.get(result=result)
        spec_personals = ResultPlayMBTISpecPersonal.objects.filter(spec=spec)
    except:
        return {"detail": "MBTI 분석 결과가 존재하지 않습니다."}

    # 채팅 파일 열기
    file_path = chat.file.path
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chat_content = f.read()  # 파일 전체 내용 읽기
    except FileNotFoundError:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    
    total = spec.total_E + spec.total_I
    names = ["" for _ in range(total)]
    MBTIs = ["" for _ in range(total)]

    for i in range(total):
        names[i] = spec_personals[i].name
        MBTIs[i] = spec_personals[i].MBTI

    personal_results = ["" for _ in range(total)]

    for i in range(total):
        personal_results[i] = f"""
            {names[i]}의 MBTI 분석 결과:
            {names[i]}의 MBTI는 {MBTIs[i]}입니다.
            {names[i]}의 MBTI에 대한 요약은 다음과 같습니다: {spec_personals[i].summary}
            {names[i]}의 MBTI에 대한 자세한 설명은 다음과 같습니다: {spec_personals[i].desc}
            {names[i]}의 단톡 내 포지션은 다음과 같습니다: {spec_personals[i].position}
            {names[i]}의 단톡 내 성향은 다음과 같습니다: {spec_personals[i].personality}
            {names[i]}의 대화 특징은 다음과 같습니다: {spec_personals[i].style}
            {names[i]}의 MBTI 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].moment_ex}, {spec_personals[i].moment_desc}
            {names[i]}의 IE 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentIE_ex}, {spec_personals[i].momentIE_desc}
            {names[i]}의 NS 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentSN_ex}, {spec_personals[i].momentSN_desc}
            {names[i]}의 TF 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentFT_ex}, {spec_personals[i].momentFT_desc}
            {names[i]}의 JP 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentJP_ex}, {spec_personals[i].momentJP_desc}
            """
        
    prompt = f"""
        당신은 카카오톡 대화 파일을 분석하여 대화 참여자들의 MBTI를 분석하는 전문가입니다.
        주어진 채팅 대화 내용과 MBTI 분석 결과를 바탕으로 두 사람에 대한 MBTI 퀴즈 10개를 생성해주세요.
        MBTI 퀴즈는 4지선다형으로, 정답은 1개입니다.

        주어진 채팅 대화 내용: 
        {chat_content}

        MBTI 분석 결과: 
        이 대화의 참여자는 {[name for name in names]}입니다.
        이들 각각의 MBTI는 순서대로 {[MBTI for MBTI in MBTIs]}입니다.

        MBTI 분석 자세한 결과:
        이 대화 참여자들 중 {spec.total_E}명은 E(외향) 성향을 가지고 있고, {spec.total_I}명은 I(내향) 성향을 가지고 있습니다.
        이 대화 참여자들 중 {spec.total_N}명은 N(직관) 성향을 가지고 있고, {spec.total_S}명은 S(감각) 성향을 가지고 있습니다.
        이 대화 참여자들 중 {spec.total_T}명은 T(사고) 성향을 가지고 있고, {spec.total_F}명은 F(감정) 성향을 가지고 있습니다.
        이 대화 참여자들 중 {spec.total_J}명은 J(판단) 성향을 가지고 있고, {spec.total_P}명은 P(인식) 성향을 가지고 있습니다.

        개인별 분석 결과:{[r for r in personal_results]}
        
        당신은 지금까지 제공된 위의 정보를 바탕으로 다음과 같은 썸 퀴즈를 10개 생성해야 합니다:

        당신의 응답은 다음과 반드시 같은 형식을 따라야 합니다:

        문제1: [문제 내용]
        선택지1-1: [선택지 1 내용]
        선택지1-2: [선택지 2 내용]
        선택지1-3: [선택지 3 내용]
        선택지1-4: [선택지 4 내용]
        정답1: [정답 선택지 번호 (1, 2, 3, 4)]
        문제2: [문제 내용]
        선택지2-1: [선택지 1 내용]
        선택지2-2: [선택지 2 내용]
        선택지2-3: [선택지 3 내용]
        선택지2-4: [선택지 4 내용]
        정답2: [정답 선택지 번호 (1, 2, 3, 4)]
        문제3: [문제 내용]
        선택지3-1: [선택지 1 내용]  
        선택지3-2: [선택지 2 내용]
        선택지3-3: [선택지 3 내용]
        선택지3-4: [선택지 4 내용]
        정답3: [정답 선택지 번호 (1, 2, 3, 4)]
        문제4: [문제 내용]
        선택지4-1: [선택지 1 내용]
        선택지4-2: [선택지 2 내용]
        선택지4-3: [선택지 3 내용]
        선택지4-4: [선택지 4 내용]
        정답4: [정답 선택지 번호 (1, 2, 3, 4)]
        문제5: [문제 내용]
        선택지5-1: [선택지 1 내용]
        선택지5-2: [선택지 2 내용]
        선택지5-3: [선택지 3 내용]
        선택지5-4: [선택지 4 내용]
        정답5: [정답 선택지 번호 (1, 2, 3, 4)]
        문제6: [문제 내용]
        선택지6-1: [선택지 1 내용]
        선택지6-2: [선택지 2 내용]
        선택지6-3: [선택지 3 내용]
        선택지6-4: [선택지 4 내용]
        정답6: [정답 선택지 번호 (1, 2, 3, 4)]
        문제7: [문제 내용]
        선택지7-1: [선택지 1 내용]
        선택지7-2: [선택지 2 내용]
        선택지7-3: [선택지 3 내용]
        선택지7-4: [선택지 4 내용]
        정답7: [정답 선택지 번호 (1, 2, 3, 4)]
        문제8: [문제 내용]
        선택지8-1: [선택지 1 내용]
        선택지8-2: [선택지 2 내용]
        선택지8-3: [선택지 3 내용]
        선택지8-4: [선택지 4 내용]
        정답8: [정답 선택지 번호 (1, 2, 3, 4)]
        문제9: [문제 내용]
        선택지9-1: [선택지 1 내용]
        선택지9-2: [선택지 2 내용]
        선택지9-3: [선택지 3 내용]
        선택지9-4: [선택지 4 내용]
        정답9: [정답 선택지 번호 (1, 2, 3, 4)]
        문제10: [문제 내용]
        선택지10-1: [선택지 1 내용]
        선택지10-2: [선택지 2 내용]
        선택지10-3: [선택지 3 내용]
        선택지10-4: [선택지 4 내용]
        정답10: [정답 선택지 번호 (1, 2, 3, 4)]
        """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    response_text = response.text
    
    print(f"Gemini로 생성된 MBTI 퀴즈 응답: {response_text}")

    return {
        "question1": parse_response(r"문제1:\s*(.+)", response_text),
        "choice1-1": parse_response(r"선택지1-1:\s*(.+)", response_text),
        "choice1-2": parse_response(r"선택지1-2:\s*(.+)", response_text),
        "choice1-3": parse_response(r"선택지1-3:\s*(.+)", response_text),
        "choice1-4": parse_response(r"선택지1-4:\s*(.+)", response_text),
        "answer1": parse_response(r"정답1:\s*(\d+)", response_text, is_int=True),
        "question2": parse_response(r"문제2:\s*(.+)", response_text),
        "choice2-1": parse_response(r"선택지2-1:\s*(.+)", response_text),
        "choice2-2": parse_response(r"선택지2-2:\s*(.+)", response_text),
        "choice2-3": parse_response(r"선택지2-3:\s*(.+)", response_text),
        "choice2-4": parse_response(r"선택지2-4:\s*(.+)", response_text),
        "answer2": parse_response(r"정답2:\s*(\d+)", response_text, is_int=True),
        "question3": parse_response(r"문제3:\s*(.+)", response_text),
        "choice3-1": parse_response(r"선택지3-1:\s*(.+)", response_text),
        "choice3-2": parse_response(r"선택지3-2:\s*(.+)", response_text),
        "choice3-3": parse_response(r"선택지3-3:\s*(.+)", response_text),
        "choice3-4": parse_response(r"선택지3-4:\s*(.+)", response_text),
        "answer3": parse_response(r"정답3:\s*(\d+)", response_text, is_int=True),
        "question4": parse_response(r"문제4:\s*(.+)", response_text),
        "choice4-1": parse_response(r"선택지4-1:\s*(.+)", response_text),
        "choice4-2": parse_response(r"선택지4-2:\s*(.+)", response_text),
        "choice4-3": parse_response(r"선택지4-3:\s*(.+)", response_text),
        "choice4-4": parse_response(r"선택지4-4:\s*(.+)", response_text),
        "answer4": parse_response(r"정답4:\s*(\d+)", response_text, is_int=True),
        "question5": parse_response(r"문제5:\s*(.+)", response_text),
        "choice5-1": parse_response(r"선택지5-1:\s*(.+)", response_text),
        "choice5-2": parse_response(r"선택지5-2:\s*(.+)", response_text),
        "choice5-3": parse_response(r"선택지5-3:\s*(.+)", response_text),
        "choice5-4": parse_response(r"선택지5-4:\s*(.+)", response_text),
        "answer5": parse_response(r"정답5:\s*(\d+)", response_text, is_int=True),
        "question6": parse_response(r"문제6:\s*(.+)", response_text),
        "choice6-1": parse_response(r"선택지6-1:\s*(.+)", response_text),
        "choice6-2": parse_response(r"선택지6-2:\s*(.+)", response_text),
        "choice6-3": parse_response(r"선택지6-3:\s*(.+)", response_text),
        "choice6-4": parse_response(r"선택지6-4:\s*(.+)", response_text),
        "answer6": parse_response(r"정답6:\s*(\d+)", response_text, is_int=True),
        "question7": parse_response(r"문제7:\s*(.+)", response_text),
        "choice7-1": parse_response(r"선택지7-1:\s*(.+)", response_text),
        "choice7-2": parse_response(r"선택지7-2:\s*(.+)", response_text),
        "choice7-3": parse_response(r"선택지7-3:\s*(.+)", response_text),
        "choice7-4": parse_response(r"선택지7-4:\s*(.+)", response_text),
        "answer7": parse_response(r"정답7:\s*(\d+)", response_text, is_int=True),
        "question8": parse_response(r"문제8:\s*(.+)", response_text),
        "choice8-1": parse_response(r"선택지8-1:\s*(.+)", response_text),
        "choice8-2": parse_response(r"선택지8-2:\s*(.+)", response_text),
        "choice8-3": parse_response(r"선택지8-3:\s*(.+)", response_text),
        "choice8-4": parse_response(r"선택지8-4:\s*(.+)", response_text),
        "answer8": parse_response(r"정답8:\s*(\d+)", response_text, is_int=True),
        "question9": parse_response(r"문제9:\s*(.+)", response_text),
        "choice9-1": parse_response(r"선택지9-1:\s*(.+)", response_text),
        "choice9-2": parse_response(r"선택지9-2:\s*(.+)", response_text),
        "choice9-3": parse_response(r"선택지9-3:\s*(.+)", response_text),
        "choice9-4": parse_response(r"선택지9-4:\s*(.+)", response_text),
        "answer9": parse_response(r"정답9:\s*(\d+)", response_text, is_int=True),
        "question10": parse_response(r"문제10:\s*(.+)", response_text),
        "choice10-1": parse_response(r"선택지10-1:\s*(.+)", response_text),
        "choice10-2": parse_response(r"선택지10-2:\s*(.+)", response_text),
        "choice10-3": parse_response(r"선택지10-3:\s*(.+)", response_text),
        "choice10-4": parse_response(r"선택지10-4:\s*(.+)", response_text),
        "answer10": parse_response(r"정답10:\s*(\d+)", response_text, is_int=True),
    }

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

        if MBTIQuiz.objects.filter(result=result).exists():
            return Response({"detail": "이미 해당 분석 결과에 대한 퀴즈가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # MBTI 퀴즈 생성
        quiz_data = generate_MBTIQuiz(result, client)

        if quiz_data == {"detail": "채팅 파일이 존재하지 않습니다."}:
            return Response({"detail": "채팅 파일이 존재하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)
        elif quiz_data == {"detail": "MBTI 분석 결과가 존재하지 않습니다."}:
            return Response({"detail": "MBTI 분석 결과가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        quiz = MBTIQuiz.objects.create(
            result=result,
            question_num=10,
            solved_num=0,
            avg_score=0,
        )

        for i in range(quiz.question_num):
            MBTIQuizQuestion.objects.create(
                quiz=quiz,
                question_index=i,
                question=quiz_data[f"question{i+1}"],
                choice1=quiz_data[f"choice{i+1}-1"],
                choice2=quiz_data[f"choice{i+1}-2"],
                choice3=quiz_data[f"choice{i+1}-3"],
                choice4=quiz_data[f"choice{i+1}-4"],
                answer=quiz_data[f"answer{i+1}"],
                correct_num=0,
                count1=0,
                count2=0,
                count3=0,
                count4=0,
            )

        result.is_quized = True
        result.save()
        
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

        result.is_quized = False
        result.save()

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


# MBTI 퀴즈 문제 리스트 조회 (게스트용)
class PlayMBTIQuizQuestionListView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 문제 리스트 조회 (게스트용)",
        operation_description="특정 MBTI 분석 결과에 대한 퀴즈의 문제 리스트를 조회합니다. (게스트용)",
        responses={
            200: MBTIQuizQuestionSerializerPlay(many=True),
            404: "Not Found"
        },
    )
    def get(self, request, uuid):  
        try:
            share = UuidMBTI.objects.get(uuid=uuid)
            result_id = share.result_id
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
            201: MBTIQuizPersonalSerializerPlay,
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
        
        QP = MBTIQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        serializer = MBTIQuizPersonalSerializerPlay(QP)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# MBTI 퀴즈 풀이 시작 (게스트용)
class PlayMBTIQuizStartGuestView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 풀이 시작 (게스트용)",
        operation_description="MBTI 퀴즈 풀이를 시작합니다. (게스트용)",
        request_body=MBTIQuizStartRequestSerializerPlay,
        responses={
            201: MBTIQuizPersonalSerializerPlay,
            400: "Bad Request",
            404: "Not Found"
        },
    )
    def post(self, request, uuid):
        serializer = MBTIQuizStartRequestSerializerPlay(data=request.data)
        
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        name = serializer.validated_data["name"]

        try:
            share = UuidMBTI.objects.get(uuid=uuid)
            result_id = share.result.result_id
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if MBTIQuizPersonal.objects.filter(quiz__result__result_id=result_id, name=name).exists():
            return Response({"detail": "이미 해당 이름의 퀴즈 풀이가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        QP = MBTIQuizPersonal.objects.create(
            quiz=quiz,
            name=name,
            score=0,  # 초기 점수는 0
        )

        serializer = MBTIQuizPersonalSerializerPlay(QP)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
            401: "Unauthorized",
            404: "Not Found"
        },
    )
    def get(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(QP_id=QP_id)
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
    def delete(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(QP_id=QP_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        quiz_personal.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# MBTI 퀴즈 결과 (문제별 리스트) 한 사람 조회 (게스트용)
class PlayMBTIQuizPersonalGuestView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 결과 (문제별 리스트) 한 사람 조회 (게스트용)",
        operation_description="MBTI 퀴즈 결과를 한 사람 기준으로 조회합니다. (게스트용)",
        responses={
            200: MBTIQuizPersonalSerializerPlay,
            404: "Not Found"
        },
    )
    def get(self, request, uuid, QP_id):
        try:
            share = UuidMBTI.objects.get(uuid=uuid)
            result_id = share.result.result_id
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(QP_id=QP_id)
            quiz_personal_details = MBTIQuizPersonalDetail.objects.filter(QP=quiz_personal)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 누구나 퀴즈를 조회할 수는 있다: 403 Forbidden 없음

        serializer = MBTIQuizPersonalDetailSerializerPlay(quiz_personal_details, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


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
    def post(self, request, result_id, QP_id):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        request_serializer = MBTIQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(QP_id=QP_id)
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

        # 퀴즈 통계 업데이트
        quiz.solved_num += 1
        quiz.avg_score = (
            (quiz.avg_score * (quiz.solved_num - 1) + quiz_personal.score) / quiz.solved_num
        )
        quiz.save()

        # 각 문제별 정답 통계 업데이트
        for idx in range(quiz.question_num):
            try:
                question = MBTIQuizQuestion.objects.get(quiz=quiz, question_index=idx)
                # 해당 문제에 대한 정답자 수 업데이트
                correct_count = MBTIQuizPersonalDetail.objects.filter(
                    QP=quiz_personal, question=question, result=True
                ).count()
                if correct_count:
                    question.correct_num += 1
                    question.save()
            except MBTIQuizQuestion.DoesNotExist:
                continue

        return Response(status=status.HTTP_200_OK)


# MBTI 퀴즈 풀이 제출 (여러 문제 답변을 한 번에 제출) (게스트용)
class PlayMBTIQuizSubmitGuestView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 제출 (게스트용)",
        operation_description="MBTI 퀴즈 풀이를 제출합니다. (여러 문제 답변을 한 번에 제출, 게스트용)",
        request_body=MBTIQuizSubmitRequestSerializerPlay(many=True),
        responses={
            200: "OK",
            400: "Bad Request",
            404: "Not Found"
        },
    )
    def post(self, request, uuid, QP_id):
        request_serializer = MBTIQuizSubmitRequestSerializerPlay(data=request.data, many=True)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            share = UuidMBTI.objects.get(uuid=uuid)
            result_id = share.result.result_id
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            quiz_personal = MBTIQuizPersonal.objects.get(QP_id=QP_id)
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
                result=result_correct
            )

            i += 1

        # 퀴즈 통계 업데이트
        quiz.solved_num += 1
        quiz.avg_score = (
            (quiz.avg_score * (quiz.solved_num - 1) + quiz_personal.score) / quiz.solved_num
        )
        quiz.save()

        # 각 문제별 정답 통계 업데이트
        for idx in range(quiz.question_num):
            try:
                question = MBTIQuizQuestion.objects.get(quiz=quiz, question_index=idx)
                # 해당 문제에 대한 정답자 수 업데이트
                correct_count = MBTIQuizPersonalDetail.objects.filter(
                    QP=quiz_personal, question=question, result=True
                ).count()
                if correct_count:
                    question.correct_num += 1
                    question.save()
            except MBTIQuizQuestion.DoesNotExist:
                continue
        
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
            

# MBTI 퀴즈 문제 수정, 삭제
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
    
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 문제 삭제",
        operation_description="MBTI 퀴즈의 특정 문제를 삭제합니다.",
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
    def delete(self, request, result_id, question_index):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
            question = MBTIQuizQuestion.objects.get(quiz=quiz, question_index=question_index)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if quiz.result.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        index = question.question_index

        # 해당 문제 삭제
        question.delete()

        # 퀴즈의 문제 수 감소
        quiz.question_num -= 1

        # 해당 문제가 속하는 퀴즈의 statistics를 초기화
        quiz.solved_num = 0
        quiz.avg_score = 0
        quiz.save()

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = MBTIQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            if q.question_index > index:
                q.question_index -= 1
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        MBTIQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    

def generate_OneMBTIQuiz(result: ResultPlayMBTI, client: genai.Client) -> dict:
    
    # 퀴즈 생성에 참고할 자료들 가져오기
    chat = result.chat
    if not chat.file:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    try:
        spec = ResultPlayMBTISpec.objects.get(result=result)
        spec_personals = ResultPlayMBTISpecPersonal.objects.filter(spec=spec)
    except:
        return {"detail": "MBTI 분석 결과가 존재하지 않습니다."}

    # 채팅 파일 열기
    file_path = chat.file.path
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chat_content = f.read()  # 파일 전체 내용 읽기
    except FileNotFoundError:
        return {"detail": "채팅 파일이 존재하지 않습니다."}
    
    total = spec.total_E + spec.total_I
    names = ["" for _ in range(total)]
    MBTIs = ["" for _ in range(total)]

    for i in range(total):
        names[i] = spec_personals[i].name
        MBTIs[i] = spec_personals[i].MBTI

    personal_results = ["" for _ in range(total)]

    for i in range(total):
        personal_results[i] = f"""
            {names[i]}의 MBTI 분석 결과:
            {names[i]}의 MBTI는 {MBTIs[i]}입니다.
            {names[i]}의 MBTI에 대한 요약은 다음과 같습니다: {spec_personals[i].summary}
            {names[i]}의 MBTI에 대한 자세한 설명은 다음과 같습니다: {spec_personals[i].desc}
            {names[i]}의 단톡 내 포지션은 다음과 같습니다: {spec_personals[i].position}
            {names[i]}의 단톡 내 성향은 다음과 같습니다: {spec_personals[i].personality}
            {names[i]}의 대화 특징은 다음과 같습니다: {spec_personals[i].style}
            {names[i]}의 MBTI 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].moment_ex}, {spec_personals[i].moment_desc}
            {names[i]}의 IE 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentIE_ex}, {spec_personals[i].momentIE_desc}
            {names[i]}의 NS 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentSN_ex}, {spec_personals[i].momentSN_desc}
            {names[i]}의 TF 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentFT_ex}, {spec_personals[i].momentFT_desc}
            {names[i]}의 JP 성향 모먼트의 예시와 그에 대한 설명은 다음과 같습니다: {spec_personals[i].momentJP_ex}, {spec_personals[i].momentJP_desc}
            """
        
    prompt = f"""
        당신은 카카오톡 대화 파일을 분석하여 대화 참여자들의 MBTI를 분석하는 전문가입니다.
        주어진 채팅 대화 내용과 MBTI 분석 결과를 바탕으로 두 사람에 대한 MBTI 퀴즈 1개를 생성해주세요.
        MBTI 퀴즈는 4지선다형으로, 정답은 1개입니다.

        주어진 채팅 대화 내용: 
        {chat_content}

        MBTI 분석 결과: 
        이 대화의 참여자는 {[name for name in names]}입니다.
        이들 각각의 MBTI는 순서대로 {[MBTI for MBTI in MBTIs]}입니다.

        MBTI 분석 자세한 결과:
        이 대화 참여자들 중 {spec.total_E}명은 E(외향) 성향을 가지고 있고, {spec.total_I}명은 I(내향) 성향을 가지고 있습니다.
        이 대화 참여자들 중 {spec.total_N}명은 N(직관) 성향을 가지고 있고, {spec.total_S}명은 S(감각) 성향을 가지고 있습니다.
        이 대화 참여자들 중 {spec.total_T}명은 T(사고) 성향을 가지고 있고, {spec.total_F}명은 F(감정) 성향을 가지고 있습니다.
        이 대화 참여자들 중 {spec.total_J}명은 J(판단) 성향을 가지고 있고, {spec.total_P}명은 P(인식) 성향을 가지고 있습니다.

        개인별 분석 결과:{[r for r in personal_results]}
        
        당신은 지금까지 제공된 위의 정보를 바탕으로 다음과 같은 썸 퀴즈를 1개 생성해야 합니다:

        당신의 응답은 다음과 반드시 같은 형식을 따라야 합니다:

        문제: [문제 내용]
        선택지1: [선택지 1 내용]
        선택지1: [선택지 2 내용]
        선택지3: [선택지 3 내용]
        선택지4: [선택지 4 내용]
        정답: [정답 선택지 번호 (1, 2, 3, 4)]
        """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    response_text = response.text
    
    print(f"Gemini로 생성된 MBTI 퀴즈 응답: {response_text}")

    return {
        "question": parse_response(r"문제:\s*(.+)", response_text),
        "choice1": parse_response(r"선택지1:\s*(.+)", response_text),
        "choice2": parse_response(r"선택지2:\s*(.+)", response_text),
        "choice3": parse_response(r"선택지3:\s*(.+)", response_text),
        "choice4": parse_response(r"선택지4:\s*(.+)", response_text),
        "answer": parse_response(r"정답:\s*(\d+)", response_text, is_int=True),
    }


# MBTI 퀴즈 문제 추가
class PlayMBTIQuizAddView(APIView):
    @swagger_auto_schema(
        operation_id="MBTI 퀴즈 문제 추가",
        operation_description="MBTI 퀴즈에 문제를 추가합니다.",
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

        try:
            result = ResultPlayMBTI.objects.get(result_id=result_id)
            quiz = MBTIQuiz.objects.get(result=result)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if quiz.result.user != author:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # 새로운 문제를 추가
        question_index = quiz.question_num # 현재 문제 수를 인덱스로 사용

        quiz_data = generate_OneMBTIQuiz(result, client)

        MBTIQuizQuestion.objects.create(
            quiz=quiz,
            question_index=question_index,
            question=quiz_data["question"],
            choice1=quiz_data["choice1"],
            choice2=quiz_data["choice2"],
            choice3=quiz_data["choice3"],
            choice4=quiz_data["choice4"],
            answer=quiz_data["answer"],
            correct_num=0,
            count1=0,
            count2=0,
            count3=0,
            count4=0,
        )

        # 해당 문제가 속하는 퀴즈의 모든 문제의 statistics를 초기화
        questions = MBTIQuizQuestion.objects.filter(quiz=quiz)
        for q in questions:
            q.correct_num = 0
            q.count1 = 0
            q.count2 = 0
            q.count3 = 0
            q.count4 = 0
            q.save() 
        
        quiz.question_num += 1  # 문제 수 증가
        quiz.solved_num = 0  # 문제 추가 후 퀴즈 통계 초기화
        quiz.avg_score = 0
        quiz.save()

        # 이제 그동안 이 문제를 푼 기록은 지워야 함.
        MBTIQuizPersonal.objects.filter(quiz=quiz).delete()

        return Response(status=status.HTTP_200_OK)
    
