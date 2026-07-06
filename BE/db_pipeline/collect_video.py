
import youtube_video_collect as collect_fun
from db_manager import db_manager

dbmanager = db_manager()
video_id_list = collect_fun.youtube_video_collect("")
dbmanager.save_video(video_id_list)