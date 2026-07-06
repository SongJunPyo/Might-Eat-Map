# analyze_local.py
# 올바른 인터프리터(venv) 설정 필수

import logging
import fun as fun
from db_manager import db_manager
from analyze_module import Analyze_module

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

# print("모든 모델 로딩 완료.")


# --- 2. 분석 대상 동영상 ID 목록 ---
# 예시: 창원 맛집 영상으로 테스트
dbmanager = db_manager()
# video_id_list = collect_fun.youtube_video_collect("")
# dbmanager.save_video(video_id_list)


        
target_video_ids =dbmanager.load_video_id_list() # 분석할 YouTube 비디오 IDAanalyze_module = Analyze_module()
# videos_to_analyze = [
#     {'video_id': 'zrLdC7aYy64', 'channel_id': None, 'view_count': 0, 'like_count': 0, 'comment_count': 0, 'subscriber_count': 0},
#     {'video_id': 'bUNWPvwzvpQ', 'channel_id': None, 'view_count': 0, 'like_count': 0, 'comment_count': 0, 'subscriber_count': 0},
#     {'video_id': 'ER8NwhJ6yH4', 'channel_id': None, 'view_count': 0, 'like_count': 0, 'comment_count': 0, 'subscriber_count': 0},
#     {'video_id': '-dz2zJw0Q3k', 'channel_id': None, 'view_count': 0, 'like_count': 0, 'comment_count': 0, 'subscriber_count': 0},
#     {'video_id': 'IJwIJZ3G-pw', 'channel_id': None, 'view_count': 0, 'like_count': 0, 'comment_count': 0, 'subscriber_count': 0}
# ]
analyze_module = Analyze_module()
# --- 3. 각 동영상별 데이터 처리 루프 ---
for video_id in target_video_ids:
    (gem_dicts, video_channel_meta) = analyze_module.get_analyze_dict(video_id)

    if gem_dicts:
        for gem_dict in gem_dicts:
            dbmanager.save_single_gem(gem_dict)
            result = analyze_module.valid_location(gem_dict)
            dbmanager.save_valid_result(gem_dict, result)
    else :
        dbmanager.mark_video_completed(video_id,2) # 좌표 없음
    
    if video_channel_meta:
        dbmanager.save_single_video(video_channel_meta)
        dbmanager.save_single_channel(video_channel_meta)

# --- 4. 모든 GEM의 z-score 업데이트 및 최종 점수 계산 ---        
dbmanager.update_all_z_scores()
dbmanager.update_all_final_scores()

    

print("\n=====================모든 동영상 분석 완료.=====================\n")