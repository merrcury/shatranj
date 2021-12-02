import json
import uuid
from datetime import date, datetime
import psycopg2
import redis
import uvicorn
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

def redis_entry(username, token_bid, min_bid,status):
    value = str(token_bid) + "," + str(min_bid) +","+str(status)
    r.set(username, value, ex=30)


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

#created_at and modified_at
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
    valuesx = []

    username = str(param.get("username"))
    token_bid = int(param.get("token_bid"))
    min_bid = int(param.get("min_bid"))

    redis_entry(username, token_bid, min_bid, 1)

    while r.exists(username):


        ### ---> Better method to search on redis
        for x in r.keys():
            if await request.is_disconnected():
                print("client disconnected!!!")
                break
            x = str(x, 'utf-8')
            response = str(r.get(x), 'utf-8')
            valuesx = list(response.split(","))
            bid_new = int(valuesx[0])
            min_bid_new = int(valuesx[1])
            statusx = int(valuesx[2])
            if min_bid <= bid_new and min_bid_new <= token_bid and statusx==1 and x!=username:  # stops self-matching #opponent min to be check
                eligible.update({x: bid_new})
        ###

        if len(eligible.keys()) > 1:  # stops self-matching
            match_username = max(eligible, key= lambda y: eligible[y])
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
            yield json.dumps(result)
            redis_entry(username,token_bid,min_bid,0)
            break


        else:
            result = {
                "description": "Waiting",
                "content": {
                    "match_username": None,
                    "match_tokenbid": None,
                    "match_id": None

                }}
            yield json.dumps(result)

    yield json.dumps({
                "description": "No match Found!",
                "content": {
                    "match_username": None,
                    "match_tokenbid": None,
                    "match_id": None

                }})



#background process

@app.post('/match') #query param
async def match(param: dict, request: Request):
    matchx = matchmaker(param, request)
    return EventSourceResponse(matchx)  ## SSE

    #{"username":"Ankur","token_bid":50,"min_bid":30}

    # Press the green button in the gutter to run the script.


# if __name__ == '__main__':
#     print("Running now")
#     uvicorn.run(app, host="0.0.0.0", port=8000)
