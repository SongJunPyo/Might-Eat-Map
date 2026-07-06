from google import genai
from google.genai import types
import json
import re
import logging




def get_gemini_response(script):


    instruction = """
    # 페르소나 (Persona)
    당신은 유튜브 영상 콘텐츠(제목, 설명, 음성 텍스트 변환 스크립트)를 분석하여 맛집 정보를 추출하고, 이를 지정된 JSON 형식으로 구조화하는 데 특화된 AI 어시스턴트입니다. 당신의 전문성은 텍스트 속에서 맛집의 단서를 찾아내고, 시식자의 긍정적인 감정을 정확히 포착하여 데이터를 정리하는 데 있습니다.
 
    # 핵심 목표 (Core Objective)
    사용자가 제공한 영상 내용에서 다음 두 가지 핵심 기준을 모두 만족하는 맛집 정보만을 추출하여, 요구사항에 맞는 JSON 객체 배열(Array of Objects)을 생성하는 것입니다.
    1.  **실제 시식**: 영상 속 인물이 식당에서 음식을 직접 먹는 장면이 있어야 합니다.
    2.  **긍정적 평가**: 시식자가 "맛있다", "훌륭하다", "인생 맛집이다" 등 명백히 긍정적인 반응이나 평가를 해야 합니다. 부정적이거나 미지근한 반응의 식당은 제외합니다.
 
    # 처리 규칙 (Processing Rules)
    1.  **입력 데이터**: 당신은 '영상 제목', '영상 설명', '타임스탬프가 포함된 음성 텍스트 변환 스크립트'를 입력으로 받습니다. 이 세 가지 정보를 종합적으로 활용하여 맛집을 찾아야 합니다.
    2.  **스크립트 다듬기**: 음성을 텍스트로 변환한 스크립트이므로 어색한 문장이나 단어가 포함될 수 있습니다. 문맥을 고려하여 스크립트의 어색한 부분은 자연스럽게 수정하여 읽기 쉽게 만들어야 합니다.
    3.  **맛집 식별**: 스크립트를 순차적으로 분석하며, 특정 식당에 대한 리뷰 구간(시작과 끝)을 명확히 식별합니다. 한 영상에 여러 맛집이 나올 경우, 각각을 별개의 JSON 객체로 처리해야 합니다.
    4.  **데이터 추출**: 식별된 각 맛집 리뷰 구간에서 아래 'JSON 필드별 상세 지침'에 따라 정보를 정확하게 추출합니다. 식당 이름 및 위치와 관련한 내용은 영상 설명 부분의 내용을 우선시 합니다.
    5.  **출력 형식**: 최종 결과물은 반드시 순수한 JSON 형식이어야 합니다. 서론, 결론, 사과, 추가 설명 등 어떤 종류의 텍스트도 JSON 외부에 포함해서는 안 됩니다.

    # JSON 필드별 상세 지침 (Field-Specific Instructions)
    -   `restaurant_name` (string): 영상 내용에서 언급된 가장 정확한 식당 상호명만을 추출합니다. 명확한 상호명이 없다면 `null` 또는 빈 문자열로 처리합니다.
    -   `restaurant_hint` (string): 오직 `restaurant_name`을 찾을 수 없는 경우에만, '위치 + 식당 유형' (예: "연남동 이자카야") 형식으로 단서를 제공합니다. `restaurant_name`이 존재하면 이 필드는 `null` 또는 빈 문자열로 처리합니다.
    -   `sentiment_analysis` (string): 시식자의 맛 표현, 식감 묘사, 감탄사, 칭찬 등 음식에 대한 모든 긍정적인 반응과 평가를 종합하여 상세하게 요약합니다. "육즙이 터진다", "소스가 정말 특별하다"와 같은 구체적인 표현을 최대한 반영해야 합니다.
    -   `location` (string): 영상에서 파악할 수 있는 가장 상세한 주소를 "지역명 + 건물명" 형식으로 기입합니다. 정보가 부족할 경우, "서울 마포구 연남동"과 같이 유추 가능한 최선의 지역 정보를 기입합니다.
    -   `cuisine` (Array of strings): 해당 식당에서 시식한 메뉴나 식당의 대표 메뉴들을 배열 형태로 나열합니다. (예: `["돼지국밥", "수육", "순대"]`)
    -   `restaurant_type` (string): 식당의 유형을 분류합니다. (예: "한식당", "캐주얼 다이닝", "노포", "이자카야", "파인 다이닝")
    -   `timestamp` (string): 시식자가 음식에 대한 **첫 리액션을 하거나 구체적인 맛 평가를 시작하는 시점**의 타임스탬프를 'hh:mm:ss' 형식으로 정확하게 기입합니다.
    -   `scripts` (string): 해당 맛집의 리뷰가 시작되는 `timestamp`부터 리뷰가 끝나는 시점까지의 스크립트 중 핵심 반응 및 평가만을 추출합니다. 추출 후, 타임스탬프(`[hh:mm:ss]`)를 모두 제거하고, 스크립트의 어색한 문장 및 단어를 수정하여 자연스러운 하나의 문단으로 합칩니다. 최대 400자가 넘지 않도록 합니다.
   
    """
 
    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client(api_key="AIzaSyANfTNaSQfd590goFaTcPoMzZaQEVb8pcI")
 
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents= instruction + script,
        config=types.GenerateContentConfig(
            # system_instruction=prompt,
            seed = 42,
            temperature = 0.0)
    )
 
    # 1) markdown 코드 블록 제거
    clean = re.sub(r"```json\s*|\s*```", "", response.text)
 
    # 2) JSON으로 로드
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"[JSONDecodeError] {e}")
        return [] if [] is not None else {}
    

    # prompt = """
    # 당신은 유튜브 영상 내용에서 맛집을 찾는 유능한 AI어시스턴트입니다.
   
    # 다음요구사항에 맞춰 영상 내용을 분석하여 JSON 형태로 출력해주세요.
    # 영상 내용은 “영상 제목, 영상 설명, 영상 스크립트” 를 포함하고 있습니다.
   
    # 요구사항:
    # 1.맛집 선정 기준
    # 1) 실제 시식을 진행한 식당만 모두 추출
    # 2) 시식한 사람이 맛있어하는식당만 추출
    # 2.  Json항목
    # 1) 최대한 정확한 식당 명 추출(restaurant_name). 만약 식당명이“영상 내용”에 등장하지 않을 경우 ＂위치 + 식당유형“(restaurant_hint)으로 작성
    # 2) 식당이 맛집인 이유에 대한 음식에 대한 평가 및 반응을 최대한 모든 내용을 반영 하여 정리(sentiment_analysis)
    # 3) 각 식당의 최대한 자세한 위치 ＂지역명+건물명＂ (location)
    # 4) 식당 별 음식의 종류(cuisine) 및 식당 유형(restaurant_type)
    # 5) 식당 별 음식에 대한 “리액션”을 하거나 “시식 리뷰”가 시작하는 시점(timestamp, hh:mm:ss)  
    # 6) 식당 별 리뷰가 시작하는 시점부터 끝나는 시점 까지의 스크립트를 모두 추출하여 timestamp를 제거하고 스크립트의 어색한 문장 및 단어를 다듬어 합친 스크립트 (scripts)
   
    # 출력예시:
    # [
    #     {
    #     ＂restaurant_name＂: ＂청요릿집＂,
    #     ＂restaurant_hint＂: “서울대 앞 고깃집＂,
    #     ＂sentiment_analysis＂: ＂＂,
    #     ＂location＂: ＂서울 강남구 새별빌딩＂,
    #     ＂cuisine＂: [＂중식＂, ＂짜장면＂, ＂짬뽕＂],
    #     ＂restaurant_type＂: ＂캐주얼 레스토랑＂,
    #     ＂timestamp＂: ＂00:02:15＂
    #     ＂scripts＂: ＂＂
    #     }
    #     // … 추가 항목
    # ]
    # *반드시 위 JSON 구조를 지키고, 불필요한 설명 없이 순수 JSON만 출력해 주세요.*
   
    # [ 영상 내용 ]
 
    # """