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
    SomeAllSerializerPlay,
    MBTIAllSerializerPlay,
    ChemAllSerializerPlay
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

# ------------------------- Some AI helper function ------------------------- #
def some_main_with_gemini(chat: ChatPlay, client: genai.Client) -> dict:
    """
    Gemini API를 사용해 채팅 썸의 주요 분석 결과를 반환합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns: 
        dict: 주요 대화 분석 결과
        - score_main (int) : 썸 지수 (0 ~ 100)
        - comment_main (str) : 전반적인 상황에 대한 코멘트
    """

    try:
        file_path = chat.file.path 
        with open(file_path, "r", encoding="utf-8") as f:
            # 우선은 최대 500줄만 읽도록 제한 (성능 및 비용 최적화)
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가입니다.
        주어진 카카오톡 대화 내용은 '썸'을 타고 있는 두 남녀의 대화입니다.
        이 대화 내용을 분석하여 '썸'의 성공 가능성을 100점 만점으로 점수화하고, 전반적인 상황에 대한 긍정적이고 희망적인 코멘트를 1~2문장으로 작성해주세요.

        출력 형식은 반드시 아래와 같이 맞춰주세요. 다른 부가적인 설명은 절대 추가하지 마세요.

        점수: [여기에 0-100 사이의 정수 점수]
        코멘트: [여기에 2-3 문장의 코멘트]
        ---
        {chat_content_sample}
        ---
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        
        # 정규식 활용으로 '점수:'와 '코멘트:' 뒤의 내용을 추출
        score_match = re.search(r"점수:\s*(\d+)", response.text)
        comment_match = re.search(r"코멘트:\s*(.+)", response.text)

        return {
            "score_main": int(score_match.group(1)) if score_match else 0,
            "comment_main": comment_match.group(1).strip() if comment_match else "분석 결과를 가져오는데 실패했습니다.",
        }
    
    except Exception as e:
        print(f"Gemini로 썸 분석 중 에러 발생: {e}")
        return {
            "score_main": -1,
            "comment_main": "분석 중 오류가 발생했습니다.",
        }

def some_favorability_with_gemini(chat: ChatPlay, client: genai.Client) -> dict:
    """
    Gemini API를 사용해 채팅 썸의 호감도 분석 결과를 반환합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns:
        dict: 대화 호감도 분석 결과
        - score_A (int) : A의 B에 대한 호감도
        - score_B (int) : B의 A에 대한 호감도
        - trait_A (str) : A가 B를 대하는 특징
        - trait_B (str) : B가 A를 대하는 특징
        - summary (str) : 요약
    """

    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            # 우선은 최대 500줄만 읽도록 제한 (성능 및 비용 최적화)
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        # Gemini에게 대화자 식별부터 분석까지 여러 단계의 작업을 구체적인 출력 형식과 함께 요청합니다.
        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가입니다.
        주어진 카카오톡 대화 내용은 '썸'을 타고 있는 두 사람의 대화입니다.

        1. 대화에서 가장 중심이 되는 두 사람의 이름을 찾아 각각 A와 B로 지정해주세요.
        2. A가 B에게 보이는 호감도를 100점 만점으로 평가해주세요.
        3. B가 A에게 보이는 호감도를 100점 만점으로 평가해주세요.
        4. A가 B를 대하는 대화상의 특징을 5~10자 내외의 짧은 3개의 어구로 설명해주세요. (예: 적극적으로 질문함, 다정하게 챙겨줌)
        5. B가 A를 대하는 대화상의 특징을 5~10자 내외의 짧은 3개의 어구로 설명해주세요.
        6. A와 B의 현재 관계에 대한 전반적인 인상을 2~3 문장으로 요약해주세요.

        출력 형식은 반드시 아래와 같이 라벨을 붙여서 작성해주세요. 다른 부가적인 설명은 절대 추가하지 마세요.

        A->B 호감도: [0-100 사이 정수]
        B->A 호감도: [0-100 사이 정수]
        A의 특징: [A의 특징 설명]
        B의 특징: [B의 특징 설명]
        요약: [관계 요약]

        ---
        {chat_content_sample}
        ---
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        response_text = response.text

        # 정규표현식을 사용하여 각 항목을 정확히 추출합니다.
        score_a_match = re.search(r"A->B 호감도:\s*(\d+)", response_text)
        score_b_match = re.search(r"B->A 호감도:\s*(\d+)", response_text)
        trait_a_match = re.search(r"A의 특징:\s*(.+)", response_text)
        trait_b_match = re.search(r"B의 특징:\s*(.+)", response_text)
        summary_match = re.search(r"요약:\s*(.+)", response_text, re.DOTALL) # re.DOTALL to match newlines

        return {
            "score_A": int(score_a_match.group(1)) if score_a_match else 0,
            "score_B": int(score_b_match.group(1)) if score_b_match else 0,
            "trait_A": trait_a_match.group(1).strip() if trait_a_match else "",
            "trait_B": trait_b_match.group(1).strip() if trait_b_match else "",
            "summary": summary_match.group(1).strip() if summary_match else "분석 결과를 요약하는데 실패했습니다.",
        }

    except Exception as e:
        print(f"Gemini로 호감도 분석 중 에러 발생: {e}")
        return {
            "score_A": -1,
            "score_B": -1,
            "trait_A": "",
            "trait_B": "",
            "summary": "분석 중 오류가 발생했습니다.",
        }

