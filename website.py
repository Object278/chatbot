from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from models import Base, engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import Form, Reservation, SearchHistory, get_db
import json
import asyncio
from pydantic import BaseModel
import uuid
import logging
from functools import wraps

from process_data import Agent

app = FastAPI()
Base.metadata.create_all(bind=engine)

# 配置 Jinja2 模板目录
templates = Jinja2Templates(directory="templates")

# WebSocket 客户端管理
connected_clients = set()

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class ReservationRequest(BaseModel):
    restaurant: str
    date: str
    time: str
    guests: int

class FormRequest(BaseModel):
    name: str
    age: int
    email: str
    address: str
    remarks: str = None

class SearchRequest(BaseModel):
    query: str

    
def handle_db_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        db = kwargs.get('db')  # 获取数据库会话
        try:
            return await func(*args, **kwargs)
        except SQLAlchemyError as e:
            if db:
                db.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise HTTPException(
                status_code=500,
                detail="数据库操作失败，请稍后重试或联系支持。",
            )
    return wrapper

@app.get("/")
async def get_page(request: Request):
    """
    渲染主页面，支持动态组件
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 用于聊天消息和实时状态同步
    """
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")

            if action == "fillForm":
                # 处理填表格逻辑
                await websocket.send_text(json.dumps({"status": "success", "message": "开始填表格"}))
            elif action == "searchContent":
                # 处理搜索内容逻辑
                await websocket.send_text(json.dumps({"status": "success", "message": "搜索内容"}))
            elif action == "makeReservation":
                # 处理预订逻辑
                await websocket.send_text(json.dumps({"status": "success", "message": "预订成功"}))
            elif action == "sendMessage":
                print(f"收到消息：{message}")
            await broadcast_message(message)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

async def broadcast_message(message):
    """
    广播消息给所有客户端
    """
    for client in connected_clients:
        await client.send_text(json.dumps(message))

@app.post("/api/forms")
@handle_db_errors
async def submit_form(
    form_request: FormRequest,
    db: Session = Depends(get_db),
):
    form_data = Form(
        name=form_request.name,
        age=form_request.age,
        email=form_request.email,
        address=form_request.address,
        remarks=form_request.remarks,
    )
    db.add(form_data)
    db.commit()
    db.refresh(form_data)
    return JSONResponse(
        status_code=200,
        content={
            "status": True,
            "detail": "提交成功，谢谢你\(￣︶￣*\))",
        },
    )

@app.post("/api/reservation")
@handle_db_errors
async def make_reservation(
    res_request: ReservationRequest,
    db: Session = Depends(get_db),
):

    reservation_data = Reservation(
        restaurant=res_request.restaurant, 
        date=res_request.date, 
        time=res_request.time, 
        guests=res_request.guests
    )
    db.add(reservation_data)
    db.commit()
    db.refresh(reservation_data)
    return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "detail": "预订成功，谢谢你(*￣3￣)╭",
            },
        )

@app.post("/api/search")
@handle_db_errors
async def perform_search(search_request: SearchRequest, db: Session = Depends(get_db)):
    # 保存搜索历史
    search_history = SearchHistory(query=search_request.query)
    db.add(search_history)
    db.commit()

    # 模拟搜索结果
    results = [
        f"{search_request} - 相关结果 1",
        f"{search_request} - 相关结果 2",
        f"{search_request} - 相关结果 3",
    ]
    return {"status": "success", "results": results}

@app.get("/components/form", response_class=HTMLResponse)
async def get_form():
    with open("templates/components/form.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/components/search", response_class=HTMLResponse)
async def get_search():
    with open("templates/components/search.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/components/reservation", response_class=HTMLResponse)
async def get_reservation():
    with open("templates/components/reservation.html", "r", encoding="utf-8") as f:
        return f.read()
