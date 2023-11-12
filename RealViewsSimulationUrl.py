import asyncio
import configparser
from rich import print
from time import sleep
from os import system, name
from threading import Thread,Event
from GhostViewCore import BoostViews
from CustomFunctions import getChannelAndId
from GhostViewCore import BoostViews,POSTS
import time

config = configparser.ConfigParser()
config.read("config.ini")
stopEvent = Event()

LatestPostLink = config["RealViewsSimulationUrl"]["LatestPostLink"]
OlderPostLink = config["RealViewsSimulationUrl"]["OlderPostLink"]

def getAllPosts():
    posts=[LatestPostLink]
    Lchannel,Latest_Post_id = getChannelAndId(LatestPostLink)
    Ochannel,older_Post_id = getChannelAndId(OlderPostLink)
    if Lchannel == Ochannel:
        bin=0
        if Latest_Post_id < older_Post_id:
            bin=Latest_Post_id
            Latest_Post_id=older_Post_id
            older_Post_id=bin
        
        for x in range(int(Latest_Post_id)-int(older_Post_id)):
             x+=1
             posts.append(LatestPostLink.replace(str(Latest_Post_id),str(int(Latest_Post_id)-x)))
        return posts
    else:
        raise Exception("Post Links are not from same Channel")

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