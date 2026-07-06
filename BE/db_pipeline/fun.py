import os
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
# from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import datetime
import requests
from yt_dlp import YoutubeDL
from googletrans import Translator
from http.cookiejar import MozillaCookieJar
import yt_dlp
import whisper
from transformers import pipeline
import mysql.connector
from mysql.connector import Error
import requests
import time
import fun as fun
import math
import json
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
from Preprocess import Preprocess



import datetime
load_dotenv()  # .env 파일 로드
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")   
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")

model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
p = Preprocess(userdic='')
     
# 로깅 설정
logging.basicConfig(
    level=logging.INFO,  # 출력 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("fun.log", encoding='utf-8'),  # 파일 저장
        logging.StreamHandler()  # 콘솔 출력
    ]
)

def get_youtube_metadata(video_id, api_key=YOUTUBE_API_KEY):
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # 1. 비디오 상세 정보 요청 (메타데이터)
    video_request = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    )
    video_response = video_request.execute()
    if not video_response.get("items"):
        raise Exception("비디오 정보를 찾을 수 없습니다.")
    video_item = video_response["items"][0]
    
    # 2. 필요한 비디오 메타데이터 추출
    view_count    = int(video_item['statistics'].get('viewCount', 0))
    like_count    = int(video_item['statistics'].get('likeCount', 0))
    comment_count = int(video_item['statistics'].get('commentCount', 0))
    
    # 날짜 형식 변환 함수
    def convert_youtube_date(date_str):
        try:
            if date_str:
                dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return None
        except:
            return None

    video_title = remove_emojis(video_item['snippet']['title'])
    description = remove_emojis(video_item['snippet']['description'])
    logging.info(f"[정보] 전처러된 비디오 제목: {video_title}")
    logging.info(f"[정보] 전처리된 비디오 설명: {description[:300]}...")  # 처음 300자만 출력
    
    video_meta = {
        'video_id':      video_item['id'],
        'channel_id':    video_item['snippet']['channelId'],
        'video_title':   video_title,
        'description':   description,
        'upload_date':   convert_youtube_date(video_item['snippet']['publishedAt']),  # 변환된 형식
        'view_count':    view_count,
        'like_count':    like_count,
        'comment_count': comment_count
    }
    
    # 3. 채널 정보 요청
    channel_id = video_meta['channel_id']
    channel_request = youtube.channels().list(
        part="snippet,statistics",
        id=channel_id
    )
    channel_response = channel_request.execute()
    if not channel_response.get("items"):
        raise Exception("채널 정보를 찾을 수 없습니다.")
    channel_item = channel_response["items"][0]
    
    subscriber_count = int(channel_item['statistics'].get('subscriberCount', 0))
    total_channel_views = int(channel_item['statistics'].get('viewCount', 0))
    total_videos = int(channel_item['statistics'].get('videoCount', 0))
    video_link = f"https://www.youtube.com/watch?v={video_id}"
    
    # 채널 메타 추가
    video_meta.update({
        'channel_name':     channel_item['snippet']['title'],
        'subscriber_count': subscriber_count,
        'video_link':       video_link
    })
    
    # 4. 추가 계산 항목
    # 1) engagement_ratio: comment_count / view_count
    video_meta['engagement_ratio'] = comment_count / view_count if view_count > 0 else 0.0
    # 2) like_ratio: like_count / view_count
    video_meta['like_ratio'] = like_count / view_count if view_count > 0 else 0.0
    # 3) avg_view: 채널 평균 조회수 (총 채널 조회수 / 총 영상 개수)
    video_meta['avg_view'] = int(total_channel_views / total_videos) if total_videos > 0 else 0
    # 4) sub_view_ratio: avg_view / subscriber_count
    video_meta['sub_view_ratio'] = (video_meta['avg_view'] / subscriber_count) if subscriber_count > 0 else 0.0
    
    return video_meta


