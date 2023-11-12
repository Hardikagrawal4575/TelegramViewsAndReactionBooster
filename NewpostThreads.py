import requests
from rich import print
from scrapy.selector import Selector
import time
from CustomFunctions import sync_CheckViewOnPost, newProxie as newResidentialProxie, newDatacenteredProxie,sendReactions
from threading import Thread
from rich import print 
from aiohttp_socks import ProxyConnector
import aiohttp
import asyncio
import configparser
import random

from rich import print

config=configparser.ConfigParser()
config.read("config.ini")

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
VIEWSCOUNT = dict()
ERRORLOG = dict()
SUBTHREADCOUNT = 0
TOKENLOGS=set()
threadcreationinterval = float(config["MonitorNewPost"]["threadcreationinterval"])

def parseView(response):
    try:
        response = Selector(text=response.text)
        views = response.xpath(
            '//span[@class="tgme_widget_message_views"]').xpath('string()').get()
        views = views.lower()
        if 'k' in views:
            view_count = int(float(views.replace('k', '').strip()) * 1000)
        else:
            view_count = int(views.strip())
        return view_count
    except:
        return 0


def SendView(url, proxy, attempt=1):
    global SUBTHREADCOUNT,TOKENLOGS,ERRORLOG, VIEWSCOUNT
    SUBTHREADCOUNT += 1
    channel, post_id = url.replace("https://t.me/", "").split("/")
    proxy = {
        'http': proxy,
    }
    try:
        session = requests.session()
        response = session.get(f'https://t.me/{channel}/{post_id}?embed=1&mode=tme', headers={'referer': url, 'user-agent': USER_AGENT},proxies=proxy)
        views_token = response.text.split('data-view="')[1].split('"')[0]
        TOKENLOGS.add(views_token)
        if views_token and "stel_ssid" in session.cookies.get_dict():
            response = session.post(f'https://t.me/v/?views={views_token}',
                                    headers={
                                        'referer': f'https://t.me/{channel}/{post_id}?embed=1&mode=tme',
                                        'user-agent': USER_AGENT,
                                        'x-requested-with': 'XMLHttpRequest'},
                                    proxies=proxy)
            if (response.status_code == 200 and response.text == 'true'):
                VIEWSCOUNT[f"{channel}--{post_id}"] += 1
                SUBTHREADCOUNT -= 1
                return 1
        raise ValueError("Token Not Available")
    except Exception as e:
        e = f"{e}"
        if e not in ERRORLOG:
            ERRORLOG[e] = 1
        else:
            ERRORLOG[e] += 1
        if attempt < 3:
            attempt += 1
            time.sleep(60)
            print("[+] Retrying")
            SendView(url, proxy, attempt)
        else:
            SUBTHREADCOUNT -= 1

async def sendViewsOn(post_url,proxie,proxy_type,attempt=1):
    global SUBTHREADCOUNT,TOKENLOGS,ERRORLOG, VIEWSCOUNT
    SUBTHREADCOUNT += 1
    channel,post_id= post_url.replace("https://t.me/", "").split("/")
    subUrl =f'https://t.me/{channel}/{post_id}?embed=1&mode=tme'
    try:
        connector = ProxyConnector.from_url(proxie)
        
        
        timeout = aiohttp.ClientTimeout(total=10)
        cookiejar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(connector=connector,cookie_jar=cookiejar,timeout=timeout) as session:
            async with session.get(
                url=subUrl,
                headers={
                'referer': post_url,
                'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"}) as resp:
                html = Selector(text=await resp.text())

                stel_ssid = cookiejar.filter_cookies(resp.url).get("stel_ssid")
                views_token = html.xpath('//*[@data-view]/@data-view').get()

                if stel_ssid and views_token : # stel_ssid in  cookie
                    resp = await session.post(
                        url=f'https://t.me/v/?views={views_token}', 
                        headers={
                            'referer': subUrl,
                            'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                            'x-requested-with': 'XMLHttpRequest'},
                        timeout=timeout)
                    if resp.status == 200 and await resp.text() == "true":
                        VIEWSCOUNT[f"{channel}--{post_id}"] += 1
                        SUBTHREADCOUNT -= 1
                        return 1
        await asyncio.sleep(1)
        raise ValueError("Token Not Available")
    except Exception as e:
        e = f"{e}"
        if e not in ERRORLOG:
            ERRORLOG[e] = 1
        else:
            ERRORLOG[e] += 1
        if attempt < 3:
            attempt += 1
            time.sleep(60)
            if proxy_type == "r":
                proxy = newResidentialProxie()
            elif proxy_type == "d":
                proxy = newDatacenteredProxie(post_url)
            print(f"[+] Attempt {attempt}: {post_url} [+] Proxy : {proxy}")
            if proxy is None:
                SUBTHREADCOUNT -= 1
                print(f"[+] All available ips are used on : {post_url}")
                return
            await sendViewsOn(post_url,proxy,proxy_type, attempt)
        else:
            SUBTHREADCOUNT -= 1

def run_async_function(url,proxie,proxy_type):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(sendViewsOn(url,proxie,proxy_type))
    finally:
        loop.close()

def startSendingViews(url, requiredViews, proxy_type):
    post = sync_CheckViewOnPost(url)
    channel, post_id = url.replace("https://t.me/", "").split("/")
    
    VIEWSCOUNT[f"{channel}--{post_id}"] = post.views
    if requiredViews > post.views:
        post.requiredViews = requiredViews-post.views
        print("[+] Boosting Views On", post)
        for _ in range(requiredViews-post.views):
            if proxy_type == "r":
                proxy = newResidentialProxie()
            elif proxy_type == "d":
                proxy = newDatacenteredProxie(url)
            if proxy:
                Thread(target=run_async_function, args=(url, proxy,proxy_type,)).start()
                time.sleep(threadcreationinterval)

def sendReactionThreadWrapper(chanel_id,post_id):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(sendReactions(chanel_id,post_id))
    finally:
        loop.close()