import time, os
import asyncio
from os.path import exists, join
# from loguru import logger as log
import configparser as cfg
from . import dymgr
from .res import wbi
import hoshino
from hoshino import Service, priv, get_bot


helpinfo='''
【b站动态监视器】
可以发布关注的up主哦。
发送[ bili-ctl help ]查看详细使用方式。

'''

# bot服务初始化
sv=Service(
    name='b站动态监视器',
    use_priv = priv.NORMAL,
    manage_priv = priv.ADMIN,
    visible=True,
    enable_on_default=True,
    help_=helpinfo
)
curpath = os.path.dirname(__file__)
# 读取配置文件
if not exists(join(curpath, 'config.ini')):
    try:
        os.rename(join(curpath, 'config_example.ini'),join(curpath, 'config.ini'))
    except:
        print("\r\n\033[1;41m[Error]\033[0m\tBili-notice:\tCannot Find config.ini or config_example.ini !!!")
conf = cfg.ConfigParser(allow_no_value=True)
conf.read(join(curpath, 'config.ini'), encoding='utf-8')
auth_follow = conf.get('authority','follow')
auth_cmd = conf.get('authority','cmd')
poll_time = conf.get('common','poll_time')

fo_nick = {}
'''
fo_nick={
    groupid:{
        nick = "str",
        uid = int,
        full = "full_uname",
        fun = "f/uf",
        time = int         比如说五分钟内答复，记录时间戳计算
    },
    groupid2:{
        ...
    }
}
'''


# 功能：轮询所有up主，有更新就发布
# 核心：dymgr.get_update()
# 返回结果为轮询结果(bool)、动态内容（list）
bot = get_bot() 


@sv.scheduled_job('interval', seconds=int(poll_time))       # 时间可以按需调整，监视的up多就短一点。但是不能太短，至少5s吧，防止被屏蔽
async def bili_watch():
    global fo_nick
    rst, dylist = await dymgr.get_update()
    if rst > 0:
        for dyinfo in dylist:
        
            bot=get_bot()
            if dyinfo["type"] == "转发":
                dytype = "转发了一条动态"
            else:
                dytype = f'发布了一个新{dyinfo["type"]}'

            msg = f'{dyinfo["nickname"]} {dytype}, 点击链接直达：\n {dyinfo["link"]}  \n[CQ:image,file={dyinfo["pic"]}]'
            for gid in dyinfo["group"]:
                for sid in hoshino.get_self_ids():
                    try:
                        await bot.send_group_msg(self_id = sid, group_id=gid, message=msg)
                    except Exception as e:
                        sv.logger.info(f'bot账号{sid}不在群{gid}中，将忽略该消息')
                # time.sleep(1)
                await asyncio.sleep(1)
        # time.sleep(5)
        await asyncio.sleep(5)
    elif rst < -1000:
        # 轮询到直播
        # 正在直播的数量为 abs(rst) - 1000
        for dyinfo in dylist:
            bot=get_bot()
            msg = f'{dyinfo["nickname"]} 在{dyinfo["type"]}区开始直播啦, 快去看看吧：\n {dyinfo["link"]}  \n[CQ:image,file={dyinfo["pic"]}]'
            for gid in dyinfo["group"]:
                for sid in hoshino.get_self_ids():
                    try:
                        await bot.send_group_msg(self_id = sid, group_id=gid, message=msg)
                    except Exception as e:
                        sv.logger.info(f'bot账号{sid}不在群{gid}中，跳过')
                # time.sleep(1)
                await asyncio.sleep(1)

    # 借助轮询处理一些时效性的内容
    rg=[]
    for g in fo_nick.keys():
        if int(time.time()) - fo_nick[g]["time"] > 1*60:
            rg.append(g)
    for g in rg:
        del fo_nick[g]
        print(f'群{str(g)}的昵称关注缓存超时了。 ')


# 功能：关注up主，更新文件，更新内存
# 核心： dymgr.follow(uid, group)
# 返回结果为 添加结果(bool)、原因或up主昵称
@sv.on_prefix("关注",only_to_me=True)
async def bili_add(bot, ev):
    global up_latest, up_list
    # 权限检查
    if not auth_cmd == 'all':
        l = 0 if auth_cmd=='group' else 1
        if not check_rights(ev, level=l):
            await bot.send(ev, "你没有权限这么做")
            return
    # 提取信息，进行关注
    keys = ev.message.extract_plain_text()
    sv.logger.info(f'收到关注命令:关键词={keys}, from {ev.group_id}')
    uid, uname, lev = await get_uid(keys)
    if lev == 1.0:
        rst, res = await dymgr.follow(str(uid), ev.group_id)
        if rst:
            msg = f'开始关注 {res} ,ta更新时将会第一时间推送到群里哦~'
        else:
            print(f'关注失败，原因: {res}')
            msg = res
    else:
        if uid == 0:
            msg = f"{keys}搜索失败~"
        else:
            print(f'记录关注信息，开始等待。')
            fo_nick[ev.group_id]={
                "nick" : keys,
                "uid" : uid,
                "full" : uname,
                "fun" : "f",
                "time" : int(time.time())
            }
            msg = f'要关注 {uname}({uid}) 吗? 发送 [是/否] 并 @我 哦~'
    await bot.send(ev,msg)