# yt-dlp로 오디오를 다운로드하고 Whisper로 텍스트 변환 후 오디오 파일을 삭제
def transcribe_audio_with_whisper(video_id, model, audio_dir="audios"):
    # 오디오 저장 폴더가 없으면 생성
    os.makedirs(audio_dir, exist_ok=True)
    #print("debug4")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    audio_path = os.path.join(audio_dir, f"{video_id}.m4a")
    print(f"debug5: {video_url} -> {audio_path}")
    # yt-dlp 옵션 설정 (오디오만 m4a 포맷으로 다운로드)
   
    
    if not os.path.exists(audio_path):
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': audio_path,
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        }
         
        # 1. 오디오 다운로드
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        #print("debug6")
        print(f"오디오 파일이 {audio_path}에 다운로드되었습니다.")
    
    
    # 2. Whisper로 텍스트 변환
    try:
        if os.path.exists(audio_path):
            print("[정보] Whisper로 오디오 텍스트 변환 중...")
            result = model.transcribe(audio_path, word_timestamps=True, fp16=False) # fp16=False는 호환성을 높여줍니다.
            # audio_text = result['text']
            print("[정보] Whisper로 오디오 텍스트 변환 완료")
            # 3. 처리 완료된 오디오 파일 삭제
            os.remove(audio_path)
            # 3) segment 단위로 시작·끝 시간과 함께 출력
            audio_text=""
            for seg in result["segments"]:
                start = format_timestamp(seg["start"])      # 시작 시간 (초)
                # end   = seg["end"]        # 종료 시간 (초)
                text  = seg["text"].strip()
                audio_text+=f"[{start}] {text}\n"
                # print(f"[{start:.0f}] {text}")
            return audio_text
        else:
            raise Exception ("오디오 파일 다운로드에 실패했습니다.")
    except Exception as e:
        print(f"🔴[오류] Whisper로 오디오 텍스트 변환 중 오류 발생: {e}")
        return ""



# 지정된 비디오 ID의 댓글을 수집하는 함수 (수정된 버전)
def get_video_comments(video_id, api_key=YOUTUBE_API_KEY, max_results=2000):
    """지정된 비디오 ID의 댓글을 페이지네이션을 통해 설정된 개수만큼 수집합니다."""
    comments = []
    youtube = build('youtube', 'v3', developerKey=api_key)
    next_page_token = None

    try:
        while True:
            # API 요청
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_results - len(comments), 100), # 남은 개수와 100개 중 작은 값으로 요청
                textFormat="plainText",
                pageToken=next_page_token # 다음 페이지 토큰 사용
            )
            response = request.execute()

            # 댓글 리스트에 추가
            for item in response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)

            # 다음 페이지 토큰 확인
            next_page_token = response.get('nextPageToken')

            # 다음 페이지가 없거나, 요청한 개수를 모두 채웠으면 루프 종료
            if not next_page_token or len(comments) >= max_results:
                break

        return comments

    except Exception as e:
        print(f"🔴댓글 수집 중 오류 발생: {e}")
        return comments # 오류 발생 전까지 수집된 댓글이라도 반환

 
def format_timestamp(seconds: float) -> str:
    """초 단위 float를 [HH:MM:SS] 문자열로 변환"""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

# def get_youtube_script(video_id: str):
#     print(f"\n--- [{video_id}] 영상 스크립트 수집 ---")
 
#     # 3-2. youtube-transcript-api로 자막 텍스트 수집
#     combined_text =""
#     try:
#         transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
#         combined_lines = []
#         for item in transcript_list:
#             ts = format_timestamp(item['start'])
#             text = item['text'].replace('\n', ' ')  # 혹시 줄바꿈이 있으면 한 줄로
#             combined_lines.append(f"[{ts}] {text}")
#         result = "\n".join(combined_lines)
#         combined_text += "\n" + result
#         print(f"[성공] 자막 텍스트 수집 완료 (총 {len(result)}자, {len(transcript_list)}줄)")
#     except Exception as e:
#         print(f"[정보] 자막 없음 또는 수집 실패: {e}")
#     return combined_text



def load_json_list_from_file(file_path):
    """
    JSON 파일에서 리스트 형식의 데이터를 읽어옵니다.

    Args:
        file_path (str): JSON 파일 경로

    Returns:
        list: JSON 파일에서 읽은 리스트 데이터
    """
    if not os.path.exists(file_path):
        print(f"⚠️ 파일이 존재하지 않습니다: {file_path}")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                print("❌ JSON 파일의 최상단 구조가 리스트가 아닙니다.")
                return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON 디코딩 오류: {e}")
        return []
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        return []

def calculate_base_video_score(view_count, like_count, comment_count, subscriber_count):
    """영상의 기본 점수(인지도, 참여도, 신뢰도)를 계산합니다."""
    # 로그 스케일링으로 값의 범위를 줄여 균형을 맞춤
    popularity_score = (math.log10(view_count + 1) * 0.2) + (math.log10(like_count + 1) * 1.0)
    engagement_score = (math.log10(comment_count + 1) * 1.5)
    channel_score = math.log10(subscriber_count + 1) * 0.3
    
    base_score = popularity_score + engagement_score + channel_score
    return base_score


