# import analyze_module

# from analyze_module import Analyze_module
# from fun import *

# print(get_youtube_metadata("cID9BR67s7s"))

# from youtube_video_collect import *
# print(get_videos_from_playlist("PLuMuHAJh9g_Py_PSm8gmHdlcil6CQ9QCM"))

import sqlite3
import mysql.connector
from mysql.connector import Error
from typing import List,Union
import logging
from fun import *
from transformers import pipeline
from db_manager import db_manager as original_db_manager
import math
import analyze_module

class db_manager():
    def db_connect(self):
        try:
            self.conn = mysql.connector.connect(
                host="10.100.54.75",  # MariaDB 서버 호스트
                user="jinsoo",  # MariaDB 사용자 이름
                password="UXUZtd.HM77DE/h!",  # MariaDB 사용자 비밀번호
                database="youtube_ht"  # 사용할 데이터베이스 이름
            )

            self.cursor = self.conn.cursor()
        except Error as e:
            print(f"Error connecting to MariaDB: {e}")
            
    def get_all_video_gemname_list(self) -> List[str]:
        """
        모든 (video_id, gem_name)을 반환합니다.
        """
        self.db_connect()
        query = "SELECT gem_id, video_id, gem_name FROM GEM"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        self.conn.close()

        return [(row[0], row[1], row[2]) for row in result]
        
    def get_duplicate_gem_id_list(self) -> List[str]:
        """
        중복된 gem_id를 반환합니다.
        """
        self.db_connect()
        query = "SELECT gem_id FROM `GEM` WHERE (video_id, gem_name) IN (SELECT video_id, gem_name FROM `GEM` GROUP BY video_id, gem_name HAVING COUNT(*) > 1)"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        self.conn.close()

        return [row[0] for row in result]

    
    def duplicate_gem_video_list(self, gem_id_list) -> List[str]:
        """
        중복된 gem_id를 가진 영상 ID를 반환합니다.
        """
        self.db_connect()
        query =  "SELECT video_id FROM GEM WHERE gem_id IN ({})".format(','.join(['%s'] * len(gem_id_list)))
        self.cursor.execute(query, tuple(gem_id_list))
        result = self.cursor.fetchall()
        self.conn.close()

        return [row[0] for row in result]

    def null_video_list(self) -> List[str]:
        """
        meta 정보가 없는 영상 ID를 반환합니다.
        """
        self.db_connect()
        query = "SELECT video_id FROM VIDEO WHERE channel_name IS NULL"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        self.conn.close()
        
        return [row[0] for row in result]

    def null_video_list(self) -> List[str]:
        """
        meta 정보가 없는 영상 ID를 반환합니다.
        """
        self.db_connect()
        query = "SELECT video_id FROM VIDEO WHERE channel_name IS NULL"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        self.conn.close()
        
        return [row[0] for row in result]
    
    def like_ratio_video_list(self) -> List[str]:
        """
        meta 정보가 없는 영상 ID를 반환합니다.
        """
        self.db_connect()
        query = "SELECT video_id FROM VIDEO WHERE like_ratio = 0"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        self.conn.close()
        
        return [row[0] for row in result]
    
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

        # finally:
        #     self.close()
        #     logging.info("🧹 [save_single_video] DB 연결 종료")
    
    def set_video_uncompleted(self, video_id):
        """
        영상의 completed 상태를 0으로 설정합니다.
        """
        self.db_connect()
        query = "UPDATE VIDEO SET is_completed = 0 WHERE video_id = %s"
        self.cursor.execute(query, (video_id,))
        self.conn.commit()
        self.conn.close()
        
    def delete_gem_by_video_id(self, video_id):
        """
        특정 video_id에 해당하는 GEM 데이터를 삭제합니다.
        """
        self.db_connect()
        query = "DELETE FROM GEM WHERE video_id = %s"
        self.cursor.execute(query, (video_id,))
        self.conn.commit()
        self.conn.close()
        
    def update_comment_score(self, gem_id, video_id, comment_score):
        """
        GEM 테이블의 comment_score를 업데이트합니다.
        """
        self.db_connect()
        query = "UPDATE GEM SET comment_score = %s WHERE gem_id = %s AND video_id = %s"
        self.cursor.execute(query, (comment_score, gem_id, video_id))
        self.conn.commit()
        self.conn.close()
        
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
        
    def update_z_scores(self, feature_name: str, table_name: str):
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
        
    def update_z_scores_to_percentile_gem(self):
        """
        모든 z-score를 백분위로 변환합니다.
        """
        self.db_connect()
        query = """
        SELECT gem_id, z_script_score, z_comment_score, final_score
        FROM GEM
        WHERE z_script_score IS NOT NULL AND z_comment_score IS NOT NULL
        AND final_score IS NOT NULL;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        update_query = """
        UPDATE GEM
        SET z_script_score = %s,
            z_comment_score = %s,
            final_score = %s
        WHERE gem_id = %s;
        """
        
        for row in rows:
            gem_id, z_script_score, z_comment_score, final_score = row
            self.cursor.execute(update_query, (
                z_to_percentile(z_script_score),
                z_to_percentile(z_comment_score),
                z_to_percentile(final_score),
                gem_id
            ))
        
        self.conn.commit()
        logging.info("✅ [update_z_scores_to_percentile] 모든 GEM의 Z-점수 백분위 업데이트 완료")
            
    def update_z_scores_to_percentile_video(self):
        """
        모든 z-score를 백분위로 변환합니다.
        """
        self.db_connect()
        query = """
        SELECT video_id, z_view_count, z_like_ratio, z_engagement_ratio
        FROM VIDEO
        WHERE z_view_count IS NOT NULL AND z_like_ratio IS NOT NULL
        AND z_engagement_ratio IS NOT NULL;
        """
       
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        update_query = """
        UPDATE VIDEO
        SET z_view_count = %s,
            z_like_ratio = %s,
            z_engagement_ratio = %s
        WHERE video_id = %s;
        """
        
        for row in rows:
            video_id, z_view_count, z_like_ratio, z_engagement_ratio = row
            self.cursor.execute(update_query, (
                z_to_percentile(z_view_count),
                z_to_percentile(z_like_ratio),
                z_to_percentile(z_engagement_ratio),
                video_id
            ))
        
        self.conn.commit()
        logging.info("✅ [update_z_scores_to_percentile_video] 모든 GEM의 Z-점수 백분위 업데이트 완료")
            
    def update_z_scores_to_percentile_channel(self):
        """
        모든 z-score를 백분위로 변환합니다.
        """
        self.db_connect()
        query = """
        SELECT channel_id, z_sub_view_ratio
        FROM collect_channel
        WHERE z_sub_view_ratio IS NOT NULL;
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        update_query = """
        UPDATE collect_channel
        SET z_sub_view_ratio = %s
        WHERE channel_id = %s;
        """
        
        for row in rows:
            channel_id, z_sub_view_ratio = row
            self.cursor.execute(update_query, (
                z_to_percentile(z_sub_view_ratio),
                channel_id
            ))
        
        self.conn.commit()
        logging.info("✅ [update_z_scores_to_percentile_channel] 모든 GEM의 Z-점수 백분위 업데이트 완료")
            
            
    def close(self):
        self.cursor.close()
        self.conn.close()



