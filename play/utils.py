import re
from google import genai
# import settings  # 실제 환경에서는 API 키를 포함한 settings 모듈을 임포트해야 합니다.
from .models import ChatPlay
from django.conf import settings
from datetime import datetime

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
            model='gemini-2.5-flash',
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

def parse_response(pattern, text, is_int=False):
    match = re.search(pattern, text)
    if not match:
        return 0 if is_int else ""
    
    value = match.group(1).strip()
    return int(value) if is_int else value

def filter_chat_by_date(lines: list, analysis_option: dict) -> list:
    """
    채팅 로그(lines)를 사용자가 지정한 기간(analysis_option)으로 필터링합니다.

    Args:
        lines (list): 전체 채팅 로그 리스트
        analysis_option (dict): 시작일과 종료일이 담긴 딕셔너리

    Returns:
        list: 필터링된 채팅 로그 리스트
    """
    start_option = analysis_option.get("start")
    end_option = analysis_option.get("end")

    start_date = None if start_option == "처음부터" else start_option
    end_date = None if end_option == "끝까지" else end_option

    filtered_lines = []
    current_date = None
    date_pattern = re.compile(r"--------------- (\d{4}년 \d{1,2}월 \d{1,2}일)")

    for line in lines:
        date_match = date_pattern.search(line)
        if date_match:
            date_str = date_match.group(1)
            current_date = datetime.strptime(date_str, "%Y년 %m월 %d일").date()
        
        if not current_date:
            continue
        
        is_after_start = start_date is None or current_date >= start_date
        is_before_end = end_date is None or current_date <= end_date

        if is_after_start and is_before_end:
            filtered_lines.append(line)

    return filtered_lines

