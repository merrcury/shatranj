from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uuid
import uvicorn
import redis
import os

# REDIS DB OS
r_host = os.environ["rhost"]
r_pass = os.environ["rpassword"]

# REDIS DB OS


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
async def match(param: dict, request: Request):

    username = str(param.get("username"))
    token_bid = int(param.get("token_bid"))
    min_bid = int(param.get("min_bid"))

    idx = uuid.uuid1().int #Unique ID to represent the user.
    redis_set(idx,username,min_bid,token_bid)
    result = {"status":"Matching",
              "username":username,
              "UUID":idx}
    return result

