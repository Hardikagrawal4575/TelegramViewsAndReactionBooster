import configparser
from CustomFunctions import getChannelAndId
from GhostViewCore import BoostViews
from threading import Thread,Event
import asyncio
from time import sleep
from os import system, name
from rich import print
import time

config = configparser.ConfigParser()
config.read("config.ini")
stopEvent = Event()

LatestPostLink = config["RealViewsSimulationIndex"]["LatestPostLink"]
NoOfPost = int(config["RealViewsSimulationIndex"]["Index"])


def getAllPosts():
    posts=[]
    _,post_id = getChannelAndId(LatestPostLink)
    for i in range(NoOfPost):
        if int(post_id)-i <1:
            continue
        posts.append(LatestPostLink.replace(str(post_id),str(int(post_id)-i)))
    return posts

def showStatus(stop_event):
    start_time = time.time()
    firstrequest=None
    while not stop_event.is_set():
        from GhostViewCore import POSTS,REQUESTSCOUNT,LOGS,REQUESTCOMPLETION
        end_time = time.time()
        POSTS.sort()
        time_spent_seconds = end_time - start_time
        hours = int(time_spent_seconds // 3600)
        remaining_seconds = time_spent_seconds % 3600
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)
        strtime=f"{hours}:{minutes}:{seconds}"
        if firstrequest is None and REQUESTCOMPLETION:
            firstrequest=strtime
        print(f"[+] Duration : {hours}:{minutes}:{seconds}",end=" ")
        if firstrequest:
            print(f"[+] FirstRequest : {strtime}",end=" ")
        print(f"[+] PostCount : {len(POSTS)}",end=" ")
        print(f"[+] Requests : {REQUESTSCOUNT}",end=" ")
        print(f"[+] CompletedRequest : {REQUESTCOMPLETION}",end="\n\n")
        print("[+] Error : ")
        print(LOGS)
        print(f"[+] LivePostStatus : ")
        print(POSTS)
        sleep(2)
        system('cls' if name=='nt' else 'clear')


async def main():
    posts=getAllPosts()
    await BoostViews(posts)

Thread(target=showStatus,args=(stopEvent,)).start()
asyncio.run(main())
stopEvent.set()
