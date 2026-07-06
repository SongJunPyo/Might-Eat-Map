

import os
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import whisper
from transformers import pipeline
import mysql.connector
from mysql.connector import Error
import requests
import time
import json
import logging
import fun as fun
#import youtube_video_collect as collect_fun
from db_manager import db_manager
import datetime
from google import genai
from google.genai import types
import re




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
    
# 로깅 설정
logging.basicConfig(
    level=logging.INFO,  # 출력 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),  # 파일 저장
        logging.StreamHandler()  # 콘솔 출력
    ]
)

load_dotenv()  # .env 파일 로드

# --- 1. 전역 설정 및 모델 로딩 ---
# API 키 환경변수에서 로드
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")         # YouTube Data API 키
KAKAO_API_KEY = os.environ.get("KAKAO_REST_API_KEY")

# AI 모델들 미리 로딩 (GPU 사용)
print("AI 모델을 로딩합니다...")
stt_model = whisper.load_model("medium", device="cuda")       # sst 모델 (Whisper)
sentiment_pipeline = pipeline("text-classification", model="daekeun-ml/koelectra-small-v3-nsmc", device=0) # KoELECTRA 기반 맛집 리뷰 문장 평가 모델 ('조회수'나 '좋아요' 수만으로 맛집을 찾는 것과 차별화되는 핵심적인 이유)

