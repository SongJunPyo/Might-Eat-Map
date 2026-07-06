import url_func
import fun
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter()
@router.get("/url_pipeline")
async def url_pipeline_endpoint(url: str):
    """
    URL 파이프라인을 실행하는 엔드포인트입니다.
    :param url: 처리할 URL
    :return: URL 파이프라인 결과
    """
    try:
        md = url_func.Analyze_module()
        video_id = fun.extract_youtube_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="유효한 YouTube URL이 아닙니다.")
        gem_dicts, video_channel_meta = md.get_analyze_dict(video_id)
        if not gem_dicts:
            raise HTTPException(status_code=404, detail="해당 비디오에 대한 GEM 데이터가 없습니다.")
        return {
            "gem_dicts": gem_dicts,
            "video_channel_meta": video_channel_meta
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))