def some_tone_with_gemini(chat: ChatPlay, client: genai.Client) -> dict:
    """
    Gemini API를 사용해 채팅 대화의 말투, 감정표현, 호칭 분석 결과를 반환합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns:
        dict: 대화 말투 분석 결과
        - tone (int) : 말투 점수 (0 ~ 100)
        - tone_desc (str) : 말투 설명
        - tone_ex (str) : 말투 예시
        - emo (int) : 감정표현 점수 (0 ~ 100)
        - emo_desc (str) : 감정표현 설명
        - emo_ex (str) : 감정표현 예시
        - addr (int) : 호칭 점수 (0 ~ 100)
        - addr_desc (str) : 호칭 설명
        - addr_ex (str) : 호칭 예시
    """
    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            # For performance and cost optimization, read only the first 500 lines
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        # A detailed prompt asking for analysis of three distinct categories.
        # It specifies a strict output format for reliable parsing.
        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가입니다.
        주어진 카카오톡 대화 내용은 '썸'을 타고 있는 두 사람의 대화입니다.
        대화 내용을 다음 세 가지 기준에 따라 분석하고, 각 기준별로 점수, 한 줄 설명, 그리고 대화 내용에 기반한 실제 예시를 제시해주세요.

        1.  **말투**: 두 사람이 얼마나 다정하고 긍정적인 말투를 사용하는지 평가합니다. (예: "~~했어?", "~~해용", "응응")
        2.  **감정표현**: 두 사람이 이모티콘, 'ㅋㅋ', 'ㅎㅎ' 등을 얼마나 효과적으로 사용하여 긍정적인 감정을 표현하는지 평가합니다.
        3.  **호칭**: 두 사람이 서로를 어떻게 부르는지, 또는 호칭을 통해 거리를 좁히려는 시도가 있는지 평가합니다. (예: "민준아", "서연님", 별명 등)

        출력 형식은 반드시 아래와 같이 라벨을 붙여서 작성해주세요. 다른 부가적인 설명은 절대 추가하지 마세요.

        말투 점수: [0-100 사이 정수]
        말투 설명: [말투에 대한 한 줄 요약 설명]
        말투 예시: [실제 대화에서 가져온 말투 예시]
        ---
        감정표현 점수: [0-100 사이 정수]
        감정표현 설명: [감정표현에 대한 한 줄 요약 설명]
        감정표현 예시: [실제 대화에서 가져온 감정표현 예시]
        ---
        호칭 점수: [0-100 사이 정수]
        호칭 설명: [호칭에 대한 한 줄 요약 설명]
        호칭 예시: [실제 대화에서 가져온 호칭 예시]

        --- CHAT LOG ---
        {chat_content_sample}
        --- END CHAT LOG ---
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        response_text = response.text

        # Regex to capture each item. re.DOTALL allows '.' to match newlines.
        tone_score_match = re.search(r"말투 점수:\s*(\d+)", response_text)
        tone_desc_match = re.search(r"말투 설명:\s*(.+)", response_text)
        tone_ex_match = re.search(r"말투 예시:\s*(.+)", response_text)

        emo_score_match = re.search(r"감정표현 점수:\s*(\d+)", response_text)
        emo_desc_match = re.search(r"감정표현 설명:\s*(.+)", response_text)
        emo_ex_match = re.search(r"감정표현 예시:\s*(.+)", response_text)

        addr_score_match = re.search(r"호칭 점수:\s*(\d+)", response_text)
        addr_desc_match = re.search(r"호칭 설명:\s*(.+)", response_text)
        addr_ex_match = re.search(r"호칭 예시:\s*(.+)", response_text)

        return {
            "tone_score": int(tone_score_match.group(1)) if tone_score_match else 0,
            "tone_desc": tone_desc_match.group(1).strip() if tone_desc_match else "",
            "tone_ex": tone_ex_match.group(1).strip() if tone_ex_match else "",

            "emo_score": int(emo_score_match.group(1)) if emo_score_match else 0,
            "emo_desc": emo_desc_match.group(1).strip() if emo_desc_match else "",
            "emo_ex": emo_ex_match.group(1).strip() if emo_ex_match else "",

            "addr_score": int(addr_score_match.group(1)) if addr_score_match else 0,
            "addr_desc": addr_desc_match.group(1).strip() if addr_desc_match else "",
            "addr_ex": addr_ex_match.group(1).strip() if addr_ex_match else "",
        }

    except Exception as e:
        print(f"Gemini로 말투/감정 분석 중 에러 발생: {e}")
        return {
            "tone_score": -1, "tone_desc": "", "tone_ex": "",
            "emo_score": -1, "emo_desc": "", "emo_ex": "",
            "addr_score": -1, "addr_desc": "", "addr_ex": "",
            "error_message": "분석 중 오류가 발생했습니다.",
        }

 # Create a helper function for parsing to avoid repetition

