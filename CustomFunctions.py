import glob
import random
import aiohttp
import time
import requests
import configparser
from CustomClasses import Post
from scrapy.selector import Selector
from telethon import functions, types
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import SendReactionRequest

config = configparser.ConfigParser()
config.read("config.ini")

reactionInterval = int(config["Reactions"]["reactionInterval"])


RPusername = config["RPCredentials"]["username"]
RPpassword = config["RPCredentials"]["password"]
RPserver = config["RPCredentials"]["server"]
RPport = config["RPCredentials"]["port"]

NoOfMsgForChunk = int(config["Reactions"]["NoOfMsgForChunk"])
SelectionPercent = int(config["Reactions"]["SelectionPercent"])

MinNoOfReactionType = int(config["Reactions"]["MinNoOfReactionType"])
MaxNoOfReactionType = int(config["Reactions"]["MaxNoOfReactionType"])

MinNoOfReaction = int(config["Reactions"]["MinNoOfReaction"])
MaxNoOfReaction = int(config["Reactions"]["MaxNoOfReaction"])

postSelectionState = []
ActiveSessionIds = []
DatacenteredIps = set()
ipUsageTrack = {}


def PostSelectionState():
    global postSelectionState
    postSelectionState.clear()
    truePercent = int((SelectionPercent/100) * NoOfMsgForChunk)
    postSelectionState = [False]*NoOfMsgForChunk
    Modified = []
    for _ in range(truePercent):
        done = False
        while not done:
            index = random.randint(0, NoOfMsgForChunk-1)
            if index not in Modified:
                postSelectionState[index] = True
                Modified.append(index)
                done = True
    random.shuffle(postSelectionState)

    def getPostSelectionState():
        while True:
            for state in postSelectionState:
                yield state
            PostSelectionState()

    return getPostSelectionState()


# -----no need to controll Manually selected----
selected = PostSelectionState()


def selectionState():
    return next(selected)
# ----------------------------------------------


def NoOfReactionTypes():
    return random.randint(MinNoOfReactionType, MaxNoOfReactionType)


def NoOfReactions():
    return random.randint(MinNoOfReaction, MaxNoOfReaction)


def selectedReactions():
    reactions = ['👍', '👌', '❤️', '😍', '🔥', '👏', '😁'
                , '🤯', '😱', '🎉', '🤩', '🙏', '🕊', '💯', '⚡', '🏆', '😇','🤗']
    reactions = random.sample(reactions, NoOfReactionTypes())
    finalrecations = []
    for _ in range(NoOfReactions()):
        finalrecations.append(random.choice(reactions))
    return finalrecations


def newProxie():
    username = RPusername
    password = RPpassword
    server = RPserver
    port = RPport
    return f'http://{username}:{password}@{server}:{port}'


def newDatacenteredProxie(url):
    global DatacenteredIps
    if not len(DatacenteredIps):
        print("[+] Fetching Ips...")
        proxyLinks = [
            "https://raw.githubusercontent.com/Hardikagrawal4575/proxy-premium/main/proxyscrape_premium_http_proxies.txt",
            "https://raw.githubusercontent.com/Hardikagrawal4575/proxy-premium/main/proxy%202"
        ]
        for link in proxyLinks:
            resp = requests.get(link)
            ips = set(resp.text.split())
            DatacenteredIps = DatacenteredIps.union(ips)
    if url not in ipUsageTrack:
        ip = random.choice(list(DatacenteredIps))
        ipUsageTrack[url] = [ip]
        return f'http://{ip}'

    unusedlist = DatacenteredIps-set(ipUsageTrack[url])
    if len(unusedlist):
        ip = random.choice(list(unusedlist))
        ipUsageTrack[url].append(ip)
        return f'http://{ip}'
    else:
        return None


def getChannelAndId(url):
    channel, id = url.replace("https://t.me/", "").split("/")
    return channel, id


def UpdateConfig(config: configparser.ConfigParser):
    with open("config.ini", "w") as file:
        config.write(file)


def calc_viewsOfPreviousPost(viewsOfCurrentPost, noOfPosts):
    previospost = viewsOfCurrentPost
    views = [viewsOfCurrentPost]
    for _ in range(noOfPosts-1):
        previospost = previospost + 0.01 * previospost
        views.append(int(previospost))
    return views


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"


async def async_CheckViewOnPost(posturl):
    post = Post(url=posturl, status=False, views=0)
    channel, post_id = getChannelAndId(posturl)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://t.me/{channel}/{post_id}', params={'embed': '1', 'mode': 'tme'},
                                   headers={'referer': f'https://t.me/{channel}/{post_id}', 'user-agent': user_agent}) as resp:
                html = Selector(text=await resp.text())
                views = html.xpath(
                    '//span[@class="tgme_widget_message_views"]').xpath('string()').get()

                if not views:
                    return post
                if 'k' in views:
                    view_count = int(
                        float(views.replace('k', '').strip()) * 1000)
                else:
                    view_count = int(views.strip())

                # update post status
                post.status = True
                post.views = view_count
    except:
        pass
    return post


def sync_CheckViewOnPost(posturl):
    post = Post(url=posturl)
    channel, post_id = getChannelAndId(posturl)
    telegram_request = requests.get(
        f'https://t.me/{channel}/{post_id}',
        params={'embed': '1', 'mode': 'tme'},
        headers={'referer': f'https://t.me/{channel}/{post_id}',
                 'user-agent': user_agent})
    html = Selector(text=telegram_request.text)
    views = html.xpath(
        '//span[@class="tgme_widget_message_views"]').xpath('string()').get()

    if views:
        if 'k' in views:
            view_count = int(float(views.replace('k', '').strip()) * 1000)
        else:
            view_count = int(views.strip())
        post.status = True
        post.views = view_count
    return post


def createChunks(contentlist, listsize):
    threads = 0
    if len(contentlist) <= listsize:
        threads = len(contentlist)
    else:
        threads = listsize

    urlDistribution = {}

    for index, url in enumerate(contentlist):
        sublist_index = index % threads
        key = f"_{sublist_index}"
        if key not in urlDistribution:
            urlDistribution[f"_{sublist_index}"] = []
        urlDistribution[f"_{sublist_index}"].append(url)

    return [urlDistribution[key] for key in urlDistribution]


def sendReactions(chanel_id, post_id):
    reactions = selectedReactions()
    sessions = glob.glob("sessions/*.session")
    for reaction in reactions:
        time.sleep(random.randint(0,10))
        print("[+] Sending Reaction")
        selectedSession = random.choice(sessions)
        print(f"[+] Selected Session : {selectedSession}")
        sessionname = selectedSession.split("\\")[1].strip(".session")
        if sessionname not in ["919874623618", "918797653753"]:
            client = TelegramClient(selectedSession, 12121212, "hash")
            try:
                client.start()
                reactionobj = SendReactionRequest(
                    peer=chanel_id, msg_id=int(post_id),
                    big=True, reaction=[types.ReactionEmoji(emoticon=reaction)])
                client(reactionobj)
            finally:
                # Stop and disconnect the client
                client.disconnect()
        time.sleep(reactionInterval)
