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

from .utils import (
    extract_chat_title,
    count_chat_participants_with_gemini,
    some_analysis_with_gemini,
    mbti_analysis_with_gemini,
    chem_analysis_with_gemini,
)

from datetime import datetime, date
    

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
        analysis_start = "처음부터" if serializer.validated_data["analysis_start"] == "string" else serializer.validated_data["analysis_start"]
        analysis_end = "끝까지" if serializer.validated_data["analysis_end"] == "string" else serializer.validated_data["analysis_end"]

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
            num_chat=chem_results.get("num_chat", 0)
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
            tone_else=chem_results.get("tone_else", 0),
            tone_ex=chem_results.get("tone_ex", ""),
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
        analysis_start = "처음부터" if serializer.validated_data["analysis_start"] == "string" else date(2025, 7, 25)
        analysis_end = "끝까지" if serializer.validated_data["analysis_end"] == "string" else date(2025, 8, 18)

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

        analysis_start = "처음부터" if serializer.validated_data["analysis_start"] == "string" else serializer.validated_data["analysis_start"]
        analysis_end = "끝까지" if serializer.validated_data["analysis_end"] == "string" else serializer.validated_data["analysis_end"]

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
        mbti_results = mbti_analysis_with_gemini(chat, client, analysis_option)

        # 2. ResultPlayMBTI 객체 생성
        result = ResultPlayMBTI.objects.create(
            type=3,
            title=chat.title,
            people_num=chat.people_num,
            is_saved=1,
            analysis_date_start=analysis_start,
            analysis_date_end=analysis_end,
            num_chat=mbti_results[-1].get("num_chat", 0),
            chat=chat,
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
        )
        totals = {
            'I': 0, 'E': 0, 'S': 0, 'N': 0, 'F': 0, 'T': 0, 'J': 0, 'P': 0
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

        # spec 객체에 전체 카운트 업데이트
        spec.total_I = totals['I']
        spec.total_E = totals['E']
        spec.total_S = totals['S']
        spec.total_N = totals['N']
        spec.total_F = totals['F']
        spec.total_T = totals['T']
        spec.total_J = totals['J']
        spec.total_P = totals['P']
        spec.save()

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
    