def parse_response(pattern, text, is_int=False):
    match = re.search(pattern, text)
    if not match:
        return 0 if is_int else ""
    
    value = match.group(1).strip()
    return int(value) if is_int else value

def some_reply_with_gemini(chat: ChatPlay, client: genai.Client) -> dict:
    """
    Gemini API를 사용해 답장 분석 결과를 반환합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns:
        dict: 대화 패턴 분석 결과
        - reply_A (int) : A의 평균답장시간(분)
        - reply_B (int) : B의 평균답장시간(분)
        - reply_A_desc (str) : A의 답장 특징
        - reply_B_desc (str) : B의 답장 특징
    """
    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            # For performance and cost optimization, read only the first 500 lines
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        # This is a very complex prompt. It asks the model to perform several distinct analytical tasks.
        # The output format is extremely specific to ensure reliable parsing.
        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가입니다.
        주어진 카카오톡 대화 내용을 '썸'을 타고 있는 두 사람의 대화입니다.
        먼저 대화의 중심이 되는 두 사람을 A와 B로 지정한 후, 답장 패턴을 심층 분석해주세요.

        **답장 패턴**: 타임스탬프를 기반으로 각 사람의 평균 답장 시간을 '분' 단위로 추정해주세요. 그리고 답장하는 경향에 대해 한 줄로 설명해주세요.

        출력 형식은 반드시 아래의 라벨을 정확히 지켜 작성하고, 다른 부가적인 설명은 절대 추가하지 마세요.

        A 평균 답장 시간(분): [숫자]
        B 평균 답장 시간(분): [숫자]
        A 답장 특징: [A의 답장 특징에 대한 한 줄 설명]
        B 답장 특징: [B의 답장 특징에 대한 한 줄 설명]
        
        --- CHAT LOG ---
        {chat_content_sample}
        --- END CHAT LOG ---
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        response_text = response.text

        return {
            "reply_A": parse_response(r"A 평균 답장 시간\(분\):\s*(\d+)", response_text, is_int=True),
            "reply_B": parse_response(r"B 평균 답장 시간\(분\):\s*(\d+)", response_text, is_int=True),
            "reply_A_desc": parse_response(r"A 답장 특징:\s*(.+)", response_text),
            "reply_B_desc": parse_response(r"B 답장 특징:\s*(.+)", response_text),
        }

    except Exception as e:
        print(f"Gemini로 답장 패턴 분석 중 에러 발생: {e}")
        return {
            "reply_A": -1, "reply_B": -1, "reply_A_desc": "", "reply_B_desc": "",
            "error_message": "답장 패턴 분석 중 오류가 발생했습니다.",
        }
    
