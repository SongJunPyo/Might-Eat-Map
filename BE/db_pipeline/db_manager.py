import sqlite3
import mysql.connector
from mysql.connector import Error
from typing import List, Union
import logging
import math
import os
from dotenv import load_dotenv
# from server.routers.gem import GemView

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


class db_manager():
    def db_connect(self):
        try:
            self.conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME")
            )

            self.cursor = self.conn.cursor()
        except Error as e:
            print(f"Error connecting to MariaDB: {e}")
    
    def save_valid_result(self, gem_dict, is_valid_location):
        # gem 테이블에 valid_location 결과 추가
        self.db_connect()
        cursor = self.conn.cursor()
        try:
            query = """
                UPDATE GEM
                SET is_valid_location = %(is_valid_location)s
                WHERE gem_id = %(gem_id)s
            """
            cursor.execute(query, {
                "is_valid_location": int(is_valid_location),  # True/False → 1/0
                "gem_id": gem_dict["gem_id"]
            })
            self.conn.commit()
            logging.info(f"✅ [save_valid_result] gem_id={gem_dict['gem_id']} → 저장 성공: {is_valid_location}")
            
        except Exception as e:
            logging.error("❌ [save_single_gem] 삽입 실패")
            logging.error(f"🔍 에러 내용: {e}")
            logging.debug(f"📝 SQL 구문:\n{query}")

        finally:
            self.close()
            logging.info("🧹 [save_single_gem] DB 연결 종료")
        
    def save_single_gem(self, gem_dict):
        logging.info("🟡 [save_single_gem] 실행 시작")
        logging.debug(f"📦 삽입할 데이터:\n{gem_dict}")
        self.db_connect()
        cursor = self.conn.cursor()

        # gem_id는 자동 증가로 설정되어 있으므로, 수동으로 관리할 필요 없음
        # cursor.execute("SELECT MAX(gem_id) FROM GEM")
        # result = cursor.fetchone()
        # max_id = result[0] if result[0] is not None else 0
        # new_gem_id = max_id + 1
        # gem_dict["gem_id"] = new_gem_id
            
        print("video_id: ", gem_dict["video_id"])
        
        # INSERT 문 수정 (= 제거)
        insert_sql = """
        INSERT INTO GEM (
            video_id,
            gem_name,
            category,
            recommend_reason,
            start_timestamp,
            latitude,
            longitude,
            script_score,
            final_score,
            comment_score,
            address,
            scripts,
            gem_type,
            location,
            collect_date
        ) VALUES (
            %(video_id)s,
            %(gem_name)s,
            %(category)s,
            %(recommend_reason)s,
            %(start_timestamp)s,
            %(latitude)s,
            %(longitude)s,
            %(script_score)s,
            %(final_score)s,
            %(comment_score)s,
            %(address)s,
            %(scripts)s,
            %(gem_type)s,
            %(location)s,
            %(collect_date)s
        )
        """

        logging.debug("🛠 SQL 준비 완료. DB에 삽입 시도...")

        try:
            cursor.execute(insert_sql, gem_dict)
            gem_id = cursor.lastrowid  # 삽입된 gem_id 가져오기
            self.conn.commit()
            logging.info(f"✅ [save_single_gem] {gem_dict['gem_name']} 삽입 성공 (gem_id: {gem_id})")
            
            # restaurant_hint (또는 gem_hint)가 있으면 추가로 UPDATE
            gem_dict["gem_id"] = gem_id  # gem_id 추가
            if 'restaurant_hint' in gem_dict:
                update_sql = """
                    UPDATE GEM
                    SET gem_name_hint = %(restaurant_hint)s
                    WHERE gem_id = %(gem_id)s
                """
                cursor.execute(update_sql, gem_dict)
                self.conn.commit()
                logging.info("🔁 [save_single_gem] restaurant_hint 추가 업데이트 완료")
            
            # VIDEO 테이블 업데이트
            sql = "UPDATE VIDEO SET is_completed = 1 WHERE video_id = %s"
            cursor.execute(sql, (gem_dict["video_id"],))
            self.conn.commit()
            logging.info(f"✅ [save_single_gem] {gem_dict['video_id']} is_completed = 1 업데이트 성공")
                
        except Exception as e:
            logging.error("❌ [save_single_gem] 삽입 실패")
            logging.error(f"🔍 에러 내용: {e}")
            logging.debug(f"📝 SQL 구문:\n{insert_sql}")

        finally:
            self.close()
            logging.info("🧹 [save_single_gem] DB 연결 종료")
            
    def save_single_video(self, video_dict):
        logging.info("🟡 [save_single_video] 실행 시작")
        logging.debug(f"📦 삽입할 데이터:\n{video_dict}")
        self.db_connect()
        cursor = self.conn.cursor()

        insert_sql = """
        UPDATE VIDEO
        SET channel_id = %(channel_id)s,
            channel_name = %(channel_name)s,
            video_link = %(video_link)s,
            video_title = %(video_title)s,
            upload_date = %(upload_date)s,
            description = %(description)s,
            view_count = %(view_count)s,
            like_count = %(like_count)s,
            comment_count = %(comment_count)s,
            engagement_ratio = %(engagement_ratio)s,
            like_ratio = %(like_ratio)s
        WHERE video_id = %(video_id)s
        """

        logging.debug("🛠 SQL 준비 완료. DB에 삽입 시도...")

        try:
            cursor.execute(insert_sql, video_dict)
            self.conn.commit()
            logging.info(f"✅ [save_single_video] {video_dict['video_id']} 삽입 성공")

        except Exception as e:
            logging.error("❌ [save_single_video] 삽입 실패")
            logging.error(f"🔍 에러 내용: {e}")
            logging.debug(f"📝 SQL 구문:\n{insert_sql}")

        finally:
            self.close()
            logging.info("🧹 [save_single_video] DB 연결 종료")
            
    def save_single_channel(self, channel_dict):

        self.db_connect()
        cursor = self.conn.cursor()
        # collect_channel 테이블에 channel_id가 있는지 확인
        cursor.execute("SELECT channel_id FROM collect_channel WHERE channel_id = %s", (channel_dict["channel_id"],))
        result = cursor.fetchone()  
        if result:
            try:
                logging.info(f"🟡 [save_single_channel] 채널 {channel_dict['channel_id']} 이미 존재. 업데이트 진행...")
                update_sql = """
                UPDATE collect_channel
                SET channel_name = %(channel_name)s,
                    subscriber_count = %(subscriber_count)s,
                    sub_view_ratio = %(sub_view_ratio)s,
                    avg_view = %(avg_view)s
                WHERE channel_id = %(channel_id)s
                """
                cursor.execute(update_sql, channel_dict)
                self.conn.commit()
                logging.info(f"✅ [save_single_channel] {channel_dict['channel_id']} 업데이트 성공")
            except Exception as e:
                logging.error("❌ [save_single_channel] 업데이트 실패")
                logging.error(f"🔍 에러 내용: {e}")
                logging.debug(f"📝 SQL 구문:\n{update_sql}")
        else:
            try:
                logging.info(f"🟢 [save_single_channel] 채널 {channel_dict['channel_id']} 새로 삽입")
                insert_sql = """
                INSERT INTO collect_channel (channel_id, channel_name, sub_view_ratio, subscriber_count, avg_view)
                VALUES (%(channel_id)s, %(channel_name)s, %(sub_view_ratio)s, %(subscriber_count)s, %(avg_view)s)
                """
                logging.debug("🛠 SQL 준비 완료. DB에 삽입 시도...")

                cursor.execute(insert_sql, channel_dict)
                self.conn.commit()
                logging.info(f"✅ [save_single_channel] {channel_dict['channel_id']} 삽입 성공")

            except Exception as e:
                logging.error("❌ [save_single_channel] 삽입 실패")
                logging.error(f"🔍 에러 내용: {e}")
                logging.debug(f"📝 SQL 구문:\n{insert_sql}")

        self.close()
        logging.info("🧹 [save_single_channel] DB 연결 종료")

    def load_video_id_list(self):
        self.db_connect()
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT video_id FROM VIDEO WHERE is_completed = 0") # 분석 안된 비디오만 불러옴
            rows = cursor.fetchall()

            # 결과를 리스트로 변환
            video_id_list = [row[0] for row in rows]
            print("✅ [fetch_all_video_ids] 조회된 video_id 목록:", video_id_list)
            return video_id_list

        except Exception as e:
            print(f"❌ [fetch_all_video_ids] 오류: {e}")
            return []

        finally:
            self.close()
            print("🧹 [fetch_all_video_ids] DB 연결 종료")
    
    def save_video(self, video_id_list):
        self.db_connect()
        try:
            print("📌 [save_video] 입력 video_id_list:", video_id_list)

            # 커서 생성
            cursor = self.conn.cursor()

            for video_id in video_id_list:
                print(f"➡️ [save_video] 삽입 시도: video_id = {video_id}")
                try:
                    # MySQL에서는 ? 대신 %s 사용
                    cursor.execute("INSERT INTO VIDEO (video_id) VALUES (%s)", (video_id,))
                except Exception as inner_e:
                    print(f"⚠️ [save_video] video_id={video_id} 삽입 실패: {inner_e}")

            # 변경 사항 커밋
            self.conn.commit()
            print("✅ [save_video] 커밋 완료")

        except Error as e:
            print(f"❌ [save_video] 전체 오류: {e}")
            return False
        finally:
            self.close()
            print("🧹 [save_video] DB 연결 종료")

        return True
    
    def mark_video_completed(self, video_id, status): # status 0:미완 1:완료 2:실패패
        self.db_connect()
        try:
            cursor = self.conn.cursor()
            sql = "UPDATE VIDEO SET is_completed = %s WHERE video_id = %s"
            cursor.execute(sql, (status, video_id))
            self.conn.commit()

            if cursor.rowcount:
                print(f"✅ [mark_video_completed] video_id={video_id} 업데이트 성공")
                return True
            else:
                print(f"⚠️ [mark_video_completed] video_id={video_id}에 해당하는 행이 없습니다")
                return False

        except Exception as e:
            print(f"❌ [mark_video_completed] 오류: {e}")
            return False

        finally:
            self.close()
        print("🧹 [mark_video_completed] DB 연결 종료")
        
    def get_all_places(self) -> List[dict]:
        self.db_connect()
        try:
            cursor = self.conn.cursor(dictionary=True)
            query = """
                SELECT gem_name, latitude, longitude
                FROM GEM
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """
            cursor.execute(query)
            results = cursor.fetchall()
            return results  # 각 row는 {'gem_name': ..., 'latitude': ..., 'longitude': ...}

        except Exception as e:
            logging.error(f"❌ [get_all_places] 오류 발생: {e}")
            return []

        finally:
            self.close()
            logging.info("🧹 [get_all_places] DB 연결 종료")

    def update_single_feature_z_scores(self, feature_name: str, table_name: str):
        """
        주어진 feature_name에 대한 z-score를 업데이트합니다.
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
        query = f"""
        UPDATE {table_name}
        SET z_{feature_name} = ({feature_name} - {mean}) / {stddev}
        WHERE {feature_name} IS NOT NULL;   
        """
        self.cursor.execute(query)
        self.conn.commit()
        self.conn.close()
        
    def update_all_z_scores(self):
        """
        모든 feature에 대한 z-score를 업데이트합니다.
        """
        self.db_connect()
        
        self.update_single_feature_z_scores('sub_view_ratio', 'collect_channel')
        self.update_single_feature_z_scores('view_count', 'VIDEO')
        self.update_single_feature_z_scores('engagement_ratio', 'VIDEO')
        self.update_single_feature_z_scores('like_ratio', 'VIDEO')
        self.update_single_feature_z_scores('comment_score', 'GEM')
        self.update_single_feature_z_scores('script_score', 'GEM')
        
        logging.info("✅ [update_all_z_scores] 모든 z-score 업데이트 완료")
        self.close()
        
    def update_all_final_scores(self):
        """
        모든 GEM의 최종 점수를 업데이트합니다.
        """
        self.db_connect()
        query = """
        SELECT a.gem_id,
               a.z_script_score,
               a.z_comment_score,
               b.z_view_count,
               b.z_like_ratio,
               c.z_sub_view_ratio
        FROM GEM a, VIDEO b, collect_channel c
        WHERE a.video_id = b.video_id
        AND b.channel_id = c.channel_id;
        """      
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        if not rows:
            logging.warning("⚠️ [update_all_final_scores] 업데이트할 데이터가 없습니다.")
            self.close()
            return
        update_query = """
        UPDATE GEM 
        SET final_score = (
            (%s + %s + %s +%s + %s) / 5.0
        )
        WHERE gem_id = %s;
        """
        for row in rows:
            gem_id, z_script_score, z_comment_score, z_view_count, z_like_ratio, z_sub_view_ratio = row
            self.cursor.execute(update_query, (
                z_script_score, 
                z_comment_score, 
                z_view_count, 
                z_like_ratio, 
                z_sub_view_ratio,
                gem_id
            ))
        self.conn.commit()
        logging.info("✅ [update_all_final_scores] 모든 GEM의 최종 점수 업데이트 완료")
        self.close()
        



        
    def close(self):
        self.cursor.close()
        self.conn.close()

