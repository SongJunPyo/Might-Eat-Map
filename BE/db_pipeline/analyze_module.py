

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
import gemmini
import datetime

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
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")         # 네이버 클라우드 API 클라이언트 ID
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET") # 네이버 클라우드 API 클라이언트 시크릿
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
            # # 받아온 데이터를 video_data 객체에 업데이트
            # video_data['channel_id'] = video_meta.get('channel_id')
            # video_data['view_count'] = video_meta.get('view_count', 0)
            # video_data['like_count'] = video_meta.get('like_count', 0)
            # video_data['comment_count'] = video_meta.get('comment_count', 0)
            # video_data['subscriber_count'] = video_meta.get('subscriber_count', 0)

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
            save_path = f"whisper_output/{video_id}.txt" 
            # 해당 영상의 음성 텍스트가 이미 존재하는지 확인
            #if not os.path.exists(save_path):
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
            # else :
            #     # 이미 저장된 텍스트 파일이 있다면 불러오기
            #     with open(save_path, "r", encoding="utf-8") as f:
            #         whisper_text = f.read()
            #     combined_text += whisper_text
            #     print(f"[정보] 이미 저장된 Whisper 텍스트 사용: {save_path}")
            #     print(f"내용 : {whisper_text[:100]}...")  # 처음 100자만 출력
        except Exception as e:
            print(f"🔴[실패] 음성 처리 실패: {e}")
            return (None, None)

        try:
            save_path = f"gemini_output/{video_id}_output.txt"
            #if not os.path.exists(save_path):
            validated_restaurants = gemmini.get_gemini_response(combined_text)                
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
            # else:
            #     # 이미 저장된 텍스트 파일이 있다면 불러오기
            #     with open(save_path, "r", encoding="utf-8") as f:
            #         validated_restaurants = json.load(f)
            #     print(f"[정보] 이미 저장된 gemini 출력 사용: {save_path}")
            #     print(f"내용 : {validated_restaurants[:3]}...")  # 처음 3개만 출력
                
        except Exception as e:
            print(f"🔴[실패] 음성 텍스트 gemini 처리 실패: {e}")
            return (None, None)

        # print(f"[{video_id}] 영상의 기본 점수 및 맛집별 리뷰 점수를 계산합니다...")
        # # 5-1. 영상의 '기본 점수' 계산
        # base_score = fun.calculate_base_video_score(
        #     video_meta['view_count'],
        #     video_meta['like_count'],
        #     video_meta['comment_count'],
        #     video_meta['subscriber_count']
        # )
        # print(f"  - 영상 기본 점수: {base_score:.2f}")
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
                'final_score': ((comment_score+script_score+video_meta['engagement_ratio']+video_meta['like_ratio']+video_meta['sub_view_ratio'])/5),
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
                
        