# 对于猜测对象的答复处理
@sv.on_fullmatch(["是","否","对"], only_to_me=True)
async def bili_answer_add(bot, ev):
    # 检查权限
    if not auth_cmd == 'all':
        l = 0 if auth_cmd=='group' else 1
        if not check_rights(ev, level=l):
            return
    grp = fo_nick.keys()
    if ev.group_id in grp:
        if int(time.time()) - fo_nick[ev.group_id]["time"] > 5*60:
            msg = '关注超时，请重新关注。' if fo_nick[ev.group_id]["fun"]=="f" else '取关超时，请重新取关'
        else:
            if not ev.message.extract_plain_text().replace(" ","") == "否":
                if fo_nick[ev.group_id]["fun"]=="f":
                    rst, res = await dymgr.follow(str(fo_nick[ev.group_id]["uid"]), ev.group_id)
                    if rst:
                        msg = f'开始关注 {res} ,ta更新时将会第一时间推送到群里哦~'
                    else:
                        print(f'关注失败，原因: {res}')
                        msg = res
                elif fo_nick[ev.group_id]["fun"]=="uf":
                    _, res = dymgr.unfollow(str(fo_nick[ev.group_id]["uid"]), ev.group_id)
                    msg = res
                # 答复是的时候，将该昵称记录为用户专属昵称
                rst = dymgr.save_uname_nick(str(fo_nick[ev.group_id]["uid"]), 
                                        fo_nick[ev.group_id]["full"], 
                                        fo_nick[ev.group_id]["nick"])
                if rst:
                    msg +=f'\r\n短昵称无法绑定，{rst}。'
            else:
                msg = "已取消。"
        del fo_nick[ev.group_id]
        await bot.send(ev,msg)


# 功能：取关up主，更新文件，更新内存
# 核心： dymgr.unfollow(uid, group)
# 返回结果为 执行结果(bool)、结果信息
@sv.on_prefix(["取关","取消关注"],only_to_me=True)
async def bili_remove(bot, ev):
    global up_list
    if not auth_cmd == 'all':
        l = 0 if auth_cmd=='group' else 1
        if not check_rights(ev, level=l):
            await bot.send(ev, "你没有权限这么做")
            return
    keys = ev.message.extract_plain_text()
    sv.logger.info(f'收到取关命令:UID={keys}, from {ev.group_id}')
    uid, uname, lev = await get_uid(keys)
    if lev == 1.0:
        _, res = dymgr.unfollow(str(uid), ev.group_id)
        msg = res   
    else:
        if uid == 0:
            msg = f'没有找到 {keys} 的有关信息。'
        else:
            print('记录取关信息，开始等待')
            fo_nick[ev.group_id]={
                "nick" : keys,
                "uid" : uid,
                "full" : uname,
                "fun" : "uf",
                "time" : int(time.time())
            }
            msg = f'要取关 {uname}({uid}) 吗? 发送 [是/否] 并 @我 哦~'
    await bot.send(ev,msg)


# 功能：类似指令执行的热配置
# 核心： dymgr.shell(group, para, right)
# 返回结果为 添加结果(bool)、原因或up主昵称
@sv.on_prefix("bili-ctl ")
async def bili_ctl(bot,ev):
    global up_group_info, up_list
    
    para = ev.message.extract_plain_text().split()
    l = 0 if auth_cmd=='group' else 1
    right = check_rights(ev, level=l)
    rst, res = await dymgr.shell(ev.group_id, para, right)
    msg = res
    await bot.send(ev,msg)

@sv.on_fullmatch(["本群关注","看看成分","关注列表"], only_to_me=True)
async def follow_list_group(bot,ev):
    rst, info = dymgr.get_follow(ev.group_id, level=0)
    await bot.send(ev, info)

@sv.on_fullmatch(["所有关注", "bili-list"])
async def follow_list_byuid(bot, ev):
    if check_rights(ev, level=1):
        rst, info = dymgr.get_follow_byuid("all", level=0)
        await bot.send(ev, info)

@sv.on_fullmatch(["所有群关注", "bili-list-group"])
async def follow_list_byuid(bot, ev):
    if check_rights(ev, level=1):
        rst, info = dymgr.get_follow_bygrp("all", level=0)
        await bot.send(ev, info)
    
def check_rights(ev, level=0):
    # 返回权限是否通过。
    # 低等级（0）支持群管理和机器人管理员，高等级（1）仅支持机器人管理员
    ret = False
    if priv.check_priv(ev, priv.ADMIN):
        ret = True
    if not level:
        if priv.get_user_priv(ev) in [priv.OWNER, priv.ADMIN]:
            ret = ret or True
    return ret


async def get_uid(i:str):
    i = i.replace(" ","").replace("\r","").replace("\n","")
    if i.isdigit():
        return i, "", 1.0
    else:
        uid, full_uname, nick, l = await dymgr.guess_who(i)
        print(f'昵称关注模式，查询 {nick}: 得到结果：uid={uid}, f_uname={full_uname}, 相似率={l}')
        return uid, full_uname, l


@sv.on_prefix(["搜索up"])
async def bili_search_up(bot, ev):

    keys = ev.message.extract_plain_text()
    uid, who = await dymgr.search_up_in_bili(keys)
    msg = f'搜索到up主{who}[{uid}]'
    await bot.send(ev,msg)