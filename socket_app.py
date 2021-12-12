from fastapi import FastAPI, Request
from fastapi_socketio import SocketManager

app = FastAPI()
socket_manager = SocketManager(app=app, mount_location='/')

@app.sio.on('room')
async def join_room(sid, *args, **kwargs):
    print(sid)
    room, username = args
    print(args)
    await app.sio.save_session(sid, {'username': username, 'room': room})
    app.sio.enter_room(sid, room)
    await app.sio.emit('room', username, room=room)

@app.sio.on('move')
async def make_move(sid, *args, **kwargs):
    session = await app.sio.get_session(sid)
    move = args[0]
    print(move)
    print("User: {}".format(session['username']))
    await app.sio.emit('move', move, room=session['room'], skip_sid=sid)

@app.sio.on('acknowledgement')
async def acknowledgement(sid, *args, **kwargs):
    session = await app.sio.get_session(sid)
    await app.sio.emit('acknowledgement', session['username'], room=session['room'], skip_sid=sid)

@app.sio.event
async def disconnect(sid):
    session = await app.sio.get_session(sid)
    await app.sio.emit('disconnect', session['username'], room = session['room'], skip_sid= sid)
    app.sio.leave_room(sid, session['room'])
    print("User Disconnected")
    print(session)

@app.sio.event
async def connect(sid, environ, auth):
    print("User Connected")

@app.sio.on('resign')
async def game_resign(sid, *args, **kwargs):
    session = await app.sio.get_session(sid)
    await app.sio.emit('resign', session['username'], room=session['room'], skip_sid=sid)
    app.sio.leave_room(sid, session['room'])
    print("User Resigned!")
    print(session)