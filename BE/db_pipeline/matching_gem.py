import requests
import os
import analyze_local
from dotenv import load_dotenv
from db_manager import db_manager
import time
manager = db_manager()
places = manager.get_all_places()

load_dotenv()  # .env 파일 로드
KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")

def find_nearby_restaurants(lat, lng, api_key, radius=50):
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
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

def is_match_kakao_vs_known(kakao_name, known_name):
    n_kakao = normalize(kakao_name)
    n_known = normalize(known_name)
    return n_kakao in n_known or n_known in n_kakao  # 포함 여부

manager = db_manager()
places = manager.get_all_places()

for place in places:
    known_name = place['gem_name']
    lat = place['latitude']
    lng = place['longitude']

    print(f"🔍 {known_name} (위도: {lat}, 경도: {lng})")

    results = find_nearby_restaurants(lat, lng, KAKAO_API_KEY, radius=100)

    if results:
        
        top_result = results[0]
        matched = is_match_kakao_vs_known(top_result["name"], known_name)

        print(f"📍 Kakao 결과: {top_result['name']} | 주소: {top_result['address']} | 거리: {top_result['distance']}m")
        print(f"✅ 일치 여부: {matched}")
    else:
        print("❌ 주변 음식점 없음")

    print("-" * 50)
    


# 테스트 좌표
#lat, lng = 35.2424544999311, 128.689748743219 #리코리코 위도/경도
#results = find_nearby_restaurants(lat, lng, KAKAO_API_KEY, radius=100)

# 비교할 기존 상호명
#known_name = "리코리코"

#if results:
    #matched = is_match_kakao_vs_known(results[0]["name"], known_name)
    #print(f"{results[0]['name']} | {results[0]['address']} | {results[0]['distance']}")
    #print("일치 여부:", matched)
#else:
    #print("좌표 검색 실패")
    #rint("일치 여부: False")
    