def calculate_restaurant_script_score(restaurant_name, scripts, sentiment_pipeline):
    # 특정 맛집에 대한 스크립트의 감성 분석을 통해 리뷰 점수를 계산합니다.
    script_score = 0
    positive_review_count = 0
    
    if restaurant_name is None or not scripts:
        logging.warning(f"[경고] 맛집 이름이 없거나 스크립트가 비어있습니다: {restaurant_name}")
        return 0

    logging.info(f"{restaurant_name} : {scripts[:30]}...")  # 스크립트의 처음 30자만 출력
    logging.info(f"[정보] 스크립트 감성 분석 시작")
    try:
        # 감성 분석 수행
        result = sentiment_pipeline(scripts)[0]
        # ★★★ 디버깅을 위한 출력 코드 ★★★
        # 모델이 실제로 어떤 label과 score를 반환하는지 확인합니다.
        logging.info(f"  [디버그] 스크립트: \"{scripts[:30]}...\" >> 모델 결과: {result}")
        # 'positive' 레이블일 경우 점수를 더함
        if result['label'].upper() == '1':
            script_score = result['score']
            return script_score
            
    except Exception as e:
        print(f"감성 분석 중 오류 발생: {e}")
 
    # # 긍정 리뷰가 있었다면, 평균 점수를 반환하여 리뷰 개수에 따른 왜곡을 줄임
    # if positive_review_count > 0:
    #     return review_score / positive_review_count
    
    return 0

def is_contain_restaurant_name(restaurant_name, restaurant_name_embedding, comment):
    pos = p.pos(comment)
    keywords = p.get_keywords(pos, without_tag=True)
    
    if not keywords:
        return False  # 빈 리스트는 비교 생략

    token_embeddings = model.encode(keywords)
    # 4. 코사인 유사도 계산
    cos_sims = cosine_similarity(token_embeddings, restaurant_name_embedding)  # shape: (len(tokens), 1)
    # print("target :", restaurant_name)
    # print("token :", keywords)
    # 5. 결과 출력
    for token, sim in zip(keywords, cos_sims):
        # print(f"  [디버그] '{token}' vs '{restaurant_name}' 유사도: {sim[0]:.4f}")
        # input()
        if sim[0] >= 0.75:
            print(comment)
            print(f"@@@@@@@@@@@@{token} vs {restaurant_name} similarity: {sim[0]:.4f}")
            input()
            found_similar = True
            break
    else:
        found_similar = False  # for문이 break 없이 끝난 경우

    return found_similar
    
    
def calculate_restaurant_review_score(restaurant_name, comments, sentiment_pipeline):

    review_score = 0
    positive_review_count = 0
    valid_comment_count = 0
    
    positive_scores = []
    negative_scores = []
    
    if not restaurant_name:
        return 0

    # restaurant_name_embedding = model.encode([restaurant_name])  # 2D로 유지
    MAX_TOKEN_LENGTH = 512  # 모델이 처리할 수 있는 최대 토큰 길이
    for comment in comments:
        # 댓글 길이 제한
        if len(comment) > MAX_TOKEN_LENGTH:
            comment = comment[-MAX_TOKEN_LENGTH:]  # 초과하는 경우 잘라냄

        # logging.info(f"{restaurant_name} : {comment}")
        # is_contain = is_contain_restaurant_name(restaurant_name, restaurant_name_embedding, comment)
        is_contain = restaurant_name in comment  # 간단한 문자열 포함 여부 확인
        if is_contain: # 댓글에 맛집 이름이 언급되었는지 확인
            # logging.info(f"[@정보@] '{restaurant_name}'이(가) 언급된 댓글 발견: {comment[:30]}...")
            try:
                # 감성 분석 수행
                result = sentiment_pipeline(comment)[0]
                label = result['label']
                score = result['score']
                # print(f"[정보] 댓글 감성 분석 결과: {label} (score: {score:.4f})")
                # input()
        
                valid_comment_count += 1
                
                # print(f"  [디버그] 댓글: \"{comment[:30]}...\" >> 모델 결과: {result}")
                # logging.info(f"  [디버그] 댓글: \"{comment[:30]}...\" >> 모델 결과: {result}")
              
                if label =='1':
                    positive_scores.append(score)
                elif label == '0':
                    negative_scores.append(score)
                # print(f"positive_scores: {positive_scores} negative_scores: {negative_scores}")
                    
            except Exception as e:
                print(f"감성 분석 중 오류 발생: {e}")

    print(f"[정보] 전체 댓글 수: {len(comments)} 유효한 댓글 수: {valid_comment_count}")
    pos_count = len(positive_scores)
    neg_count = len(negative_scores)
    total_count = pos_count + neg_count
    # print(f"[정보] 긍정 리뷰: {pos_count}, 부정 리뷰: {neg_count}, 총 리뷰: {total_count}")

    if total_count == 0:
        return 0.5  # 예외처리: 긍/부정이 하나도 없으면 중립으로 간주

    avg_pos = sum(positive_scores) / pos_count if pos_count > 0 else 0
    avg_neg = sum(negative_scores) / neg_count if neg_count > 0 else 0

    positive_percent = (((pos_count * avg_pos) - (neg_count * avg_neg)) / total_count + 1) / 2 # 0~1 사이로 정규화
    return positive_percent          


