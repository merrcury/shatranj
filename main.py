from fastapi import FastAPI, Request, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from matchmaker import matchmaking
from fastapi_socketio import SocketManager


from pydantic import BaseModel
import uuid
import redis
import os
import json
import time
import  psycopg2

# REDIS DB OS
r_host = os.environ["rhost"]
r_pass = os.environ["rpassword"]

sql_user = os.environ["suser"]
sql_host = os.environ["shost"]
sql_pass = os.environ["spassword"]

class match_model(BaseModel):
    username: str = Query(...)
    token_bid: int = Query(...)
    min_bid: int = Query(...)


r = redis.Redis(
    host=r_host,
    port=6379,
    password=r_pass)

app = FastAPI(
    title="Shatranj",
    description="Online User Registration for Shatranj",
    version="0.1.1",
    openapi_url="/api/v0.1.1/openapi.json",
)



socket_manager = SocketManager(app=app, mount_location='/ws')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connection = psycopg2.connect(user=sql_user,
                                  password=sql_pass,
                                  host=sql_host,
                                  port="5432",
                                  database="shatranj")

def redis_set(idx, username, min_token, token):
    valuex=""
    if r.get("uuid"):
        valuesx = ","+str(idx)
        r.append("uuid",valuesx) #ARRAY 1
    else:
        valuesx = str(idx)
        r.append("uuid", valuesx)  # ARRAY 1

    if r.get("username"):
        valuesx = ","+str(username)
        r.append("username",valuesx) #ARRAY 2
    else:
        valuesx = str(username)
        r.append("username", valuesx)  # ARRAY 2

    if r.get("min"):
        valuesx = ","+str(min_token)
        r.append("min",valuesx) #ARRAY 3
    else:
        valuesx = str(min_token)
        r.append("min", valuesx)  # ARRAY 3

    if r.get("token"):
        valuesx = ","+str(token)
        r.append("token",valuesx) #ARRAY 4
    else:
        valuesx = str(token)
        r.append("token", valuesx)  # ARRAY 4

""" GET TIME OF CREATION of a key in redis """
"""List can be used in redis instead of string
Ref  - https://realpython.com/python-redis/#more-data-types-in-python-vs-redis"""


@app.post('/match')
async def match_start(data: match_model, background_tasks: BackgroundTasks):

    username = data.username
    token_bid = data.token_bid
    min_bid = data.min_bid

    if min_bid > token_bid:
        return {
            "message":"Minimum Bid can't be bigger than your bid amount"
        }

    idx = uuid.uuid4().hex #Unique ID to represent the user.

    redis_set(idx,username,min_bid,token_bid)
    background_tasks.add_task(matchmaking)
    result = {"status":"Matching",
              "username":username,
              "UUID":idx}

    return result


async def check_matchmaking(uuid, request):
    query = '''
                SELECT
                *
            FROM
                match_history
            WHERE
                '{}' = ANY (uuid)  
    '''.format(uuid)

    print(query)

    while True:
        if await request.is_disconnected():
            uuids = (list(str(r.get("uuid"), 'utf-8').split(",")))
            idm = uuids.index(str(uuid))
            uuids.pop(idm)
            usernames = (list(map(str, str(r.get("username"), 'utf-8').split(","))))
            tokens = (list(map(int, str(r.get("token"), 'utf-8').split(","))))
            mins = (list(map(int, str(r.get("min"), 'utf-8').split(","))))
            usernames.pop(idm)
            tokens.pop(idm)
            mins.pop(idm)

            uu = ",".join(uuids)
            r.set("uuid", uu)
            ux = ",".join(usernames)
            r.set("username", ux)
            tk = ",".join(list(map(str, tokens)))
            r.set("token", tk)
            mi = ",".join(list(map(str, mins)))
            r.set("min", mi)
            print("client disconnected!!!")
            break
        else:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()

            if result == None:
                yield json.dumps(
                    "No Match Found"
                )
            else:
                yield json.dumps({
                    "match_id": result[0],
                    "white": result[1],
                    "black":  result[2]
                } )
                break
        time.sleep(1)


@app.get('/match/status')
async def match_status(uuid: str, request: Request):
    status = check_matchmaking(uuid, request)
    return EventSourceResponse(status)

@app.get('/match/cancel')
async def match_cancel(uuid:str, request: Request):
    uuids = (list(str(r.get("uuid"), 'utf-8').split(",")))
    idm = uuids.index(str(uuid))
    uuids.pop(idm)
    usernames = (list(map(str, str(r.get("username"), 'utf-8').split(","))))
    tokens = (list(map(int, str(r.get("token"), 'utf-8').split(","))))
    mins = (list(map(int, str(r.get("min"), 'utf-8').split(","))))
    usernames.pop(idm)
    tokens.pop(idm)
    mins.pop(idm)

    uu = ",".join(uuids)
    r.set("uuid", uu)
    ux = ",".join(usernames)
    r.set("username", ux)
    tk = ",".join(list(map(str, tokens)))
    r.set("token", tk)
    mi = ",".join(list(map(str, mins)))
    r.set("min", mi)
    return True



@app.get('/match')
async def match_valid(match_id:str):
    query = ''' select * from match_history where match_id = '{}' '''.format(match_id)

    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()
    return {   "match_id": result[0],
                "white": result[1],
                "black":  result[2]
                }

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
    query = '''
    update match_history SET pgn = '{}' where match_id = '{}'
    '''.format(move, session['room'])

    with connection.cursor() as cursor:
        cursor.execute(query)
        connection.commit()

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