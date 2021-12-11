import logging
import os
import uuid
import psycopg2
import redis

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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


def postgres_data(u1, u2, t1, t2, uu1, uu2):
    match_id = uuid.uuid4()

    connection = psycopg2.connect(user=sql_user,
                                  password=sql_pass,
                                  host=sql_host,
                                  port="5432",
                                  database="shatranj")
    ## ---> take param from os.env
    print("writing to db")
    uuid_pass = '"{}","{}"'.format(uu1, uu2)
    uuid_pass = "{"+uuid_pass+"}"
    postgres_insert_query = '''INSERT INTO match_history 
                                (match_id, opponent1,opponent2, token1, token2,uuid) 
                                VALUES ('{}','{}','{}', {},{},'{}')'''.format(match_id, u1, u2, t1, t2, uuid_pass)
    cursor = connection.cursor()
    cursor.execute(postgres_insert_query)
    connection.commit()


def match_found(usernames, tokens, uuids, mins, i, j):
    u1 = usernames[i]
    u2 = usernames[j]
    t1 = tokens[i]
    t2 = tokens[j]
    uu1 = uuids[i]
    uu2 = uuids[j]
    postgres_data(u1, u2, t1, t2, uu1, uu2)  # new entry in Postgres
    custom = "match found for" + str(u1) + "," + str(u2)
    logger.info(custom)

    usernames.pop(i)
    usernames.pop(j - 1)
    uuids.pop(i)
    uuids.pop(j - 1)
    tokens.pop(i)
    tokens.pop(j - 1)
    mins.pop(i)
    mins.pop(j - 1)
    ux = ",".join(usernames)
    r.set("username", ux)
    uu = ",".join(uuids)
    r.set("uuid", uu)
    tk = ",".join(list(map(str, tokens)))
    r.set("token", tk)
    mi = ",".join(list(map(str, mins)))
    r.set("min", mi)
    return True


async def matchmaking():
    print(r.get("uuid"))
    uuids = (list(str(r.get("uuid"), 'utf-8').split(",")))
    logger.info("Checking matchmaking pre-requisites")
    if len(uuids) > 1:
        logger.info("Finding Appropriate match")

        usernames = (list(map(str, str(r.get("username"), 'utf-8').split(","))))

        tokens = (list(map(int, str(r.get("token"), 'utf-8').split(","))))

        mins = (list(map(int, str(r.get("min"), 'utf-8').split(","))))

        last_val = mins[-1]
        last_ask = tokens[-1]
        token_len = len(tokens)
        if last_val in tokens[:-1]:
            t = tokens[:-1].index(last_val)
            if mins[t] >= last_ask:
                match_found(usernames, tokens, uuids, mins, t, token_len-1)
                return True
        else:
            for u in range(0, token_len - 1):
                if tokens[u] > last_val:
                    if mins[u] >= last_ask:
                        match_found(usernames, tokens, uuids, mins, u,token_len - 1)
                        return True

    return False