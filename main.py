from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from matchmaker import matchmaking

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
async def match(data: match_model):

    username = data.username
    token_bid = data.token_bid
    min_bid = data.min_bid

    if min_bid > token_bid:
        return {
            "message":"Minimum Bid can't be bigger than your bid amount"
        }

    idx = uuid.uuid1().int #Unique ID to represent the user.

    redis_set(idx,username,min_bid,token_bid)
    x = await matchmaking()
    result = {"status":"Matching",
              "username":username,
              "UUID":idx}

    return result


async def check_matchmaking(uuid, request):
    query = '''
                SELECT
                *
            FROM
                "public".match_history
            WHERE
                '{}' = ANY (uuid)  
    '''.format(uuid)

    print(query)

    while True:
        if await request.is_disconnected():
            uuids = (list(str(r.get("uuid"), 'utf-8').split(",")))
            uuids.pop(uuid)
            uu = ",".join(uuids)
            r.set("uuid", uu)
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
                yield json.dumps("Match Found")
                break
        time.sleep(1)



@app.get('/match/status')
async def match_status(uuid: int, request: Request):
    status = check_matchmaking(uuid, request)
    return EventSourceResponse(status)