def get_kakao_geocode(query: str, kakao_api_key: str):
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    params = {"query": query}
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    print(f"  [좌표 검색 쿼리] '{query}'")
    
 
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        result = res.json()
        print("  [좌표 검색 결과] :", result["documents"][0])
        if result["documents"]:
            top = result["documents"][0]
            return {
                "name": top["place_name"],
                "address": top.get("road_address_name") or top.get("address_name"),
                "lat": float(top["y"]),
                "lng": float(top["x"])
            }
        else:
            return None
 
    except Exception as e:
        print(f"[Kakao API 오류] '{query}' 요청 실패: {e} | status_code: {getattr(res, 'status_code', 'N/A')}")
        print(res.text if 'res' in locals() else "No response object")
        return None
    
## 결과 검증 함수들


def find_nearby_restaurants(lat, lng, radius=50):
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "category_group_code": "FD6",
        "x": lng,
        "y": lat,
        "radius": radius,
        "sort": "distance"
    }

    res = requests.get(url, headers=headers, params=params)

    if res.status_code == 200:
        documents = res.json().get("documents", [])
        if not documents:
            return []  # 바로 빈 리스트 반환
        return [
            {
                "name": doc["place_name"],
                "address": doc["road_address_name"] or doc["address_name"],
                "distance": doc["distance"]
            }
            for doc in documents
        ]
    else:
        print(f"[ERROR] {res.status_code}: {res.text}")
        return []

def normalize(text):
    return text.lower().replace(" ", "").strip()

def cosine_name_similarity(name1, name2):
    vectorizer = TfidfVectorizer().fit([name1, name2])
    tfidf_matrix = vectorizer.transform([name1, name2])
    similarity = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])
    return float(similarity[0][0])  # similarity 값은 0 ~ 1 사이

def is_match_kakao_vs_known(kakao_name, known_name):
    n_kakao = normalize(kakao_name)
    n_known = normalize(known_name)
    return n_kakao in n_known or n_known in n_kakao  # 포함 여부 

def remove_emojis(text):
    # 텍스트가 None이거나 비어있는 경우 처리
    if not text:
        return ""
    
    # DB 입력시 불필요한 이모지 또는 특수 문자로 인한 오류를 방지하기 위해
    # 이모지를 제거하고, 한글, 영어, 숫자, 기본 기호는 보존하는 함수
    import re
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        
        # 이모지만 정확하게 타겟팅하여 제거 (한글, 영어, 숫자, 기본 기호는 보존)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 감정 이모티콘
            "\U0001F300-\U0001F5FF"  # 기호 및 그림문자
            "\U0001F680-\U0001F6FF"  # 교통 및 지도 기호
            "\U0001F700-\U0001F77F"  # 연금술 기호
            "\U0001F780-\U0001F7FF"  # 기하학적 모양 확장
            "\U0001F800-\U0001F8FF"  # 보조 화살표-C
            "\U0001F900-\U0001F9FF"  # 보조 기호 및 그림문자
            "\U0001FA00-\U0001FA6F"  # 체스 기호
            "\U0001FA70-\U0001FAFF"  # 기호 및 그림문자 확장-A
            "\U0001F1E0-\U0001F1FF"  # 국기
            "\u200d"                 # 제로 폭 결합자
            "\ufe0f"                 # 변형 선택자
            "]+", 
            flags=re.UNICODE
        )
        
        # 이모지 제거
        cleaned_text = emoji_pattern.sub('', text)
        
        # 불필요한 공백 제거
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # 한글, 영어, 숫자, 기본 기호는 유지
        cleaned_text = re.sub(r'[^\w\s가-힣.,!?<>:;\'\"()\[\]{}\-]', '', cleaned_text)
        
        return cleaned_text.strip()
        
    except Exception as e:
        print(f"[에러] 이모지 제거 중 오류: {e}")
        # 에러 발생 시 기본적인 정리만 수행
        return re.sub(r'[^\w\s가-힣]', ' ', str(text))