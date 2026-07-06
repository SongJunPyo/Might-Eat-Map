from pydantic import BaseModel

# Pydantic 모델 정의
class GemView(BaseModel):
    video_id: str
    gem_name: str
    gem_type: str
    recommend_reason: str | None = None
    start_timestamp: str | None = None  
    category: str | None = None
    latitude: float
    longitude: float
    address: str | None = None
    
    class Config:
        from_attributes = True # ORM 모델과의 호환성을 위함