import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()  # .env 파일 로드
#fun 파일
def get_kakao_geocode(query: str, kakao_api_key: str):
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    params = {"query": query}
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
 
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        result = res.json()
        print("result:", result)
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
 
#analyze_local
# 4-2. Kakao Local API로 후보 검증 및 좌표 획득
validated_restaurants = {}  # {'상호명': {'lat': 위도, 'lng': 경도, 'address': 주소}}
location_context = "창원"  # 지역명 넣으면 정확도 상승
 
KAKAO_API_KEY = os.environ.get("KAKAO_REST_API_KEY")

candidates  =[""]
print(f"KAKAO_API_KEY: {KAKAO_API_KEY}")
for candidate in candidates:
    time.sleep(0.1)  # API 부하 방지
    query = location_context + candidate
    coords = get_kakao_geocode(query, KAKAO_API_KEY)
 
    if coords:
        print(f"  [검증 성공] '{query}' → 좌표: ({coords['lat']}, {coords['lng']}) | 주소: {coords['address']}")
        # 동일 주소 중복 방지
        if coords["address"] not in [v["address"] for v in validated_restaurants.values()]:
            validated_restaurants[candidate] = coords