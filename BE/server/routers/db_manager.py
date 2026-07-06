#server/routers/db_manager.py

import sqlite3
import mysql.connector
from mysql.connector import Error
from typing import List
import logging
from server.routers.gem import GemView
import os
import requests
from dotenv import load_dotenv

load_dotenv()


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,  # 출력 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("db_manager.log", encoding='utf-8'),  # 파일 저장
        logging.StreamHandler()  # 콘솔 출력
    ]
)

def get_kakao_geocode(query: str, kakao_api_key: str):
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    params = {"query": query}
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        result = res.json()
        if result["documents"]:
            top = result["documents"][0]
            return {
                "name": top["place_name"],
                "address": top.get("road_address_name") or top.get("address_name"),
                "lat": float(top["y"]),
                "lng": float(top["x"])
            }
        return None
    except Exception as e:
        print(f"[Kakao API 오류] '{query}' 요청 실패: {e}")
        return None

class db_manager():
    def __init__(self):
        self.conn = None
        self.cursor = None

    def db_connect(self):
        try:
            self.conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                charset="utf8mb4"
            )

            self.cursor = self.conn.cursor()
        except Error as e:
            print(f"Error connecting to MariaDB: {e}")
    
    def get_all_gem(self)-> List[GemView]:
        self.db_connect()
        try:
            cursor = self.conn.cursor(dictionary=True)
            query = """
            SELECT
                video_id,
                gem_name,
                gem_type,
                recommend_reason,
                start_timestamp,
                category,
                latitude,
                longitude,
                address
            FROM GEM
            WHERE gem_name IS NOT NULL
            """
            cursor.execute(query)
            result = cursor.fetchall()
            
            return [GemView(**row) for row in result]  # 🔥 Pydantic 모델로 변환

        except Exception as e:
            print(f"❌ [get_all_gem] 오류: {e}")
            return []
        finally:
            self.close()
        
    def search_gem(self, query: str) -> List[GemView]:
        """
        데이터베이스의 gem 테이블에서 gem_name 또는 category에
        검색어가 포함된 맛집을 찾아 반환합니다.
        """
        self.db_connect()
        try:
            cursor = self.conn.cursor(dictionary=True)

            sql_query = """
                SELECT * FROM GEM
                WHERE (gem_name LIKE %s OR gem_type LIKE %s OR category LIKE %s OR address LIKE %s)
                AND gem_name IS NOT NULL
            """
            # 검색어 앞뒤에 %를 붙여 부분 일치 패턴을 만듭니다.
            search_pattern = f"%{query}%"
            
            cursor.execute(sql_query, (search_pattern, search_pattern, search_pattern, search_pattern))
            # cursor.execute(sql_query, (query,))
            
            result = cursor.fetchall()
            return [GemView(**row) for row in result]

        except Exception as e:
            print(f"❌ [search_gem] 오류: {e}")
            return []
        finally:
            self.close()
            
    def get_z_score(self, feature_name: str, table_name: str, now: float):
        """
        주어진 feature_name에 대한 평균(mean)과 표준편차(stddev)를 계산하고,
        해당 값을 사용하여 z-score를 반환 합니다.
        """
        self.db_connect()
        query = f"""
        SELECT AVG({feature_name}) AS mean, STDDEV({feature_name}) AS stddev
        FROM {table_name}
        WHERE {feature_name} IS NOT NULL;
        """
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if result is None or result[1] == 0:
            logging.warning(f"⚠️ {feature_name}의 평균 또는 표준편차가 0입니다. z-score 업데이트를 건너뜁니다.")
            self.conn.close()
            return  
        mean, stddev = result
        result = (now - mean) / stddev if stddev != 0 else 0

        self.conn.close()
    
    def close(self):
        if self.conn and self.conn.is_connected():
            if self.cursor is not None:
                self.cursor.close()
            self.conn.close()
        self.conn = None
        self.cursor = None
    
