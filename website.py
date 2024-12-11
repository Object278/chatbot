from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import asyncio
from pydantic import BaseModel
import uuid

app = FastAPI()

# 配置 Jinja2 模板目录
templates = Jinja2Templates(directory="templates")

# WebSocket 客户端管理
connected_clients = set()

class Reservation(BaseModel):
    restaurant: str
    date: str
    time: str
    guests: int

@app.get("/")
async def get_page(request: Request):
    """
    渲染主页面，支持动态组件
    """
    return templates.TemplateResponse("index.html", {"request": request})


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

@app.post("/api/reservation")
async def make_reservation(reservation: Reservation):
    # 简单模拟保存预订信息
    reservation_id = str(uuid.uuid4())  # 生成唯一预订编号
    print(f"收到预订请求: {reservation}")
    return {"status": "success", "reservationId": reservation_id}

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