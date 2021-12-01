import json
import uuid
from datetime import date, datetime
import psycopg2
import redis
# import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import os

# POSTGRES CRED
sql_user = os.environ["suser"]
sql_host = os.environ["shost"]
sql_pass = os.environ["spassword"]

# REDIS DB OS
r_host = os.environ["rhost"]
r_pass = os.environ["rpassword"]

r = redis.Redis(
    host=r_host,
    port=6379,
    password=r_pass)

app = FastAPI(
    title="Shatranj",
    description="MatchMaking API for Shatranj",
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


# class UnicornException(Exception):
#     def __init__(self, name: str):
#         self.name = name


# class data(BaseModel):
#     username: List[str] = Query(...)
#     token_bid: List[str] = Query(...)
#     min_bid: List[str] = Query(...)


# @app.exception_handler(UnicornException)
# async def unicorn_exception_handler(request: Request, exc: UnicornException):
#     return JSONResponse(
#         status_code=418,
#         content={
#             "message": f"Oops! {exc.name} can't be processed. There goes a rainbow..."
#         },
#     )

def redis_entry(username, token_bid, min_bid):
    value = str(token_bid) + "," + str(min_bid)
    r.set(username, value, ex=300)


def db_write(opponent1, opponent2, token1, token2, match_id):
    # Write in DB
    try:
        connection = psycopg2.connect(user=sql_user,
                                      password=sql_pass,
                                      host=sql_host,
                                      port="5432",
                                      database="shatranj")
        ## ---> take param from os.env
        cursor = connection.cursor()

        print("writing to db")
        today = date.today()
        dt = today.strftime("%d/%m/%Y")

        now = datetime.now()
        tm = now.strftime("%H:%M:%S")

        postgres_insert_query = """ INSERT INTO match_history (match_id, opponent1,opponent2, token1, token2, Date, Time) VALUES (%d,%s,%s, %d,%d,%s,%s)"""
        values = (match_id, opponent1, opponent2, token1, token2, dt, tm)
        cursor.execute(postgres_insert_query, values)
        connection.commit()

    except Exception as e:
        print("Failed to connect to DB" + str(e))

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")


async def matchmaker(param, request):
    eligible = {}
    username = param.get("username")
    token_bid = param.get("token_bid")
    min_bid = param.get("min_bid")

    redis_entry(username, token_bid, min_bid)

    ### ---> Better method to search on redis
    for x in r.keys():
        if await request.is_disconnected():
            print("client disconnected!!!")
            break
        x = str(x, 'utf-8')
        response = str(r.get(x), 'utf-8')
        bid_new = int(response[0])
        if min_bid <= bid_new <= token_bid and x != username:  # stops self-matching
            eligible.update({x: bid_new})
    ###

    if len(eligible.keys()) > 1:  # stops self-matching
        match_username = max((zip(eligible.values(), eligible.keys()))[1])
        match_tokenbid = eligible.get(match_username)
        idx = uuid.uuid1()
        match_id = idx.int

        ### ---> Wallet Code Here
        ###
        db_write(username, match_username, token_bid, match_tokenbid, match_id)
        eligible.clear()

        result = {
            "description": "Match Successful",
            "content": {
                "match_username": match_username,
                "match_tokenbid": match_tokenbid,
                "match_id": match_id

            }}
    else:
        result = {
            "description": "No Match found",
            "content": {
                "match_username": None,
                "match_tokenbid": None,
                "match_id": None

            }}
    yield json.dumps(result)


@app.get('/match')
async def match(param: dict, request: Request):
    matchx = matchmaker(param, request)
    return EventSourceResponse(matchx)  ## SSE

    # Press the green button in the gutter to run the script.


# if __name__ == '__main__':
#     print("Running now")
#     uvicorn.run(app, host="0.0.0.0", port=8000)
