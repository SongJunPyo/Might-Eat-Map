from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import asyncio
import uvicorn
from typing import Optional, Dict, Any
import logging

import sqlite3  # 예제용으로 SQLite 사용
from pydantic import BaseModel



# 로그 설정
#logging.basicConfig(level=logging.INFO)

# 로그 설정: 파일에 로그 기록
logging.basicConfig(
    filename='server.log',       # 로그 파일 이름
    level=logging.INFO,        # 로그 레벨
    format='%(asctime)s - %(levelname)s - %(message)s',  # 로그 포맷
    filemode='a'               # 파일 모드 (append 모드)
)

from fastapi import FastAPI
from server.routers import react_web   # 라우터 임포트
#from routers.pdf_manager import pdf_router

app = FastAPI()

# 다른 도메인에서 오는 요청을 허용할 수 있도록 설정합니다.
app.add_middleware(
    CORSMiddleware,
    #allow_origins=["http://15.164.220.68"],     #flutter 웹앱의 주소를 설정하면됨. 나중에  # flutter run -d web-server --web-port= <<여기에 설정된 값으로 하면됨
    allow_origins=["*"], 
    allow_credentials=True,                  # 쿠키를 허용하도록 설정
    allow_methods=["*"],
    allow_headers=["*"],
)


# 세션 미들웨어 추가
# FastAPI 앱의 전역 미들웨어로 동작합니다.
# 클라이언트와 서버 간의 세션 데이터를 관리합니다.
# 세션 데이터를 암호화하고, 요청/응답을 통해 쿠키로 전달합니다.
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secure-secret-key",  # 실제로는 안전한 키를 사용해야 합니다
)


# 라우터 등록


app.include_router(react_web.router, prefix="/react_web", tags=["react_web"])

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server on http://")
    uvicorn.run(app, host="0.0.0.0", port=9000)  #  비동기함수가 아님