# ------------------------- some AI helper function ------------------------- #
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

    """
    Gemini API를 사용해 채팅 썸의 주요 분석 결과를 반환합니다.

    Args:
        chat (str): 분석할 전체 채팅 내용 문자열

    Returns:
        dict: 다음과 같은 키를 포함하는 딕셔너리
            - score_main (int): 썸 성공 가능성 총점 (0-100)
            - comment_main (str): 전반적인 상황에 대한 코멘트
    """
    try:
        # Gemini API 클라이언트 초기화
        # client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Gemini에게 역할을 부여하고, 원하는 결과물의 형식을 구체적으로 지정하는 프롬프트
        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가입니다.
        주어진 카카오톡 대화 내용은 '썸'을 타고 있는 두 남녀의 대화입니다.
        이 대화 내용을 분석하여 '썸'의 성공 가능성을 100점 만점으로 점수화하고, 전반적인 상황에 대한 긍정적이고 희망적인 코멘트를 1~2문장으로 작성해주세요.

        출력 형식은 반드시 아래와 같이 맞춰주세요. 다른 부가적인 설명은 절대 추가하지 마세요.

        점수: [여기에 0-100 사이의 정수 점수]
        코멘트: [여기에 1-2 문장의 코멘트]

        ---
        {chat}
        ---
        """

        # # 실제 API 호출
        # response = client.models.generate_content(
        #     model='gemini-pro',  # 또는 다른 적절한 모델
        #     contents=[prompt]
        # )
        # response_text = response.text
        
        # 아래는 API 응답 예시입니다.
        response_text = "점수: 85\n코멘트: 두 분 사이에 긍정적인 신호가 많이 보여요! 서로에게 더 솔직하게 다가간다면 좋은 관계로 발전할 가능성이 매우 높습니다."


        # 정규표현식을 사용해 '점수:'와 '코멘트:' 뒤의 내용을 추출
        score_match = re.search(r"점수:\s*(\d+)", response_text)
        comment_match = re.search(r"코멘트:\s*(.+)", response_text)

        score = int(score_match.group(1)) if score_match else 0
        comment = comment_match.group(1).strip() if comment_match else "분석 결과를 가져오는 데 실패했습니다."

        return {
            "score_main": score,
            "comment_main": comment,
        }

    except Exception as e:
        print(f"Gemini로 썸 분석 중 에러 발생: {e}")
        return {
            "score_main": 0,
            "comment_main": "분석 중 오류가 발생했습니다.",
        }
 
# ------------------------- SOME AI helper function ------------------------- #
def some_analysis_with_gemini(chat: ChatPlay, client: genai.Client, analysis_option: dict) -> dict:
    """
    사용자가 지정한 기간의 채팅을 필터링한 후,
    Gemini API를 단 한 번 호출하여 '썸' 관계에 대한 종합 분석 결과를 반환합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체.
        client (genai.Client): Gemini API 클라이언트.
        analysis_option (dict): 썸 분석 옵션 딕셔너리.

    Returns:
        dict: 모든 분석 항목을 포함하는 종합 결과 딕셔너리.
    """
    try:
        with open(chat.file.path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        # 1. 사용자가 선택한 기간으로 채팅 로그 필터링
        filtered_lines = filter_chat_by_date(all_lines, analysis_option)
        
        # 분석할 채팅이 없는 경우 처리
        if not filtered_lines:
             return {
                "error_message": "선택하신 기간에 해당하는 대화 내용이 없습니다."
             }

        # 2. 필터링된 로그를 바탕으로 Gemini에 보낼 샘플 생성 (최대 1000줄)
        chat_content_sample = "".join(filtered_lines[:1000])

        # 3. analysis_option에서 나이, 희망 관계 정보 추출
        age_info = analysis_option.get("age", "알 수 없음")
        relationship_info = analysis_option.get("relationship", "알 수 없음")

        # 4. 모든 분석 요청을 하나의 프롬프트로 통합
        prompt = f"""
        당신은 연애 상담 및 카카오톡 대화 분석 전문가 '챗토'입니다.

        [분석 요청자 정보]
        - 나이대: {age_info}
        - 상대방과 희망하는 관계: {relationship_info}

        [당신의 임무]
        요청자의 희망 사항에 편향되지 말고, 주어진 대화 내용만을 근거로 두 사람의 '썸' 성공 가능성과 현재 관계의 분위기를 **매우 객관적으로 분석**해야 합니다.
        반드시 지정된 출력 형식에 맞춰 결과를 작성해주세요. 다른 부가 설명은 절대 추가하지 마세요.

        [분석 항목]
        1.  **주요 분석**: '썸'의 성공 가능성을 0~100점 사이의 '썸 지수'로 평가하고, 전반적인 상황에 대한 1~2 문장의 코멘트를 작성해주세요.
        2.  **호감도 분석**: 대화의 중심인물 두 명을 A와 B로 지정하세요. A가 B에게, B가 A에게 보이는 호감도를 각각 0~100점으로 평가하고, 각자가 상대를 대하는 대화상 특징을 5~10자 내외의 짧은 어구 3개로 설명해주세요. 마지막으로 관계를 2~3문장으로 요약해주세요.
        3.  **대화 스타일 분석**: 말투, 감정표현(이모티콘, ㅋㅋ 등), 호칭 세 가지 기준에 대해 각각 0~100점 점수, 한 줄 설명, 실제 대화 예시를 제시해주세요.
        4.  **답장 패턴 분석**: 타임스탬프를 기반으로 A와 B의 평균 답장 시간을 '분' 단위로 추정하고, 각자의 답장 경향을 한 줄로 설명해주세요.
        5.  **약속 제안 분석**: A와 B가 만남을 제안한 횟수를 각각 세고, 제안 스타일을 한 줄로 설명한 뒤, 가장 대표적인 실제 제안 예시를 각각 들어주세요. (예시가 없으면 '없음')
        6.  **대화 주도권 분석**: A와 B가 새로운 대화 주제를 시작한 비율을 합계 100%가 되도록 추정하고, 주제를 시작하는 스타일을 한 줄로 설명한 뒤, 실제 예시를 각각 들어주세요. (예시가 없으면 '없음'). 마지막으로 대화 패턴을 2문장으로 요약해주세요.
        7.  **종합 상담**: '챗토'의 입장에서, 두 사람의 관계를 긍정적으로 요약하고 응원하는 3~4문장의 따뜻한 상담 메시지와, 관계 발전을 위한 1~2문장의 실용적인 팁을 작성해주세요.

        --- [출력 형식] ---
        썸 지수: [숫자]
        전반적인 코멘트: [1-2 문장 코멘트]
        ###
        이름 A: [A의 실제 이름]
        이름 B: [B의 실제 이름]
        A->B 호감도: [숫자]
        B->A 호감도: [숫자]
        A의 특징: [특징1, 특징2, 특징3]
        B의 특징: [특징1, 특징2, 특징3]
        호감도 요약: [2-3 문장 요약]
        ###
        말투 점수: [숫자]
        말투 설명: [한 줄 설명]
        말투 예시: [실제 대화 예시]
        감정표현 점수: [숫자]
        감정표현 설명: [한 줄 설명]
        감정표현 예시: [실제 대화 예시]
        호칭 점수: [숫자]
        호칭 설명: [한 줄 설명]
        호칭 예시: [실제 대화 예시]
        ###
        A 평균 답장 시간(분): [숫자]
        B 평균 답장 시간(분): [숫자]
        A 답장 특징: [한 줄 설명]
        B 답장 특징: [한 줄 설명]
        ###
        A 약속 제안 횟수: [숫자]
        B 약속 제안 횟수: [숫자]
        A 약속 제안 특징: [한 줄 설명]
        B 약속 제안 특징: [한 줄 설명]
        A 약속 제안 예시: [실제 대화 예시]
        B 약속 제안 예시: [실제 대화 예시]
        ###
        A 주제 시작 비율(%): [숫자]
        B 주제 시작 비율(%): [숫자]
        A 주제 시작 특징: [한 줄 설명]
        B 주제 시작 특징: [한 줄 설명]
        A 주제 시작 예시: [실제 대화 예시]
        B 주제 시작 예시: [실제 대화 예시]
        대화 패턴 분석: [2문장 요약]
        ###
        챗토의 연애상담: [3-4 문장의 따뜻한 상담 내용]
        챗토의 연애상담 팁: [1-2 문장의 구체적인 팁]

        --- [카카오톡 대화 내용] ---
        {chat_content_sample}
        --- [분석 시작] ---
        """

        # Gemini API 호출
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
        response_text = response.text

        # 4. 헬퍼 함수를 사용하여 응답 텍스트를 파싱하고 딕셔너리로 구성
        results = {
            "name_A": parse_response(r"이름 A:\s*(.+)", response_text),
            "name_B": parse_response(r"이름 B:\s*(.+)", response_text),
            "score_main": parse_response(r"썸 지수:\s*(\d+)", response_text, is_int=True),
            "comment_main": parse_response(r"전반적인 코멘트:\s*(.+)", response_text),
            "score_A": parse_response(r"A->B 호감도:\s*(\d+)", response_text, is_int=True),
            "score_B": parse_response(r"B->A 호감도:\s*(\d+)", response_text, is_int=True),
            "trait_A": parse_response(r"A의 특징:\s*(.+)", response_text),
            "trait_B": parse_response(r"B의 특징:\s*(.+)", response_text),
            "summary": parse_response(r"호감도 요약:\s*(.+)", response_text),
            "tone_score": parse_response(r"말투 점수:\s*(\d+)", response_text, is_int=True),
            "tone_desc": parse_response(r"말투 설명:\s*(.+)", response_text),
            "tone_ex": parse_response(r"말투 예시:\s*(.+)", response_text),
            "emo_score": parse_response(r"감정표현 점수:\s*(\d+)", response_text, is_int=True),
            "emo_desc": parse_response(r"감정표현 설명:\s*(.+)", response_text),
            "emo_ex": parse_response(r"감정표현 예시:\s*(.+)", response_text),
            "addr_score": parse_response(r"호칭 점수:\s*(\d+)", response_text, is_int=True),
            "addr_desc": parse_response(r"호칭 설명:\s*(.+)", response_text),
            "addr_ex": parse_response(r"호칭 예시:\s*(.+)", response_text),
            "reply_A": parse_response(r"A 평균 답장 시간\(분\):\s*(\d+)", response_text, is_int=True),
            "reply_B": parse_response(r"B 평균 답장 시간\(분\):\s*(\d+)", response_text, is_int=True),
            "reply_A_desc": parse_response(r"A 답장 특징:\s*(.+)", response_text),
            "reply_B_desc": parse_response(r"B 답장 특징:\s*(.+)", response_text),
            "rec_A": parse_response(r"A 약속 제안 횟수:\s*(\d+)", response_text, is_int=True),
            "rec_B": parse_response(r"B 약속 제안 횟수:\s*(\d+)", response_text, is_int=True),
            "rec_A_desc": parse_response(r"A 약속 제안 특징:\s*(.+)", response_text),
            "rec_B_desc": parse_response(r"B 약속 제안 특징:\s*(.+)", response_text),
            "rec_A_ex": parse_response(r"A 약속 제안 예시:\s*(.+)", response_text),
            "rec_B_ex": parse_response(r"B 약속 제안 예시:\s*(.+)", response_text),
            "atti_A": parse_response(r"A 주제 시작 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "atti_B": parse_response(r"B 주제 시작 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "atti_A_desc": parse_response(r"A 주제 시작 특징:\s*(.+)", response_text),
            "atti_B_desc": parse_response(r"B 주제 시작 특징:\s*(.+)", response_text),
            "atti_A_ex": parse_response(r"A 주제 시작 예시:\s*(.+)", response_text),
            "atti_B_ex": parse_response(r"B 주제 시작 예시:\s*(.+)", response_text),
            "pattern_analysis": parse_response(r"대화 패턴 분석:\s*(.+)", response_text),
            "chatto_counsel": parse_response(r"챗토의 연애상담:\s*(.+)", response_text),
            "chatto_counsel_tips": parse_response(r"챗토의 연애상담 팁:\s*(.+)", response_text),
        }
        return results

    except Exception as e:
        print(f"Gemini로 종합 분석 중 에러 발생: {e}")
        return {
            "error_message": f"분석 중 오류가 발생했습니다: {e}"
        }
# ------------------------- MBTI AI helper function ------------------------- #
def mbti_analysis_with_gemini(chat: ChatPlay, client: genai.Client, analysis_option: dict) -> list:
    """
    Gemini API를 사용해 채팅 참여자들의 MBTI를 분석합니다.

    Args:
        chat (ChatPlay): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트

    Returns:
        list: 각 참여자의 MBTI 분석 결과 딕셔너리가 담긴 리스트.
              예: [
                  {
                      "name": "참여자1", "mbti": "ENFP", "summary": "...", 
                      "ie_desc": "...", "ie_ex": "...", ...
                  },
                  {
                      "name": "참여자2", "mbti": "ISTJ", "summary": "...",
                      "ie_desc": "...", "ie_ex": "...", ...
                  }
              ]
    """
    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
            filtered_lines = filter_chat_by_date(lines, analysis_option)

            chat_content_sample = "".join(filtered_lines[:1000]) 

        # Gemini에게 보낼 프롬프트입니다.
        # 각 참여자별로 분석을 반복하고, 명확한 구분자(--- PERSON ANALYSIS ---)를 사용하도록 지시합니다.
        prompt = f"""
        당신은 대화 내용을 기반으로 MBTI를 분석하는 심리 분석 전문가입니다.
        주어진 카카오톡 대화 내용을 분석하여, 대화의 주요 참여자 전원의 정보를 예측해주세요.

        각 참여자에 대해 다음 항목들을 분석하고, 반드시 지정된 출력 형식에 맞춰 작성해야 합니다.
        1.  이름: 대화에서 사용된 참여자의 이름을 정확히 기재해주세요.
        2.  MBTI: 예측된 MBTI 유형 16가지 중 하나를 기재해주세요.
        3.  요약 (summary): 해당 참여자의 대화 스타일과 성격을 보여주는 한 줄 요약을 작성해주세요.
        4.  설명+부가설명 (desc): 예측된 MBTI와 요약을 바탕으로, 성격에 대한 2-3문장의 부가 설명을 작성해주세요.
        5.  단톡 내 포지션 (position): 대화에서 보이는 역할을 한 단어로 표현해주세요 (예: 분위기메이커, 정보공유자, 리더, 조용한관찰자).
        6.  성향 (personality): 성격을 나타내는 키워드를 '#'을 붙여 3가지 제시해주세요 (예: #활발함, #공감능력, #계획적).
        7.  대화특징 (style): 대화 스타일의 특징을 나타내는 키워드를 '#'을 붙여 3가지 제시해주세요 (예: #질문요정, #풍부한리액션, #논리적인설명).
        8.  대표 MBTI 모먼트 (moment): 성격이 가장 잘 드러나는 대표적인 대화 순간 하나를 인용하고, 왜 그렇게 생각하는지 한 문장으로 설명해주세요.
        9.  각 MBTI 지표(I/E, S/N, F/T, J/P) 분석: 각 지표에 대해 왜 그렇게 판단했는지 1-2 문장으로 설명하고, 근거가 된 실제 대화 내용을 정확히 인용해주세요.

        아래 출력 형식을 반드시 지켜주세요. 참여자별 분석은 '--- PERSON ANALYSIS ---'로 구분해주세요.
        다른 부가적인 설명은 절대 추가하지 마세요.

        --- PERSON ANALYSIS ---
        이름: [참여자 이름]
        MBTI: [예측 MBTI]
        summary: [성격 및 대화 스타일 요약]
        desc: [2-3 문장의 부가 설명]
        position: [한 단어로 표현된 포지션]
        personality: [#키워드1, #키워드2, #키워드3]
        style: [#키워드1, #키워드2, #키워드3]
        moment_desc: [대표 모먼트에 대한 한 문장 설명]
        moment_ex: [가장 대표적인 실제 대화 예시]
        momentIE_desc: [내향/외향 판단 근거]
        momentIE_ex: [실제 대화 예시]
        momentSN_desc: [감각/직관 판단 근거]
        momentSN_ex: [실제 대화 예시]
        momentFT_desc: [감정/사고 판단 근거]
        momentFT_ex: [실제 대화 예시]
        momentJP_desc: [판단/인식 판단 근거]
        momentJP_ex: [실제 대화 예시]

        --- CHAT LOG ---
        {chat_content_sample}
        --- END CHAT LOG ---
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
        response_text = response.text

        analyses = response_text.split('--- PERSON ANALYSIS ---')
        results = []

        for analysis_block in analyses:
            if not analysis_block.strip():
                continue

            # DB 스키마에 맞게 모든 필드를 파싱합니다.
            name = parse_response(r"이름:\s*(.+)", analysis_block)
            mbti = parse_response(r"MBTI:\s*([A-Z]{4})", analysis_block)
            summary = parse_response(r"summary:\s*(.+)", analysis_block)
            desc = parse_response(r"desc:\s*(.+)", analysis_block)
            position = parse_response(r"position:\s*(.+)", analysis_block)
            personality = parse_response(r"personality:\s*(.+)", analysis_block)
            style = parse_response(r"style:\s*(.+)", analysis_block)
            moment_desc = parse_response(r"moment_desc:\s*(.+)", analysis_block)
            moment_ex = parse_response(r"moment_ex:\s*(.+)", analysis_block)
            momentIE_desc = parse_response(r"momentIE_desc:\s*(.+)", analysis_block)
            momentIE_ex = parse_response(r"momentIE_ex:\s*(.+)", analysis_block)
            momentSN_desc = parse_response(r"momentSN_desc:\s*(.+)", analysis_block)
            momentSN_ex = parse_response(r"momentSN_ex:\s*(.+)", analysis_block)
            momentFT_desc = parse_response(r"momentFT_desc:\s*(.+)", analysis_block)
            momentFT_ex = parse_response(r"momentFT_ex:\s*(.+)", analysis_block)
            momentJP_desc = parse_response(r"momentJP_desc:\s*(.+)", analysis_block)
            momentJP_ex = parse_response(r"momentJP_ex:\s*(.+)", analysis_block)

            if name and mbti:
                results.append({
                    "name": name,
                    "MBTI": mbti,
                    "summary": summary,
                    "desc": desc,
                    "position": position,
                    "personality": personality,
                    "style": style,
                    "moment_desc": moment_desc,
                    "moment_ex": moment_ex,
                    "momentIE_desc": momentIE_desc,
                    "momentIE_ex": momentIE_ex,
                    "momentSN_desc": momentSN_desc,
                    "momentSN_ex": momentSN_ex,
                    "momentFT_desc": momentFT_desc,
                    "momentFT_ex": momentFT_ex,
                    "momentJP_desc": momentJP_desc,
                    "momentJP_ex": momentJP_ex,
                })

        return results

    except Exception as e:
        print(f"Gemini로 MBTI 상세 분석 중 에러 발생: {e}")
        return [{"error_message": "MBTI 상세 분석 중 오류가 발생했습니다."}]

# ------------------------- CHMI AI helper function ------------------------- #
def chem_analysis_with_gemini(chat: ChatPlay, client: genai.Client, analysis_option: dict) -> dict:
    """
    단체 채팅방의 '케미'를 종합적으로 분석합니다.
    사용자의 상황 정보를 참고하여 전반적인 점수, Top3 케미 조합, 대화 스타일,
    주요 토픽, 상호작용 매트릭스, 맞춤형 조언 등을 생성합니다.
    """
    try:
        with open(chat.file.path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        filtered_lines = filter_chat_by_date(all_lines, analysis_option)
        
        if not filtered_lines:
            return {"error_message": "선택하신 기간에 해당하는 대화 내용이 없습니다."}

        # 단체 채팅은 더 많은 맥락이 필요하므로 샘플을 1000줄로 늘립니다.
        chat_content_sample = "".join(filtered_lines[:1000])

        relationship_info = analysis_option.get("relationship", "알 수 없음")
        situation_info = analysis_option.get("situation", "알 수 없음")
        people_num = chat.people_num
        # 분석할 참여자 수를 최대 5명으로 제한
        size = 5 if people_num >= 5 else people_num

        prompt = f"""
        당신은 그룹 커뮤니케이션 및 관계 분석 전문가 '챗토'입니다.

        [분석 요청 정보]
        - 참여자 수: {people_num}명
        - 관계 유형: {relationship_info}
        - 대화 상황: {situation_info}

        [당신의 임무]
        주어진 단체 카톡방 대화 내용을 바탕으로, 그룹의 전반적인 '케미'와 멤버 간의 상호작용을 객관적으로 분석해야 합니다.
        아래의 모든 분석 항목에 대해, 반드시 지정된 출력 형식에 맞춰 결과를 작성해주세요.

        [분석 항목]
        1.  **핵심 분석**: 그룹 전체의 케미를 100점 만점으로 평가하고, 2-3문장으로 요약해주세요.
        2.  **참여자 식별**: 대화에서 가장 활동적인 참여자 {size}명의 이름을 찾아주세요.
        3.  **최고의 케미 조합 Top 3**: 가장 케미가 좋은 두 사람의 조합(Dyad) 3개를 찾아, 각 조합의 이름, 케미 점수, 긍정적인 이유를 한 문장으로 설명해주세요.
        4.  **대화 스타일**: 그룹의 전체적인 말투를 '긍정적/다정함', '유머러스함', '기타(중립, 비판 등)' 세 가지로 나누어 비율(%)을 추정하고, 가장 특징적인 대화 예시를 하나 들어주세요.
        5.  **응답 패턴**: 그룹의 평균 답장 시간(분), 전체적인 응답률(%), 그리고 답을 받지 못하고 묻힌 메시지 비율(%)을 추정하고, 응답 패턴에 대한 종합 분석을 1-2문장으로 요약해주세요.
        6.  **주요 토픽**: 대화에서 가장 많이 언급된 상위 4개 토픽과 각 토픽의 비율(%)을 분석해주세요.
        7.  **상호작용 매트릭스**: 위에서 식별한 {size}명의 참여자 간 상호작용 점수(0~100)를 계산해주세요. A가 B에게 보낸 메시지의 긍정성, 응답률 등을 종합하여 점수를 매깁니다.
        8.  **챗토의 종합 솔루션**: 그룹의 현재 상태를 진단하고, 관계를 더 좋게 만들기 위한 솔루션의 제목과 구체적인 팁을 작성해주세요.

        --- [출력 형식] ---
        전체 케미 점수: [숫자]
        전체 케미 요약: [2-3 문장 요약]
        ###
        참여자 1: [이름]
        참여자 2: [이름]
        참여자 3: [이름]
        참여자 4: [이름]
        참여자 5: [이름]
        ###
        Top1 이름 A: [이름]
        Top1 이름 B: [이름]
        Top1 케미 점수: [숫자]
        Top1 코멘트: [한 문장 설명]
        ---
        Top2 이름 A: [이름]
        Top2 이름 B: [이름]
        Top2 케미 점수: [숫자]
        Top2 코멘트: [한 문장 설명]
        ---
        Top3 이름 A: [이름]
        Top3 이름 B: [이름]
        Top3 케미 점수: [숫자]
        Top3 코멘트: [한 문장 설명]
        ###
        긍정 말투 비율(%): [숫자]
        유머 말투 비율(%): [숫자]
        기타 말투 비율(%): [숫자]
        말투 대표 예시: [실제 대화 예시]
        ###
        평균 답장 시간(분): [숫자]
        응답률(%): [숫자]
        메시지 무시 비율(%): [숫자]
        응답 패턴 종합 분석: [1-2 문장 요약]
        ###
        주요 토픽 1: [토픽 이름]
        주요 토픽 1 비율(%): [숫자]
        주요 토픽 2: [토픽 이름]
        주요 토픽 2 비율(%): [숫자]
        주요 토픽 3: [토픽 이름]
        주요 토픽 3 비율(%): [숫자]
        주요 토픽 4: [토픽 이름]
        주요 토픽 4 비율(%): [숫자]
        기타 토픽 비율(%): [숫자]
        ###
        상호작용 매트릭스: [참여자1-참여자2: 점수, 참여자1-참여자3: 점수, ...]
        ###
        챗토의 종합 분석: [그룹 관계 진단]
        챗토의 관계 레벨업: [솔루션 제목]
        챗토의 관계 레벨업 팁: [구체적인 팁]

        --- [카카오톡 대화 내용] ---
        {chat_content_sample}
        --- [분석 시작] ---
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash', contents=[prompt]
        )
        response_text = response.text

        # 상호작용 매트릭스 파싱 로직
        matrix_str = parse_response(r"상호작용 매트릭스:\s*\[(.+)\]", response_text)
        interaction_matrix = {}
        if matrix_str:
            pairs = matrix_str.split(',')
            for pair in pairs:
                try:
                    key, value = pair.split(':')
                    interaction_matrix[key.strip()] = int(value.strip())
                except ValueError:
                    continue # 파싱 오류 시 해당 쌍은 건너뜀

        results = {
            "score_main": parse_response(r"전체 케미 점수:\s*(\d+)", response_text, is_int=True),
            "summary_main": parse_response(r"전체 케미 요약:\s*(.+)", response_text),
            "name_0": parse_response(r"참여자 1:\s*(.+)", response_text),
            "name_1": parse_response(r"참여자 2:\s*(.+)", response_text),
            "name_2": parse_response(r"참여자 3:\s*(.+)", response_text),
            "name_3": parse_response(r"참여자 4:\s*(.+)", response_text),
            "name_4": parse_response(r"참여자 5:\s*(.+)", response_text),
            "top1_A": parse_response(r"Top1 이름 A:\s*(.+)", response_text),
            "top1_B": parse_response(r"Top1 이름 B:\s*(.+)", response_text),
            "top1_score": parse_response(r"Top1 케미 점수:\s*(\d+)", response_text, is_int=True),
            "top1_comment": parse_response(r"Top1 코멘트:\s*(.+)", response_text),
            "top2_A": parse_response(r"Top2 이름 A:\s*(.+)", response_text),
            "top2_B": parse_response(r"Top2 이름 B:\s*(.+)", response_text),
            "top2_score": parse_response(r"Top2 케미 점수:\s*(\d+)", response_text, is_int=True),
            "top2_comment": parse_response(r"Top2 코멘트:\s*(.+)", response_text),
            "top3_A": parse_response(r"Top3 이름 A:\s*(.+)", response_text),
            "top3_B": parse_response(r"Top3 이름 B:\s*(.+)", response_text),
            "top3_score": parse_response(r"Top3 케미 점수:\s*(\d+)", response_text, is_int=True),
            "top3_comment": parse_response(r"Top3 코멘트:\s*(.+)", response_text),
            "tone_pos": parse_response(r"긍정 말투 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "tone_humer": parse_response(r"유머 말투 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "tone_else": parse_response(r"기타 말투 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "tone_ex": parse_response(r"말투 대표 예시:\s*(.+)", response_text),
            "resp_time": parse_response(r"평균 답장 시간\(분\):\s*(\d+)", response_text, is_int=True),
            "resp_ratio": parse_response(r"응답률\(%\):\s*(\d+)", response_text, is_int=True),
            "ignore": parse_response(r"메시지 무시 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "resp_analysis": parse_response(r"응답 패턴 종합 분석:\s*(.+)", response_text),
            "topic1": parse_response(r"주요 토픽 1:\s*(.+)", response_text),
            "topic1_ratio": parse_response(r"주요 토픽 1 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "topic2": parse_response(r"주요 토픽 2:\s*(.+)", response_text),
            "topic2_ratio": parse_response(r"주요 토픽 2 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "topic3": parse_response(r"주요 토픽 3:\s*(.+)", response_text),
            "topic3_ratio": parse_response(r"주요 토픽 3 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "topic4": parse_response(r"주요 토픽 4:\s*(.+)", response_text),
            "topic4_ratio": parse_response(r"주요 토픽 4 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "topicelse_ratio": parse_response(r"기타 토픽 비율\(%\):\s*(\d+)", response_text, is_int=True),
            "chatto_analysis": parse_response(r"챗토의 종합 분석:\s*(.+)", response_text),
            "chatto_levelup": parse_response(r"챗토의 관계 레벨업:\s*(.+)", response_text),
            "chatto_levelup_tips": parse_response(r"챗토의 관계 레벨업 팁:\s*(.+)", response_text),
            "interaction_matrix": interaction_matrix, # 파싱된 딕셔너리
        }
        return results

    except Exception as e:
        print(f"Gemini로 케미 분석 중 에러 발생: {e}")
        return {"error_message": f"케미 분석 중 오류가 발생했습니다: {e}"}