def some_rec_with_gemini(chat: ChatPlay, client: genai.Client) -> dict:
    """
    Gemini API를 사용해 약속제안 패턴 분석 결과를 반환합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns:
        dict: 약속 제안 분석 결과
        - rec_A (int) : A의 약속제안 횟수
        - rec_B (int) : B의 약속제안 횟수
        - rec_A_desc (str) : A의 약속제안 특징
        - rec_B_desc (str) : B의 약속제안 특징
        - rec_A_ex (str) : A의 약속제안 예시
        - rec_B_ex (str) : B의 약속제안 예시
    """
    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가입니다.
        주어진 카카오톡 대화 내용은 '썸'을 타고 있는 두 사람의 대화입니다.
        먼저 대화의 중심이 되는 두 사람을 A와 B로 지정한 후, 약속 제안 패턴을 심층 분석해주세요.

        **약속 제안**: 각 사람이 '만나자', '보자', '언제 시간 돼?' 등 명시적으로 만남을 제안한 횟수를 세어주세요. 제안하는 스타일을 설명하고, 가장 대표적인 실제 예시를 하나씩 들어주세요. (예시가 없으면 '없음'으로 표시)

        출력 형식은 반드시 아래의 라벨을 정확히 지켜 작성하고, 다른 부가적인 설명은 절대 추가하지 마세요.

        A 약속 제안 횟수: [숫자]
        B 약속 제안 횟수: [숫자]
        A 약속 제안 특징: [A의 약속 제안 스타일에 대한 한 줄 설명]
        B 약속 제안 특징: [B의 약속 제안 스타일에 대한 한 줄 설명]
        A 약속 제안 예시: [A의 실제 약속 제안 대화 예시]
        B 약속 제안 예시: [B의 실제 약속 제안 대화 예시]

        --- CHAT LOG ---
        {chat_content_sample}
        --- END CHAT LOG ---
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        response_text = response.text

        return {
            "rec_A": parse_response(r"A 약속 제안 횟수:\s*(\d+)", response_text, is_int=True),
            "rec_B": parse_response(r"B 약속 제안 횟수:\s*(\d+)", response_text, is_int=True),
            "rec_A_desc": parse_response(r"A 약속 제안 특징:\s*(.+)", response_text),
            "rec_B_desc": parse_response(r"B 약속 제안 특징:\s*(.+)", response_text),
            "rec_A_ex": parse_response(r"A 약속 제안 예시:\s*(.+)", response_text),
            "rec_B_ex": parse_response(r"B 약속 제안 예시:\s*(.+)", response_text),
        }

    except Exception as e:
        print(f"Gemini로 약속 제안 분석 중 에러 발생: {e}")
        return {
            "rec_A": -1, "rec_B": -1, "rec_A_desc": "", "rec_B_desc": "", "rec_A_ex": "", "rec_B_ex": "",
            "error_message": "약속 제안 분석 중 오류가 발생했습니다.",
        }

