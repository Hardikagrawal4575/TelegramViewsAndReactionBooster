import configparser
from telethon import TelegramClient, events
from telethon.tl.types import User, Channel, Chat, ChatEmpty
from rich import print
import time
from threading import Thread,Event
from NewpostThreads import startSendingViews,sendReactionThreadWrapper
from CustomFunctions import selectionState
from os import system, name

config=configparser.ConfigParser()
config.read("config.ini")

stop_event = Event()

api_id = config["MonitorNewPost"]["api_id"]
api_hash = config["MonitorNewPost"]["api_hash"]
proxytype = config["MonitorNewPost"]["proxytype"]
minimumviews = int(config["Global"]["minimumviews"])
MonitoringList = config["MonitorNewPost"]["monitorchannel"]
MonitoringList = [int(id.strip()) for id in MonitoringList.split(",") if id]


client = TelegramClient('anon', api_id, api_hash)

@client.on(events.NewMessage)
async def my_event_handler(event):
    chat = await event.get_chat()
    if not isinstance(chat, Channel):
        return
    
    sender = await event.get_sender()
    chat_id = event.chat_id
    sender_id = event.sender_id
    print(chat_id)
    if chat_id in MonitoringList:
        print(f"[+] From : {chat.title} [+] Link : https://t.me/{chat.username}/{event.message.id} [+] Msg : {event.message.message}")
        Thread(target=startSendingViews,args=(f"https://t.me/{chat.username}/{event.message.id}",minimumviews,proxytype)).start()
        if selectionState():
            Thread(target=sendReactionThreadWrapper,args=(chat.username,event.message.id)).start()
        else:
            print("[+] Skipping Post to send Reaction")

def parseTime(initial,final):
    time_spent_seconds = final - initial
    hours = int(time_spent_seconds // 3600)
    remaining_seconds = time_spent_seconds % 3600
    minutes = int(remaining_seconds // 60)
    seconds = int(remaining_seconds % 60)
    return f"{hours}:{minutes}:{seconds}"

def terminal():
    start_time = time.time()
    while not stop_event.is_set():
        from NewpostThreads import ERRORLOG,VIEWSCOUNT,SUBTHREADCOUNT
        from CustomFunctions import ipUsageTrack,DatacenteredIps
        ipusageformated={key:len(ipUsageTrack[key]) for key in ipUsageTrack}
        end_time = time.time()
        print(f"[+] Uptime : {parseTime(start_time,end_time)}")
        print(f"[+] Monitoring : {MonitoringList}")
        print(f"[+] Errors : {ERRORLOG}")
        print(f"[+] ThreadCount : {SUBTHREADCOUNT}")
        print(f"[+] View Analytics : {VIEWSCOUNT}")
        if proxytype=="d":
            print(f"[+] Total Ip : {len(DatacenteredIps)}")
            print(f"[+] Ip Uage :{ipusageformated}")
        print("\n\n")
        time.sleep(2)
        # system('cls' if name=='nt' else 'clear')

client.start()
Thread(target=terminal).start()
client.run_until_disconnected()
stop_event.set()