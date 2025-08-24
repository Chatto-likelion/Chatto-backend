import re
from google import genai
# import settings  # 실제 환경에서는 API 키를 포함한 settings 모듈을 임포트해야 합니다.
from .models import ChatBus
from django.conf import settings
from datetime import datetime, date

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
            lines = f.readlines()
            chat_content_sample = "".join(lines)

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
    value = strip_helper(value)
    return int(value) if is_int else value

def filter_chat_by_date(lines: list, analysis_option: dict) -> tuple[list, int]:
    """
    채팅 로그(lines)를 사용자가 지정한 기간(analysis_option)으로 필터링하고,
    필터링된 라인의 수를 함께 반환합니다.

    Args:
        lines (list): 전체 채팅 로그 리스트
        analysis_option (dict): 시작일과 종료일이 담긴 딕셔너리

    Returns:
        tuple: (필터링된 채팅 로그 리스트, 필터링된 라인 수)
    """
    start_option = analysis_option.get("start")
    end_option = analysis_option.get("end")

    # analysis_option의 날짜 형식이 'YYYY-MM-DD' 문자열이라고 가정합니다.
    # 만약 datetime.date 객체라면 .strptime() 부분을 제거해야 합니다.
    start_date = None if start_option == "처음부터" else datetime.strptime(start_option, "%Y-%m-%d").date()
    end_date = None if end_option == "끝까지" else datetime.strptime(end_option, "%Y-%m-%d").date()

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

    # 필터링된 라인 리스트와 그 길이를 튜플로 반환
    return filtered_lines, len(filtered_lines)

def strip_helper(text: str) -> str:
    """
    문자열에서 불필요한 부분들을 제거합니다.
    1. 앞뒤의 마크다운 코드 블록(```)
    2. 대괄호([])와 그 안의 내용 (이름, 시간 등)
    3. 앞뒤의 불필요한 기호(따옴표, 공백 등)
    """
    # 1. '```json', '```' 등 코드 블록 제거
    cleaned_text = re.sub(r'^```[\w]*\n', '', text)
    cleaned_text = re.sub(r'\n```$', '', cleaned_text)

    # 2. [사람 이름] [시간] 이 연속된 헤더가 있을 경우 제거
    cleaned_text = re.sub(r'^\[.*?\]\s*\[.*?\]\s*', '', cleaned_text)

    # 3. 양 끝에 남은 공백, 따옴표(`'`, `"`), 백틱(`)을 모두 제거
    chars_to_strip = "\"'` "
    previous_text = ""
    while cleaned_text != previous_text:
        previous_text = cleaned_text
        cleaned_text = cleaned_text.strip(chars_to_strip)

    # 4. (선택) 여러 개의 공백을 하나로 합치기
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

    return cleaned_text