def some_atti_with_gemini(chat: ChatPlay, client: genai.Client) -> dict:
    """
    Gemini API를 사용해 대화의 주제시작 분석 결과를 반환합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns:
        dict: 대화 주제시작 분석 결과
        - atti_A (int) : A의 주제시작 비율(%)
        - atti_B (int) : B의 주제시작 비율(%)
        - atti_A_desc (str) : A의 주제시작 특징
        - atti_B_desc (str) : B의 주제시작 특징
        - atti_A_ex (str) : A의 주제시작 예시
        - atti_B_ex (str) : B의 주제시작 예시
        - pattern_analysis (str) : 대화 패턴 분석 결과  
    """
    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가입니다.
        주어진 카카오톡 대화 내용은 '썸'을 타고 있는 두 사람의 대화입니다.
        먼저 대화의 중심이 되는 두 사람을 A와 B로 지정한 후, 주제 시작 패턴을 심층 분석해주세요.

        **대화 주도**: 각 사람이 새로운 주제를 꺼내며 대화를 시작한 비율을 퍼센트(%)로 추정해주세요 (A와 B의 합은 100). 주제를 시작하는 스타일을 설명하고, 가장 대표적인 실제 예시를 하나씩 들어주세요. (예시가 없으면 '없음'으로 표시). 마지막으로, 이 패턴을 기반으로 두 사람의 대화 주도권에 대한 종합 분석을 2문장으로 요약해주세요.

        출력 형식은 반드시 아래의 라벨을 정확히 지켜 작성하고, 다른 부가적인 설명은 절대 추가하지 마세요.

        A 주제 시작 비율(%): [숫자]
        B 주제 시작 비율(%): [숫자]
        A 주제 시작 특징: [A의 주제시작 스타일에 대한 한 줄 설명]
        B 주제 시작 특징: [B의 주제시작 스타일에 대한 한 줄 설명]
        A 주제 시작 예시: [A의 실제 주제시작 대화 예시]
        B 주제 시작 예시: [B의 실제 주제시작 대화 예시]
        대화 패턴 분석: [대화 패턴에 대한 2문장 요약]

        --- CHAT LOG ---
        {chat_content_sample}
        --- END CHAT LOG ---
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        response_text = response.text

        return {
            "atti_A": parse_response(r"A 주제 시작 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "atti_B": parse_response(r"B 주제 시작 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "atti_A_desc": parse_response(r"A 주제 시작 특징:\s*(.+)", response_text),
            "atti_B_desc": parse_response(r"B 주제 시작 특징:\s*(.+)", response_text),
            "atti_A_ex": parse_response(r"A 주제 시작 예시:\s*(.+)", response_text),
            "atti_B_ex": parse_response(r"B 주제 시작 예시:\s*(.+)", response_text),
            "pattern_analysis": parse_response(r"대화 패턴 분석:\s*(.+)", response_text),
        }

    except Exception as e:
        print(f"Gemini로 주제시작 분석 중 에러 발생: {e}")
        return {
            "atti_A": -1, "atti_B": -1, "atti_A_desc": "", "atti_B_desc": "", "atti_A_ex": "", "atti_B_ex": "", "pattern_analysis": "",
            "error_message": "주제시작 분석 중 오류가 발생했습니다.",
        }

def some_comment_with_gemini(chat: ChatPlay, client: genai.Client) -> dict:
    """
    Gemini API를 사용해 대화의 종합 코멘트(상담 및 팁)를 생성합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns:
        dict: 분석 코멘트
        - chatto_counsel (str) : 챗토의 연애상담
        - chatto_counsel_tips (str) : 챗토의 연애상담 팁
    """
    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            # For performance and cost optimization, read only the first 500 lines
            lines = f.readlines()
            chat_content_sample = "".join(lines[:500])

        # This prompt asks the model to adopt a persona ("챗토") and generate two distinct types of content:
        # a warm counseling message and a concrete tip.
        prompt = f"""
        당신은 따뜻하고 친근한 연애 상담가 '챗토'입니다.
        주어진 카카오톡 대화 내용은 '썸'을 타고 있는 두 사람의 대화입니다. 대화 전체의 맥락과 분위기를 고려하여 아래 두 가지 내용을 작성해주세요.

        1.  **챗토의 연애상담**: 두 사람의 관계를 긍정적으로 요약하고, 따뜻한 응원의 메시지를 담아 3~4문장의 완성된 단락으로 작성해주세요.
        2.  **챗토의 연애상담 팁**: 두 사람의 관계가 한 단계 더 발전하기 위해 시도해볼 만한 구체적이고 실용적인 팁을 1~2문장으로 작성해주세요.

        출력 형식은 반드시 아래의 라벨을 정확히 지켜 작성하고, 다른 부가적인 설명은 절대 추가하지 마세요.

        챗토의 연애상담: [여기에 3~4문장의 따뜻한 상담 내용]
        챗토의 연애상담 팁: [여기에 1~2문장의 구체적인 팁]

        --- CHAT LOG ---
        {chat_content_sample}
        --- END CHAT LOG ---
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        response_text = response.text

        # Use regex with re.DOTALL to ensure multiline content is captured
        counsel_match = re.search(r"챗토의 연애상담:\s*(.+)", response_text, re.DOTALL)
        tips_match = re.search(r"챗토의 연애상담 팁:\s*(.+)", response_text, re.DOTALL)

        return {
            "chatto_counsel": counsel_match.group(1).strip() if counsel_match else "상담 내용을 가져오는 데 실패했습니다.",
            "chatto_counsel_tips": tips_match.group(1).strip() if tips_match else "팁을 가져오는 데 실패했습니다.",
        }

    except Exception as e:
        print(f"Gemini로 코멘트 생성 중 에러 발생: {e}")
        return {
            "chatto_counsel": "분석 중 오류가 발생하여 상담 내용을 생성하지 못했습니다.",
            "chatto_counsel_tips": "분석 중 오류가 발생하여 팁을 생성하지 못했습니다.",
        }


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

        # Gemini API 클라이언트를 사용하여 대화 내용을 분석
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        main_output = some_main_with_gemini(chat, client)
        favorability_output = some_favorability_with_gemini(chat, client)
        tone_output = some_tone_with_gemini(chat, client)
        reply_output = some_reply_with_gemini(chat, client)
        rec_output = some_rec_with_gemini(chat, client)
        atti_output = some_atti_with_gemini(chat, client)
        comment_output = some_comment_with_gemini(chat, client)

        ResultPlaySomeSpec.objects.create(
            result=result,
            score_main=main_output.get("score_main", 0),    # score_A + score_B / 2 로 해도 좋을 듯
            comment_main=main_output.get("comment_main", ""),
            score_A=favorability_output.get("score_A", 0),
            score_B=favorability_output.get("score_B", 0),
            trait_A=favorability_output.get("trait_A", ""),
            trait_B=favorability_output.get("trait_B", ""),
            summary=favorability_output.get("summary", ""),
            tone=tone_output.get("tone_score", 0),
            tone_desc=tone_output.get("tone_desc", ""),
            tone_ex=tone_output.get("tone_ex", ""),
            emo=tone_output.get("emo_score", 0),
            emo_desc=tone_output.get("emo_desc", ""),
            emo_ex=tone_output.get("emo_ex", ""),
            addr=tone_output.get("addr_score", 0),
            addr_desc=tone_output.get("addr_desc", ""),
            addr_ex=tone_output.get("addr_ex", ""),
            reply_A = reply_output.get("reply_A", 0),
            reply_B = reply_output.get("reply_B", 0),
            reply_A_desc = reply_output.get("reply_A_desc", ""),
            reply_B_desc = reply_output.get("reply_B_desc", ""),
            rec_A = rec_output.get("rec_A", 0),
            rec_B = rec_output.get("rec_B", 0),
            rec_A_desc = rec_output.get("rec_A_desc", ""),
            rec_B_desc = rec_output.get("rec_B_desc", ""),
            rec_A_ex = rec_output.get("rec_A_ex", ""),
            rec_B_ex = rec_output.get("rec_B_ex", ""),
            atti_A = atti_output.get("atti_A", 0),
            atti_B = atti_output.get("atti_B", 0),
            atti_A_desc = atti_output.get("atti_A_desc", ""),
            atti_B_desc = atti_output.get("atti_B_desc", ""),
            atti_A_ex = atti_output.get("atti_A_ex", ""),
            atti_B_ex = atti_output.get("atti_B_ex", ""),
            pattern_analysis = atti_output.get("pattern_analysis", ""),
            chatto_counsel = comment_output.get("chatto_counsel", ""),
            chatto_counsel_tips = comment_output.get("chatto_counsel_tips", ""),
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



# class PlayChemResultListView(APIView):
#     @swagger_auto_schema(
#         operation_id="채팅 케미 분석 결과 리스트 조회",
#         operation_description="로그인된 유저의 채팅 케미 분석 결과 리스트를 조회합니다.",
#         manual_parameters=[
#             openapi.Parameter(
#                 "Authorization",
#                 openapi.IN_HEADER, 
#                 description="access token", 
#                 type=openapi.TYPE_STRING),
#         ],
#         responses={200: ChemResultSerializerPlay(many=True), 401: "Unauthorized"},
#     )
#     def get(self, request):
#         # authenticated user check
#         author = request.user
#         if not author.is_authenticated:
#             return Response(status=status.HTTP_401_UNAUTHORIZED)
        
#         # Get all analysis results for the logged-in user
#         results = ResultPlayChem.objects.filter(chat__user = author)
#         serializer = ChemResultSerializerPlay(results, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)



# class PlaySomeResultListView(APIView):
#     @swagger_auto_schema(
#         operation_id="채팅 썸 분석 결과 리스트 조회",
#         operation_description="로그인된 유저의 채팅 썸 분석 결과 리스트를 조회합니다.",
#         manual_parameters=[
#             openapi.Parameter(
#                 "Authorization",
#                 openapi.IN_HEADER, 
#                 description="access token", 
#                 type=openapi.TYPE_STRING),
#         ],
#         responses={200: SomeResultSerializerPlay(many=True), 401: "Unauthorized"},
#     )
#     def get(self, request):
#         # authenticated user check
#         author = request.user
#         if not author.is_authenticated:
#             return Response(status=status.HTTP_401_UNAUTHORIZED)
        
#         # Get all analysis results for the logged-in user
#         results = ResultPlaySome.objects.filter(chat__user = author)
#         serializer = SomeResultSerializerPlay(results, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)



# class PlayMBTIResultListView(APIView):
#     @swagger_auto_schema(
#         operation_id="채팅 MBTI 분석 결과 리스트 조회",
#         operation_description="로그인된 유저의 채팅 MBTI 분석 결과 리스트를 조회합니다.",
#         manual_parameters=[
#             openapi.Parameter(
#                 "Authorization",
#                 openapi.IN_HEADER, 
#                 description="access token", 
#                 type=openapi.TYPE_STRING),
#         ],
#         responses={200: MBTIResultSerializerPlay(many=True), 401: "Unauthorized"},
#     )
#     def get(self, request):
#         # authenticated user check
#         author = request.user
#         if not author.is_authenticated:
#             return Response(status=status.HTTP_401_UNAUTHORIZED)
        
#         # Get all analysis results for the logged-in user
#         results = ResultPlayMBTI.objects.filter(chat__user = author)
#         serializer = MBTIResultSerializerPlay(results, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)



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