class Analyze_module:
    def valid_location(self,gem_dict):
        # 유효한 위치인지 확인하는 함수
        # 유효하면 True, 아니면 False DB에 is_valid_location 컬럼에 저장
       
        verify_results = fun.find_nearby_restaurants( gem_dict["latitude"],gem_dict["longitude"])
        if verify_results:
            if verify_results[0]["name"] and gem_dict['gem_name']:
                matched = fun.is_match_kakao_vs_known(verify_results[0]["name"], gem_dict['gem_name'])
                print(f"{verify_results[0]['name']} | {verify_results[0]['address']} | {verify_results[0]['distance']}")
                print("일치 여부:", matched)
                return matched # 일치 여부 반환
        
        return False # 주변 음식점이 없거나 일치하지 않으면 False 반환
    
    def get_analyze_dict(self, video_id):
        #video_id = "zrLdC7aYy64"
        #video_id = video_data['video_id'] # 현재 처리 중인 영상 ID
        print(f"\n--- [{video_id}] 영상 분석 시작 ---")
        combined_text = ""
        

        # 3-1. 유튜브 API로 제목, 설명, 메타데이터 수집
        try:
            # get_youtube_metadata 함수를 호출하여 비디오와 채널 정보를 한 번에 받아옵니다.
            video_meta = fun.get_youtube_metadata(video_id)
            print("video_meta: ", video_meta)

            # 통합 텍스트 변수 초기화
            combined_text += video_meta.get('video_title', '') + "\n" + video_meta.get('description', '')
            print(f"[성공] 제목/설명 수집 완료: {video_meta['video_title']}")
        except Exception as e:
            print(f"[실패] 유튜브 API 호출 실패: {e}")
            return  (None, None)  # 이 영상은 처리 불가, 다음 영상으로


        # 3-2. 댓글 텍스트 수집
        print("댓글을 수집합니다...")
        video_comments = fun.get_video_comments(video_id, YOUTUBE_API_KEY)
        print(f"[성공] {len(video_comments)}개의 댓글 수집 완료")
                

        # 3-4. Whisper로 음성 텍스트 수집
        whisper_text = ""
        try:
            save_path = f"/home/super/2025_hackathon/db_pipeline/whisper_output/{video_id}.txt" 
            # 해당 영상의 음성 텍스트가 이미 존재하는지 확인
            if not os.path.exists(save_path):
                # transcribe_audio_with_whisper 함수를 호출합니다.
                whisper_text = fun.transcribe_audio_with_whisper(video_id, stt_model)
                if whisper_text == "" :
                    print(f"🔴[실패] 음성 텍스트 변환 실패: {e}")
                    return (None, None)
                logging.info(whisper_text[:300])  # 처음 300자만 로그에 남김
                combined_text += whisper_text
                
                # ✅ 텍스트 파일로 저장
                
                os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 폴더 없으면 생성
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(whisper_text)
                print(f"[저장 완료] Whisper 텍스트: {save_path}")
                
                print("[성공] 음성 텍스트 변환 완료")
            else :
                # 이미 저장된 텍스트 파일이 있다면 불러오기
                with open(save_path, "r", encoding="utf-8") as f:
                    whisper_text = f.read()
                combined_text += whisper_text
                print(f"[정보] 이미 저장된 Whisper 텍스트 사용: {save_path}")
                print(f"내용 : {whisper_text[:100]}...")  # 처음 100자만 출력
        except Exception as e:
            print(f"🔴[실패] 음성 처리 실패: {e}")
            return (None, None)

        try:
            save_path = f"/home/super/2025_hackathon/db_pipeline/gemini_output/{video_id}_output.txt"
            #if not os.path.exists(save_path):
            validated_restaurants = get_gemini_response(combined_text)                
            print(f"gemmini: {validated_restaurants}")
            # validated_restaurants를 텍스트 파일로 저장하는 코드
            if validated_restaurants:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 폴더 없으면 생성
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(validated_restaurants, f, ensure_ascii=False, indent=4)
                print(f"[저장 완료] gemini 출력: {save_path}")

            if not validated_restaurants:
                print(f"[{video_id}] 영상에서 검증된 맛집 후보를 찾지 못했습니다.")
                return (None, None)
            else:
                # 이미 저장된 텍스트 파일이 있다면 불러오기
                with open(save_path, "r", encoding="utf-8") as f:
                    validated_restaurants = json.load(f)
                print(f"[정보] 이미 저장된 gemini 출력 사용: {save_path}")
                print(f"내용 : {validated_restaurants[:3]}...")  # 처음 3개만 출력
                
        except Exception as e:
            print(f"🔴[실패] 음성 텍스트 gemini 처리 실패: {e}")
            return (None, None)

        DB_dicts =[]
        final_restaurant_scores = []
        # 5-2. 검증된 맛집별로 루프를 돌며 리뷰 점수 추가 및 최종 점수 계산
        for restaurant in validated_restaurants:
            #print(restaurant)
            if not restaurant.get("restaurant_name"):
                print(f"🔴경고] 맛집 이름이 없습니다. 건너뜁니다.")
                continue
            elif not restaurant.get("scripts"):
                print(f"🔴[경고] 맛집 '{restaurant['restaurant_name']}'의 스크립트가 없습니다. 건너뜁니다.")
                continue
            
            name = restaurant["restaurant_name"]
            
            
            # 5-2-1. 맛집별 '리뷰 점수' 계산
            comment_score = fun.calculate_restaurant_review_score(name, video_comments, sentiment_pipeline)
            script_score = fun.calculate_restaurant_script_score(name, restaurant['scripts'], sentiment_pipeline)
            
            
            if script_score == 0 : continue # 리뷰 점수가 0이면 해당 맛집은 제외
            if comment_score == 0 : continue # 리뷰 점수가 0이면 해당 맛집은 제외
            

            #final_score = base_score + (script_score * review_weight)
            
            # print(f"  - 맛집 '{name}': 리뷰 점수={script_score:.2f}, 최종 점수={final_score:.2f}")

            # 5-2-3. 최종 결과를 리스트에 저장
            new_restaurant = {
                'restaurant_name': name,
                'video_id': video_id,
                'video_title': video_meta['video_title'],
              
                'scripts':restaurant['scripts'],
                'gem_type' : restaurant['restaurant_type'],
                'recommend_reason' : restaurant['sentiment_analysis'],
                'start_timestamp' : restaurant['timestamp'],
                'category' :restaurant['cuisine'],
                'location':restaurant['location'],
                'comment_score': comment_score,
                'script_score': script_score,
                'final_score': 0, # 임시값, 나중에 계산
            }
            
            # restaurant_hint가 존재하면 추가
            if 'restaurant_hint' in restaurant:
                new_restaurant['restaurant_hint'] = restaurant['restaurant_hint']
            
            final_restaurant_scores.append(new_restaurant)

        print(f"\n[{video_id}] 동영상 분석 완료.")

        # --- 최종 결과 확인 ---
        # print("\n--- 최종 맛집별 점수 순위 ---")
        # sorted_restaurants  = sorted(final_restaurant_scores, key=lambda x: x['final_score'], reverse=True) # 점수가 높은 순으로 정렬하여 출력

        # for video in sorted_videos:
        #     print(f"ID: {video['video_id']}, Score: {video['score']:.2f}, 조회수: {video['view_count']}, 구독자: {video['subscriber_count']}, 좋아요: {video['like_count']}, 댓글: {video['comment_count']}")

        # print("영상 식당 개수: ", len(sorted_restaurants))
        for restaurant in final_restaurant_scores :
            print(
                f"스크립트 점수: {restaurant['script_score']:.2f} \n "
                f"맛집명: {restaurant['restaurant_name']} \n "
                f"등장 영상: {restaurant['video_title']} \n"
            )
            #print("restaursnt:")
            #print(restaurant)
            # validated_restaurants = {}  # {'상호명': {'lat': 위도, 'lng': 경도, 'address': 주소}}
            #location_context = restaurant.location'] or '' # 지역명 넣으면 정확도 상승
            #restraurant_name = restaurant['restaurant_name']  or ''
            
            location_context = restaurant.get('location') or ''
            restaurant_name = restaurant.get('restaurant_name') or ''

            query = location_context + " " + restaurant_name
            
            coords =fun.get_kakao_geocode(query, KAKAO_API_KEY)
        
            if coords:
                print(f"  [검색 성공] '{query}' → 좌표: ({coords['lat']}, {coords['lng']}) | 주소: {coords['address']}")
                # GEM 데이터베이스에 저장할 딕셔너리 생성
                DB_dict = {
                    'video_id': video_id,
                    'gem_name': restaurant['restaurant_name'],
                    'gem_type' : restaurant['gem_type'],
                    'recommend_reason' : restaurant['recommend_reason'],
                    'start_timestamp' : restaurant['start_timestamp'],
                    'category' : ", ".join(restaurant["category"]) if isinstance(restaurant["category"], list) else restaurant["category"],
                    'latitude': coords['lat'],
                    'longitude' : coords['lng'],
                    'address':  coords['address'],
                    'script_score' : restaurant['script_score'],
                    'comment_score':restaurant['comment_score'], # 임시값
                    'final_score': restaurant['final_score'], #임시값
                    'scripts':restaurant['scripts'],
                    'location':restaurant['location'],
                    'collect_date':datetime.datetime.now().isoformat()

                }
                
                # restaurant_hint가 존재하면 추가
                if 'restaurant_hint' in restaurant:
                    DB_dict['restaurant_hint'] = restaurant['restaurant_hint']
                DB_dicts.append(DB_dict)
                
            else:
                print(f"  [검색 실패] '{query}' → 좌표 없음")
        # --- 최종 결과 저장 ---
        if not DB_dicts:
            print(f"🟡[{video_id}] 영상에서 유효한 맛집을 찾지 못했습니다.")
            return (None, video_meta)  # 유효한 맛집이 없으면 None 반환
        else:
            print(f"🟢[{video_id}] 영상에서 {len(DB_dicts)}개의 유효한 맛집을 찾았습니다.")
            return (DB_dicts, video_meta)
                
        