def contrib_analysis_with_gemini(client: genai.Client, chat: ChatBus, analysis_option: dict) -> dict:
    """
    Gemini API를 사용해 채팅 참여자들의 기여도를 분석합니다.

    Args:
        chat (ChatBus): 분석할 채팅 객체
        client (genai.Client): Gemini API 클라이언트
        analysis_option (dict): 분석 옵션

    Returns:
        dict: 모든 분석 항목을 포함하는 종합 결과 딕셔너리.
    """
    try:
        file_path = chat.file.path
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        filtered_lines, num_chat = filter_chat_by_date(lines, analysis_option)

        if not filtered_lines:
            return {"error_message": "선택하신 기간에 해당하는 대화 내용이 없습니다."}

        chat_content_sample = "".join(filtered_lines) 
        analysis_size = len(filtered_lines)

        project_type = analysis_option.get("project_type", "지정되지 않음")
        team_type = analysis_option.get("team_type", "지정되지 않음")
        
        # --- ERD 기반의 상세 프롬프트 ---
        comprehensive_prompt = f"""
        당신은 그룹 채팅 내용을 분석하여 팀의 협업 방식과 개인별 기여도를 평가하는 전문가입니다.
        주어진 채팅 내용과 프로젝트 정보를 바탕으로 아래 항목들을 매우 객관적으로 분석해주세요.

        [프로젝트 정보]
        - 프로젝트 종류: {project_type}
        - 팀 종류: {team_type}

        [분석 요청 항목]
        1.  **전체 요약 분석 (Overall Spec)**
            -   `대화 주도자`: 전체 대화의 흐름을 가장 많이 이끈 사람의 이름.
            -   `평균 응답 속도`: 전체 대화의 평균 응답 속도를 '분' 단위로 추정.
            -   `AI 생성 인사이트`: 대화에서 발견된 팀의 협업 특징, 강점, 약점에 대한 1-2 문장의 인사이트.
            -   `AI 추천 솔루션`: 발견된 문제점이나 협업 방식 개선을 위한 1-2 문장의 구체적인 솔루션.

        2.  **기간별 분석 (Periodic Analysis)**
            -   전체 대화를 시간 순서에 따라 6개의 구간으로 동일하게 나눕니다.
            -   각 참여자별로 6개 구간에서의 점수(0~100)를 (1)종합 참여 점수, (2)정보 공유 점수, (3)문제 해결 참여 점수, (4)주도적 제안 점수, (5)응답 속도 점수에 대해 각각 평가합니다.

        3.  **개인별 상세 분석 (Personal Analysis)**
            -   채팅에 참여한 모든 주요 인물을 찾아냅니다.
            -   각 참여자에 대해 아래 7가지 항목을 0~100점 척도로 평가하고 순위를 매깁니다.
                -   `참여도 점수 (participation)`: 메시지 빈도와 총량 기반.
                -   `정보 공유 점수 (infoshare)`: 새로운 정보, 자료, 링크 공유 기여도.
                -   `문제 해결 점수 (probsolve)`: 문제 상황에서 해결책이나 대안을 제시하는 기여도.
                -   `의견/아이디어 제시 점수 (proposal)`: 새로운 아이디어나 의견을 제시하는 기여도.
                -   `응답 속도 점수 (resptime)`: 다른 사람의 메시지에 얼마나 빠르고 적극적으로 반응하는지.
                -   `개인 분석 요약 (analysis)`: 각 참여자의 기여도에 대한 1 문장 요약.
                -   `담당자 유형 (type)`: 분석을 바탕으로 각 참여자를 '주도형', '분석형', '아이디어형', '지원형', '관망형' 중 하나로 분류.
            -   모든 점수를 합산하여 `종합 순위 (rank)`를 매깁니다.

        --- [출력 형식] ---
        결과는 반드시 아래 형식을 정확히 지켜서 작성해주세요.

        [전체 요약 분석]
        대화 주도자: [이름]
        평균 응답 속도(분): [숫자]
        AI 생성 인사이트: [1-2 문장]
        AI 추천 솔루션: [1-2 문장]
        ###
        [기간별 분석]
        ---
        이름: [참여자 이름]
        분석 종류: 종합 참여 점수
        period_1: [숫자]
        period_2: [숫자]
        period_3: [숫자]
        period_4: [숫자]
        period_5: [숫자]
        period_6: [숫자]
        ---
        이름: [참여자 이름]
        분석 종류: 정보 공유
        period_1: [숫자]
        period_2: [숫자]
        period_3: [숫자]
        period_4: [숫자]
        period_5: [숫자]
        period_6: [숫자]
        ---
        이름: [참여자 이름]
        분석 종류: 문제 해결 참여
        period_1: [숫자]
        period_2: [숫자]
        period_3: [숫자]
        period_4: [숫자]
        period_5: [숫자]
        period_6: [숫자]
        ---
        이름: [참여자 이름]
        분석 종류: 주도적 제안
        period_1: [숫자]
        period_2: [숫자]
        period_3: [숫자]
        period_4: [숫자]
        period_5: [숫자]
        period_6: [숫자]
        ---
        이름: [참여자 이름]
        분석 종류: 응답 속도
        period_1: [숫자]
        period_2: [숫자]
        period_3: [숫자]
        period_4: [숫자]
        period_5: [숫자]
        period_6: [숫자]
        ---
        (참여자 수만큼 반복)
        ###
        [개인별 상세 분석]
        ---
        이름: [참여자 이름]
        종합 순위: [숫자]
        담당자 유형: [유형]
        참여도 점수: [숫자]
        정보 공유 점수: [숫자]
        문제 해결 점수: [숫자]
        의견/아이디어 제시 점수: [숫자]
        응답 속도 점수: [숫자]
        개인 분석 요약: [1 문장]
        ---
        (참여자 수만큼 반복)
        ###

        --- [카카오톡 대화 내용] ---
        {chat_content_sample}
        --- [분석 시작] ---
        """

        # --- 단일 API 호출 ---
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[comprehensive_prompt]
        )
        response_text = response.text

        # --- 결과 파싱 ---    
        # 1. 전체 요약 분석 파싱 (Spec)
        summary_spec_text = parse_response(r"\[전체 요약 분석\]\n([\s\S]*?)\n###", response_text)
        summary_spec = {
            "total_talks": analysis_size, # 분석 메시지 수
            "leader": parse_response(r"대화 주도자:\s*(.+)", summary_spec_text),
            "avg_resp": parse_response(r"평균 응답 속도\(분\):\s*(\d+)", summary_spec_text, is_int=True),
            "insights": parse_response(r"AI 생성 인사이트:\s*(.+)", summary_spec_text),
            "recommendation": parse_response(r"AI 추천 솔루션:\s*(.+)", summary_spec_text)
        }

        # 2. 기간별 분석 파싱 (Period)
        periodic_text_block = parse_response(r"\[기간별 분석\]\n([\s\S]*?)\n###", response_text)
        periodic_specs = []
        if periodic_text_block:
            person_blocks = periodic_text_block.split('---')
            for block in person_blocks:
                if not block.strip(): continue
                periodic_specs.append({
                    "name": parse_response(r"이름:\s*(.+)", block),
                    "analysis_type": parse_response(r"분석 종류:\s*(.+)", block),
                    "period_1": parse_response(r"period_1:\s*(\d+)", block, is_int=True),
                    "period_2": parse_response(r"period_2:\s*(\d+)", block, is_int=True),
                    "period_3": parse_response(r"period_3:\s*(\d+)", block, is_int=True),
                    "period_4": parse_response(r"period_4:\s*(\d+)", block, is_int=True),
                    "period_5": parse_response(r"period_5:\s*(\d+)", block, is_int=True),
                    "period_6": parse_response(r"period_6:\s*(\d+)", block, is_int=True),
                })

        # 3. 개인별 상세 분석 파싱 (Personal)
        personal_text_block = parse_response(r"\[개인별 상세 분석\]\n([\s\S]*?)\n###", response_text)
        personal_specs = []
        if personal_text_block:
            person_blocks = personal_text_block.split('---')
            for block in person_blocks:
                if not block.strip(): continue
                personal_specs.append({
                    "name": parse_response(r"이름:\s*(.+)", block),
                    "rank": parse_response(r"종합 순위:\s*(\d+)", block, is_int=True),
                    "type": parse_response(r"담당자 유형:\s*(.+)", block),
                    "participation": parse_response(r"참여도 점수:\s*(\d+)", block, is_int=True),
                    "infoshare": parse_response(r"정보 공유 점수:\s*(\d+)", block, is_int=True),
                    "probsolve": parse_response(r"문제 해결 점수:\s*(\d+)", block, is_int=True),
                    "proposal": parse_response(r"의견/아이디어 제시 점수:\s*(\d+)", block, is_int=True),
                    "resptime": parse_response(r"응답 속도 점수:\s*(\d+)", block, is_int=True),
                    "analysis": parse_response(r"개인 분석 요약:\s*(.+)", block)
                })
            
            # 최종 결과 조합
            final_results = {
                "summary_spec": summary_spec,
                "periodic_specs": periodic_specs,
                "personal_specs": personal_specs,
            }

            final_results["num_chat"] = num_chat
            return final_results

    except Exception as e:
        print(f"Gemini로 기여도 상세 분석 중 에러 발생: {e}")
        # 함수 시그니처(-> dict)에 맞춰 에러 메시지를 딕셔너리로 반환
        return {"error_message": "기여도 상세 분석 중 오류가 발생했습니다."}
