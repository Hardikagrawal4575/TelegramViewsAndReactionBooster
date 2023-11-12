import aiohttp, asyncio
from CustomFunctions import newProxie,getChannelAndId,async_CheckViewOnPost,calc_viewsOfPreviousPost
from NewpostThreads import sendReactionThreadWrapper
from CustomClasses import TokenException,Target,Post
from aiohttp_socks import ProxyConnector
from rich import print
from scrapy.selector import Selector
import configparser
from os import system, name
from time import sleep
from threading import Thread

config = configparser.ConfigParser()
config.read("config.ini")


user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
ASYNCTASKS=[]
POSTS = []
MINVIEWS=int(config["Global"]["MinimumViews"])
REQUESTSCOUNT=0
REQUESTCOMPLETION=0
LOGS=dict()

async def sendViewsOn(post:Post):
    global  REQUESTCOMPLETION
    global REQUESTSCOUNT
    global LOGS

    channel,post_id=getChannelAndId(post.url)
    subUrl =f'https://t.me/{channel}/{post_id}?embed=1&mode=tme'
    target =Target()

    while not target.Achieved and target.Attempt < target.maxRetry:
        target.Attempt+=1
        # print(f"[+] Attempt : {target.Attempt}, Url : {post.url} ")
        try:
            connector = ProxyConnector.from_url(newProxie())
            timeout = aiohttp.ClientTimeout(total=120)
            cookiejar = aiohttp.CookieJar(unsafe=True)
            async with aiohttp.ClientSession(connector=connector,cookie_jar=cookiejar,timeout=timeout) as session:
                REQUESTSCOUNT+=1
                async with session.get(url=subUrl,headers={'referer': post.url,'user-agent': user_agent}) as resp:
                    REQUESTCOMPLETION+=1
                    html = Selector(text=await resp.text())

                    stel_ssid = cookiejar.filter_cookies(resp.url).get("stel_ssid")
                    views_token = html.xpath('//*[@data-view]/@data-view').get()

                    if stel_ssid and views_token : # stel_ssid in  cookie
                        resp = await session.post(
                            url=f'https://t.me/v/?views={views_token}', 
                            headers={
                                'referer': subUrl,
                                'user-agent': user_agent,
                                'x-requested-with': 'XMLHttpRequest'},
                            timeout=timeout)
                        REQUESTCOMPLETION+=1
                        if resp.status == 200 and await resp.text() == "true":
                            post.views+=1
                            target.Achieved = True                
                    else:
                        raise TokenException(f"Token Not Found on 'https://t.me/{channel}/{post_id}?embed=1&mode=tme'")
                        
        except Exception as e:
            if f"{e}" not in LOGS:
                LOGS[f"{e}"]=0
            LOGS[f"{e}"]+=1

async def CheckAndIncreaseView(post:Post):
    channel,post_id=getChannelAndId(post.url)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://t.me/{channel}/{post_id}',params={'embed': '1', 'mode': 'tme'},
            headers={'referer': f'https://t.me/{channel}/{post_id}','user-agent': user_agent}) as resp:
                html = Selector(text= await resp.text())
                views = html.xpath('//span[@class="tgme_widget_message_views"]').xpath('string()').get()

                if not views: return 0 # post is not available
                views=views.lower()
                if 'k' in views:
                    view_count = int(float(views.replace('k', '').strip()) * 1000)
                else:
                    view_count = int(views.strip())

                # update post status 
                post.status=True
                post.views=view_count
                POSTS.append(post)
        
        # start increasing views
        if post.views<post.requiredViews:
            subtask=[]
            for _ in range(post.requiredViews-post.views):
                subtask.append(asyncio.create_task(sendViewsOn(post)))
            await asyncio.gather(*subtask)
    except Exception as e:
        if f"{e}" not in LOGS:
            LOGS[f"{e}"]=0
        LOGS[f"{e}"]+=1

async def calculateViews(PostUrlList: list[str]):
    try:
        PostUrlList.sort(reverse=True)
        calculatedViews = []
        LatestPost = await async_CheckViewOnPost(PostUrlList[0])
        if LatestPost.views<=MINVIEWS:
            calculatedViews=calc_viewsOfPreviousPost(MINVIEWS,len(PostUrlList))
        else:
            calculatedViews=calc_viewsOfPreviousPost(LatestPost.views,len(PostUrlList))

        return [Post(url=url,requiredViews=views) for url,views in zip(PostUrlList,calculatedViews) ]
    except Exception as e:
        if f"{e}" not in LOGS:
            LOGS[f"{e}"]=0
        LOGS[f"{e}"]+=1



async def BoostViews(posts):
    try:
        posts = list(set(posts))
        posts = await calculateViews(posts)
        for post in posts:
            chat_id,post_id = post.url.replace("https://t.me/", "").split("/")
            Thread(target=sendReactionThreadWrapper,args=(chat_id,post_id)).start()
            
            task = asyncio.create_task(CheckAndIncreaseView(post))
            await task
            
        await asyncio.gather(*ASYNCTASKS)
    except Exception as e:
        if f"{e}" not in LOGS:
            LOGS[f"{e}"]=0
        LOGS[f"{e}"]+=1
        