import requests
import json 
import time
import os
from os.path import dirname, join, exists
# from PIL import Image

from .res import drawCard
import hoshino
from hoshino import Service, log, priv, get_bot


# 程序初始化代码
curpath = dirname(__file__)
watcher_file = join(curpath, 'upperlist.json')
res_dir = join(curpath,'res/')
up_dir = join(curpath,'uppers/')

sv=Service(
    name='b站动态监视器',
    use_priv = priv.NORMAL,
    manage_priv = priv.ADMIN,
    visible=True,
    enable_on_default=True
)

number = 0
up_latest = {}
up_list=[]


# 从文件中读取up主配置列表和up主发送动态的历史
if os.path.exists(up_dir + 'list.json'):
    with open(join(up_dir,'list.json'), 'r') as f:
        up_group_info = json.load(f)

    for uid in list(up_group_info.keys()):
        if os.path.exists(up_dir+uid+'.json'):
            with open(up_dir+uid+'.json','r') as f:
                up_latest[uid] = json.load(f)["history"]
        else:
            up_latest[uid]=[]
            with open(up_dir+uid+'.json','w') as f:
                json.dump({"history":[]}, f, ensure_ascii=False)
    up_list = list(up_group_info.keys())

# 主要功能实现
# 轮询订阅，解析动态，发送动态信息
async def get_update():
    global number,up_latest, up_list
    msg,dyimg,dytype = None,None,None
    
    maxcount = len(up_list)
    while 1:
        this_up = up_group_info[up_list[number]]
        if this_up["watch"] == True:                # 跳过不监控的up
            if len(this_up["group"]) == 0:          # 如果没有群关注up，就更改状态为不监控
                up_group_info[up_list[number]]["watch"]=False
                with open(join(up_dir,'list.json'), 'w') as f:
                    json.dump(up_group_info, f, ensure_ascii=False)
                continue            # 状态更新完成，下一个
            else:
                break               # up主状态正常，跳出循环
        else:
            if maxcount <= 0:       # 避免死循环不跳出
                return
            else:
                maxcount = maxcount -1
            if number+1>=len(up_list):          # 最多进行一轮
                number = 0
            else:
                number = number+1
        
        
    
    group_list = this_up["group"]
    if this_up["watch"]:
        
        uid_str = up_list[number]
        try:
            res = requests.get(url=f'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid_str}' )
        except:
            print('Err: Get dynamic list failed.')
        dylist = json.loads(res.text)
        dynamic = drawCard.Card(dylist)

        if not dynamic.nickname == this_up["uname"]:
            up_group_info[up_list[number]]["uname"] = dynamic.nickname
            with open(join(up_dir,'list.json'), 'w') as f:
                json.dump(up_group_info, f, ensure_ascii=False)

        
        if dynamic.dyid not in up_latest[up_list[number]]:  # 查到新的动态
            print(f'Start watch {this_up["uname"]} ==> New Dynamic id={dynamic.dyid}, type = {dynamic.dytype}')
            up_latest[uid_str].append(dynamic.dyid)         # 把动态加入肯德基豪华午餐
            with open(up_dir+uid_str+'.json','w') as f:
                    json.dump({"history":up_latest[uid_str]}, f, ensure_ascii=False)
            if not dynamic.check_black_words(this_up["ad_keys"]):  # 如果触发过滤关键词，则忽视该动态
                if dynamic.is_realtime(30):             # 太久的动态不予发送
                # if True:
                    drawBox = drawCard.Box(650, 1200)
                    dyimg, dytype = dynamic.draw(drawBox)
                
                    msg = f"{dynamic.nickname} {dytype}, 点击连接直达：\n https://t.bilibili.com/{dynamic.dyidstr}  \n[CQ:image,file={dyimg}]"
                    group_list = this_up["group"]
                    
                else:
                    print(f"this is too old.{(dynamic.dytime - int(time.time()))/60}")
    number = 0 if number+1>=len(up_list) else number+1
    return msg, group_list




@sv.scheduled_job('interval', seconds=30)       # 时间可以按需调整，监视的up多就短一点。但是不能太短，至少15s吧，防止被屏蔽
async def bili_watch():
    global up_latest, up_list
    if up_list:
        msg, grp = await get_update()
        if msg:
            bot=get_bot()
            for gid in grp:
                await bot.send_group_msg(group_id=gid, message=msg)
                # print(f'Send Dynamic message to {gid}')




@sv.on_prefix("关注",only_to_me=True)
async def bili_add(bot, ev):
    global up_latest, up_list
    uid = ev.message.extract_plain_text()
    print(f'收到观察命令:UID={uid}, from {ev.group_id}')
    if not uid.isdigit():
        msg = '请输入正确的UID!'
    else:
        if uid not in up_list:  # 从未添加过
            try:
                res = requests.get(url=f'http://api.bilibili.com/x/space/acc/info?mid={uid}')
            except:
                
                msg="网络出错了，请稍后再试~"
                await bot.send(ev,msg)
                return

            resj = json.loads(res.text)
            if not resj["code"] == 200:
                upinfo = {}
                upinfo["uid"]   = int(uid)
                upinfo["uname"] = resj["data"]["name"]
                upinfo["group"] = [ev.group_id]
                upinfo["watch"] = True
                upinfo["islucky"]= False
                upinfo["ad_keys"]= ["恰饭","广告"]

                up_group_info[uid]=upinfo
                with open(join(up_dir,'list.json'), 'w') as f:      # 更新UP主列表
                    json.dump(up_group_info, f, ensure_ascii=False)  

                with open(up_dir+uid+'.json','w') as f:             # 给up主创建和添加动态历史列表
                    json.dump({"history":[]}, f, ensure_ascii=False)
                    print(f'add {upinfo["uname"]}({uid}) history json to {up_dir+uid}.json')

                up_list = list(up_group_info.keys())

                up_latest[uid]=[]

                msg=f'开始关注 {upinfo["uname"]}[{uid}], ta更新时将会第一时间推送到群里哦~'
            else:
                msg = "UID有误。"
        else:                       # 已经关注过了，那么只需要添加group
            if ev.group_id in up_group_info[uid]["group"]:
                msg = "已经关注过惹~"
            else:    
                up_group_info[uid]["group"].append(ev.group_id)
                with open(join(up_dir,'list.json'), 'w') as f:
                    json.dump(up_group_info, f, ensure_ascii=False)  
                msg=f'开始关注 {up_group_info[uid]["uname"]}[{uid}], ta更新时将会第一时间推送到群里哦~'

    await bot.send(ev,msg)

@sv.on_prefix(["取关","取消关注"],only_to_me=True)
async def bili_add(bot, ev):
    global up_latest, up_list
    uid = ev.message.extract_plain_text()
    if not uid.isdigit():
        msg = '请输入正确的UID!'
    else:
        if uid not in up_list:
            msg="没有关注ta哦~"
        else:
            if ev.group_id not in up_group_info[uid]["group"]:
                msg="没有关注ta哦~"
            else:
                up_group_info[uid]["group"].remove(ev.group_id)
                with open(join(up_dir,'list.json'), 'w') as f:
                    json.dump(up_group_info, f, ensure_ascii=False)
                del up_latest[uid]
                msg = "已经取关惹~"
    msg = msg + '\n (这个功能还待完善)'                
    await bot.send(ev,msg)



