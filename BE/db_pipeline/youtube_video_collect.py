

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
import fun as fun
import json
import logging
import youtube_video_collect as collect_fun

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,  # 출력 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("youtube_video_collect.log", encoding='utf-8'),  # 파일 저장
        logging.StreamHandler()  # 콘솔 출력
    ]
)

load_dotenv()  # .env 파일 로드

# --- 1. 전역 설정 및 모델 로딩 ---
# API 키 환경변수에서 로드
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")         # YouTube Data API 키
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")         # 네이버 클라우드 API 클라이언트 ID
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET") # 네이버 클라우드 API 클라이언트 시크릿

# --- 2. 분석 대상 동영상 ID 목록(유튜브 API로 불러오기) ---
def get_all_videos_from_channel(channel_id, max_results=9999):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        # 채널 → 업로드 재생목록 ID 가져오기
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()

        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 재생목록 기반으로 영상 수집
        video_ids = []
        next_page_token = None

        while True:
            playlist_response = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            video_ids += [item["contentDetails"]["videoId"] for item in playlist_response["items"]]

            next_page_token = playlist_response.get("nextPageToken")
            if not next_page_token or len(video_ids) >= max_results:
                break

        return video_ids

    except Exception as e:
        logging.error(f"[오류] 채널 전체 영상 수집 실패 (channel_id: {channel_id}): {e}")
        return []


def get_videos_from_playlist(playlist_id, max_results=9999):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        video_ids = []
        next_page_token = None

        while True:
            request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            video_ids += [item['contentDetails']['videoId'] for item in response['items']]

            next_page_token = response.get('nextPageToken')
            if not next_page_token or len(video_ids) >= max_results:
                break

        return video_ids
    except Exception as e:
        logging.error(f"[오류] 재생목록 전체 수집 실패 (playlist_id: {playlist_id}): {e}")
        return []

def youtube_video_collect(search_keyword):
    
    # 일반 채널 목록 (채널 전체 영상 대상)
    channel_search_targets = {
        #"UCIP3hSJruPL4dIi95lsuCZA": "홍석천이원일",
        # "UCLwCHoQ9h7DPXvLwx5XwTQg": "먹보스 쭈엽이",
        # "UCQA89gPDjJ-1M1o9bwdGF-g": "맛있겠다 Yummy"
    }

    # 재생목록 기반 채널 목록
    playlist_search_targets = {
        # "PL8ZmFxF9Ts5yZY-RlNAG51MqkURwYBBk5": "또간집",
        # "PLuMuHAJh9g_Py_PSm8gmHdlcil6CQ9QCM" : "성시경 - 먹을텐데",
        "PLt9IaFYitbwgXP5BN8pBUlm8R-XBnAp09" : "홍석천 이원일 - 줄서는 맛집 앞",
        "PLlP0KGgSpfBqN7qmqr2oP8GqrntjEsA46" : "용티의 푸드트립 - 부산",
        "PL2iYoYVt-EboXriT9iekHRzhcRqYhEBz5" : "이장우 - 살찐맛집",
        "PLWoGc25qzA3uNHuMdjiRyYJVVY-_Yq3TA": "최자로드 시즌 7",
        "PLWoGc25qzA3tSRZKQVLoE7NEcUfQFaMLN": "최자로드 시즌 8",
        "PLWoGc25qzA3tAoQ3-7uAt7ZywMAMwbPPK": "최자로드 시즌 9",
        
        # "PLt9IaFYitbwgPg1ZmF26f7prXIY13IUQc" : "홍석천 이원일 - 미식은 경험이다"
        # "PLWoGc25qzA3tNkDJ6_RQzsTemA4RFcScb": "최자로드 시즌 1",
        # "PLWoGc25qzA3vthfzjd7LAS24_A58iIKZv": "최자로드 시즌 2",
        # "PLWoGc25qzA3s__HwGKJphyLl_KZTEwYGS": "최자로드 시즌 3",
        # "PLWoGc25qzA3vAvOy52DJN7vco_jkU0cV2": "최자로드 시즌 4",
        # "PLWoGc25qzA3vRoh0umDUCk3FnWjk6IKhF": "최자로드 시즌 5",
        # "PLWoGc25qzA3uVQsBeqoYeRY4uKqzmM3EY": "최자로드 in 흑백요리사",
        # "PLWoGc25qzA3s5wC1AdhHf1LGojWrE8pOa": "최자로드 시즌 6",
    }

    # 키워드 입력 + 전체 수집 모드 지원
    #search_keyword = input("검색할 키워드를 입력하세요 (빈 입력 시 전체 수집): ").strip()
    use_filtering = bool(search_keyword)

    total_video_ids = []

   # 채널 영상 수집
    # for channel_id, name in channel_search_targets.items():
    #     video_ids = get_all_videos_from_channel(channel_id)
    #     logging.info(f"[{name}] 채널에서 {len(video_ids)}개 영상 수집됨")

    #     for vid in video_ids:
    #         try:
    #             video_meta, _ = fun.get_youtube_metadata(vid, YOUTUBE_API_KEY)
    #             title = video_meta.get("title", "")
    #             desc = video_meta.get("description", "")
    #             if not use_filtering or search_keyword.lower() in (title + desc).lower():
    #                 total_video_ids.append(vid)
    #                 logging.info(f"[{name}] 포함 영상: {title}")
    #         except Exception as e:
    #             logging.warning(f"[{name}] 메타데이터 조회 실패 (영상ID: {vid}): {e}")
    #             continue

    #재생목록 영상 수집
    for playlist_id, name in playlist_search_targets.items():
        video_ids = get_videos_from_playlist(playlist_id)
        logging.info(f"[{name}] 재생목록에서 {len(video_ids)}개 영상 수집됨")

        for vid in video_ids:
            try:
                video_meta = fun.get_youtube_metadata(vid, YOUTUBE_API_KEY)
                title = video_meta.get("title", "")
                desc = video_meta.get("description", "")
                if not use_filtering or search_keyword.lower() in (title + desc).lower():
                    total_video_ids.append(vid)
                    logging.info(f"[{name}] 포함 영상: {title}")
            except Exception as e:
                logging.warning(f"[{name}] 메타데이터 조회 실패 (영상ID: {vid}): {e}")
                continue

    # 중복 제거
    target_video_ids = list(set(total_video_ids))

    print(f"\n▶ 최종 영상 ID 수집 완료 ({len(target_video_ids)}개): {target_video_ids}")
    return target_video_ids