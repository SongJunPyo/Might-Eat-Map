# #server/routers/react_web.py

# from fastapi import APIRouter, HTTPException, Query
# from fastapi import Request
# from typing import List
# import logging
# from server.routers.gem import GemView
# from server.routers.db_manager import db_manager, get_kakao_geocode
# import os
# # 로그 설정
# #logging.basicConfig(level=logging.INFO)

# # 로그 설정: 파일에 로그 기록
# logging.basicConfig(
#     filename='server.log',       # 로그 파일 이름
#     level=logging.INFO,        # 로그 레벨
#     format='%(asctime)s - %(levelname)s - %(message)s',  # 로그 포맷
#     filemode='a'               # 파일 모드 (append 모드)
# )
# router = APIRouter()
# dbmanager = db_manager()

# # response_model을 지정함으로써 모델에 정의된 필드만 반환하도록 한다.
# # FastAPI가 자동으로 반환하는 리스트를 JSON으로 변환합니다
# # 상태 코드는 기본적으로 200을 반환합니다

# @router.get("/get_all_gem", response_model=List[GemView]) 
# async def get_all_gem(request: Request):
#     # 전체 Pet 정보를 반환한다.
#     try:
#         print("------get_all_gem------")
#         gemView = dbmanager.get_all_gem()
#         return gemView
    
#     except Exception as e:
#         # 에러 발생시 500 에러 반환
#         raise HTTPException(status_code=500, detail=str(e))
        
        
# @router.get('/search_gem', response_model=List[GemView])
# async def search_gem_endpoint(query: str): # 함수 이름 변경 및 query 파라미터 사용
#     try:
#         print(f"------search_gem: {query}------")
#         gemView = dbmanager.search_gem(query=query)
#         return gemView
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
    
# @router.get("/geocode")
# async def geocode_landmark(query: str):
#     KAKAO_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
#     if not KAKAO_API_KEY:
#         raise HTTPException(status_code=500, detail="카카오 API 키가 설정되지 않았습니다.")
    
#     # ★★★ 4. 올바른 함수 호출 ★★★
#     coords = get_kakao_geocode(query, KAKAO_API_KEY) 
    
#     if not coords:
#         raise HTTPException(status_code=404, detail=f"'{query}'에 대한 좌표를 찾을 수 없습니다.")
    
#     return coords



# react_web.py (수정본)

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import os
from dotenv import load_dotenv

# db_manager.py 파일에서 필요한 클래스와 함수를 모두 가져옵니다.
from server.routers.gem import GemView
from server.routers.db_manager import db_manager, get_kakao_geocode

# .env 파일을 로드하여 os.environ을 설정합니다.
load_dotenv()

router = APIRouter()

# DB 매니저 인스턴스를 생성하는 의존성 함수
def get_db():
    return db_manager()

# 카카오 API 키를 가져오는 의존성 함수
def get_kakao_key():
    key = os.environ.get("KAKAO_REST_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="서버에 카카오 API 키가 설정되지 않았습니다.")
    return key

@router.get("/get_all_gem", response_model=List[GemView])
async def get_all_gem_endpoint(db: db_manager = Depends(get_db)):
    
    
    
    
    return db.get_all_gem()

@router.get('/search_gem', response_model=List[GemView])
async def search_gem_endpoint(query: str, db: db_manager = Depends(get_db)):
    return db.search_gem(query=query)

@router.get("/geocode")
async def geocode_landmark(query: str, kakao_api_key: str = Depends(get_kakao_key)):
    coords = get_kakao_geocode(query, kakao_api_key)
    if not coords:
        raise HTTPException(status_code=404, detail=f"'{query}'에 대한 좌표를 찾을 수 없습니다.")
    return coords