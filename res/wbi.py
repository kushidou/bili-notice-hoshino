# 自 2023 年三月起，B站 Web 端部分接口开始使用 Wbi 鉴权方式，
# 一种独立于 APP 鉴权 与其他 Cookie 鉴权的方式
# 在 REST API 请求时在 query 中添加了w_rid和wts字段，为一种 Web 端的风控手段
# 同时抛弃了一部分api，
# https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/misc/sign/wbi.md

from functools import reduce
from hashlib import md5
import urllib.parse
import time
import httpx
p = {
    "all://":None
}
mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

img_key, sub_key = '', ''

header={'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-encoding': 'gzip, deflate, br', 
        'accept-language': 'zh-CN,zh;q=0.9', 
        'sec-ch-ua': '"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"', 
        'sec-fetch-dest': 'document', 
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none', 
        'sec-fetch-user': '?1', 
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58'
    }
        

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

async def getWbiKeys(): # sync to async
    '获取最新的 img_key 和 sub_key'
    
    async with httpx.AsyncClient(proxies=p) as client:
        resp = await client.get('https://api.bilibili.com/x/web-interface/nav', headers=header)
    if not resp.status_code == 200:
        return '', ''
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

async def update(): # sync to async
    global img_key, sub_key
    img_key, sub_key = await getWbiKeys()
    if img_key == '' and sub_key == '':
        return False
    return True

def encode(para:dict):
    global img_key, sub_key
    return encWbi(para, img_key, sub_key)