def z_to_percentile(z: Union[float, list[float]]) -> Union[float, list[float]]:
    """
    표준점수 z를 0~100 백분위로 변환합니다.
    - z: 단일값 또는 값들의 리스트
    - 반환값: 백분위 (0.0 ~ 100.0)
    """
    def _cdf(val: float) -> float:
        # 표준 정규분포 CDF: 0.5 * [1 + erf(z / sqrt(2))]
        return 0.5 * (1 + math.erf(val / math.sqrt(2)))

    if isinstance(z, list):
        return [ _cdf(v) * 100 for v in z ]
    else:
        return _cdf(z) * 100
    
    
# video_list = db_manager().like_ratio_video_list()
db = db_manager()
ori_db = original_db_manager()
# video_list = db.null_video_list()

# # @@@@video 메타 정보가 없는 행 업데이트
# for video_id in video_list:
#     try:
#         video_meta = fun.get_youtube_metadata(video_id)
#         db.save_single_video(video_meta)
        
#     except Exception as e:
#         logging.error(f"Error processing video {video_id}: {e}")

# @@@@중복된 GEM 데이터 삭제 및 해당 video is_completed 상태 초기화
# videos = db.duplicate_gem_video_list(db.get_duplicate_gem_id_list())
# for video_id in videos:
#     try:
#         db.set_video_uncompleted(video_id)
#         db.delete_gem_by_video_id(video_id)
#         logging.info(f"✅ {video_id}의 GEM 데이터 삭제 및 completed 상태 초기화 완료")
#     except Exception as e:
#         logging.error(f"❌ {video_id} 처리 중 오류 발생: {e}")
        
# @@@@ 현재 GEM 테이블의 SCORE 업데이트
# sentiment_pipeline = pipeline("text-classification", model="daekeun-ml/koelectra-small-v3-nsmc", device=0) # KoELECTRA 기반 맛집 리뷰 문장 평가 모델 ('조회수'나 '좋아요' 수만으로 맛집을 찾는 것과 차별화되는 핵심적인 이유)

# for gem_id, video_id, gem_name in db.get_all_video_gemname_list():
#     try:
#         if gem_name is None or gem_name == "":
#             logging.warning(f"⚠️ {video_id}의 GEM 이름이 비어있습니다. 건너뜁니다.") 
#             # 이후 모듈 코드에서도 gem_name이 비어있을 경우를 처리
#             continue
#         comments = fun.get_video_comments(video_id)
#         comment_score = fun.calculate_restaurant_review_score(gem_name, comments, sentiment_pipeline)
#         db.update_comment_score(gem_id, video_id, comment_score)
#         logging.info(f"✅ {video_id}의 GEM 댓글 점수 업데이트 완료 : SCORE = {comment_score}")
#     except Exception as e:
#         logging.error(f"❌ {video_id} 처리 중 오류 발생: {e}")

# @@@@ 채널 메타 정보 업데이트
# video_meta = fun.get_youtube_metadata('-e6zzDqCS6E')
# db.save_single_channel(video_meta)


### @@@@ 표준 점수 업데이트

# db.update_z_scores('view_count', 'VIDEO')
# db.update_z_scores('like_ratio', 'VIDEO')
# db.update_z_scores('sub_view_ratio', 'collect_channel')
# db.update_z_scores('engagement_ratio', 'VIDEO')
# db.update_z_scores('comment_score', 'GEM')
# db.update_z_scores('script_score', 'GEM')

# @@@@ 모든 z-score 업데이트 and final_score 수정
# ori_db = original_db_manager()
# ori_db.update_all_z_scores()
# ori_db.update_all_final_scores()

# db.update_z_scores_to_percentile_gem()
# db.update_z_scores_to_percentile_video()
# db.update_z_scores_to_percentile_channel()

# db.close()

an = analyze_module.Analyze_module()
gems,meta = an.get_analyze_dict('QkURfyDZuTw')
print("===========================")
print(gems)
print("===========================")
print(meta)

# final_score 수정하는 코드 추가

# 채널 조회율, 조회수, 좋아요비율, 댓글참여율, 댓글감성, 스크립트감성 DB 적재 완료 후 표준정규화 코드 추가