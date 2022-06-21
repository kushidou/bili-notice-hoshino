import requests
import json 
import time
import os
from os.path import dirname, join, exists
from loguru import logger as log

from . import dymgr
import hoshino
from hoshino import Service, priv, get_bot

# bot服务初始化
sv=Service(
    name='b站动态监视器',
    use_priv = priv.NORMAL,
    manage_priv = priv.ADMIN,
    visible=True,
    enable_on_default=True
)



# 功能：轮询所有up主，有更新就发布
# 核心：dymgr.get_update()
# 返回结果为轮询结果(bool)、动态内容（list）
@sv.scheduled_job('interval', seconds=15)       # 时间可以按需调整，监视的up多就短一点。但是不能太短，至少5s吧，防止被屏蔽
async def bili_watch():
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
                await bot.send_group_msg(group_id=gid, message=msg)
                time.sleep(1)
        time.sleep(5)


# 功能：关注up主，更新文件，更新内存
# 核心： dymgr.follow(uid, group)
# 返回结果为 添加结果(bool)、原因或up主昵称
@sv.on_prefix("关注",only_to_me=True)
async def bili_add(bot, ev):
    global up_latest, up_list
    # 权限检查
    if not await check_rights(ev, level=0):
        await bot.send(ev, "你没有权限这么做")
        return
    # 提取信息，进行关注
    uid = ev.message.extract_plain_text()
    print(f'收到观察命令:UID={uid}, from {ev.group_id}')
    rst, res = dymgr.follow(uid, ev.group_id)
    if rst:
        msg = f'开始关注 {res}, ta更新时将会第一时间推送到群里哦~'
    else:
        print(f'关注失败，原因: {res}')
        msg = res
    await bot.send(ev,msg)


# 功能：取关up主，更新文件，更新内存
# 核心： dymgr.unfollow(uid, group)
# 返回结果为 执行结果(bool)、结果信息
@sv.on_prefix(["取关","取消关注"],only_to_me=True)
async def bili_add(bot, ev):
    global up_list
    if not await check_rights(ev, level=0):
        await bot.send(ev, "你没有权限这么做")
        return
    uid = ev.message.extract_plain_text()
    log.info(f'收到取关命令:UID={uid}, from {ev.group_id}')
    _, res = dymgr.unfollow(uid, ev.group_id)
    msg = res         
    await bot.send(ev,msg)


# 功能：类似指令执行的热配置
# 核心： dymgr.shell(group, para, right)
# 返回结果为 添加结果(bool)、原因或up主昵称
@sv.on_prefix("bili-ctl ")
async def bili_ctl(bot,ev):
    global up_group_info, up_list
    
    para = ev.message.extract_plain_text().split()
    right = await check_rights(ev, level=1)
    rst, res = dymgr.shell(ev.group_id, para, right)
    msg = res
    await bot.send(ev,msg)
    
async def check_rights(ev, level=0):
    # 返回权限是否通过。
    # 低等级（0）支持群管理和机器人管理员，高等级（1）仅支持机器人管理员
    ret = False
    if priv.check_priv(ev, priv.ADMIN):
        ret = True
    if not level:
        if priv.get_user_priv(ev) in [priv.OWNER, priv.ADMIN]:
            ret = ret or True
    return ret
