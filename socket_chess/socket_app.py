from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_socketio import SocketManager


app = FastAPI(
    title="Socket Server",
    description="Socketio server",
    version="0.1.1",
    openapi_url="/api/v0.1.1/openapi.json",
    docs_url="/",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

socket_manager = SocketManager(app=app, async_mode="asgi", cors_allowed_origins=["*"])


@app.sio.on('connect')
async def connect(sid, *args, **kwargs):
    print("connect ", sid)
    await app.sio.emit('connect', 'User joined')


@app.sio.on('disconnect')
async def disconnect(sid):
    print('disconnect ', sid)
    await app.sio.emit('disconnect', 'User left')

@app.sio.event
async def string(sid, data):
    print("message ", data)
    await app.sio.emit('string', data=data)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.websocket('/ws')
async def websocket_endpoint(websocket: Request):
    await websocket.accept()
    json_data = await websocket.receive_json()

