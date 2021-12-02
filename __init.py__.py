import logging
import os
import uuid
from datetime import datetime

import boto3
import psycopg2
import redis
from aws_xray_sdk.core import patch_all

# LOGGING
logger = logging.getLogger()
logger.setLevel(logger.info())
patch_all()

client = boto3.client('lambda')
client.get_account_settings()

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


def postgres_data(u1, u2, t1, t2):
    match_id = uuid.uuid1().int

    try:
        connection = psycopg2.connect(user=sql_user,
                                      password=sql_pass,
                                      host=sql_host,
                                      port="5432",
                                      database="shatranj")
        ## ---> take param from os.env
        cursor = connection.cursor()
        cursor = connection.cursor()
        print("writing to db")

        now = str(datetime.now())

        postgres_insert_query = """ INSERT INTO match_history (match_id, opponent1,opponent2, token1, token2, created) VALUES (%d,%s,%s, %d,%d,%s,%s)"""
        values = (match_id, u1, u2, t1, t2, now)
        cursor.execute(postgres_insert_query, values)
        connection.commit()
    except Exception as e:
        print("Failed to connect to DB" + str(e))
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")


async def matcher():
    uuids = (list(r.get("uuid").split(",")))
    logger.info("Checking matchmaking pre-requisites")
    if len(uuids) > 1:

        while len(uuids) > 1:  # ATLEAST 2 PLAYERS
            logger.info("Finding Appropriate match")

            usernames = (list(map(str, r.get("username").split(","))))

            tokens = (list(map(int, r.get("token").split(","))))

            mins = (list(map(int, r.get("min").split(","))))

            for i in range(len(mins)):
                m = mins[i]
                for j in range(len(tokens)):
                    if i != j:  # Not the same player
                        t = tokens[j]
                        if m <= t and mins[j] < tokens[i]:  # matching Algo

                            u1 = usernames[i]
                            u2 = usernames[j]
                            t1 = tokens[i]
                            t2 = tokens[j]
                            uu1 = uuids[i]
                            uu2 = uuids[j]
                            postgres_data(u1, u2, t1, t2)  # new entry in Postgres
                            custom = "match found for" + str(u1) + "," + str(u2)
                            logger.info(custom)

                            usernames.pop(i)
                            usernames.pop(j)
                            uuids.pop(i)
                            uuids.pop(j)
                            tokens.pop(i)
                            tokens.pop(j)
                            mins.pop(i)
                            mins.pop(j)
                            break
                    logger.info("No match found, Please wait")
                if m not in mins:
                    break

            ux = ",".join(usernames)
            r.set("username", ux)
            uu = ",".join(uuids)
            r.set("uuid", uu)
            tk = ",".join(list(map(str,tokens)))
            r.set("token", tk)
            mi = ",".join(list(map(str,mins)))
            r.set("min", mi)

    else:
        logger.info("No match found!, Wait for more users to join in")
