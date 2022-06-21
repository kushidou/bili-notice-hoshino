import json, requests, time
import configparser as cfg
import os
from os.path import dirname, join, exists
from .res import drawCard
from loguru import logger as log

available_type=[
    2,      # Picture
    4,      # text
    8,      # video
    64      # article
]

help_info="""=== bili-notice-hoshino 帮助 ===
    
bili-ctl para1 para2 para3 [...]
关键词过滤  black-words  uid  add/remove 拼多多 pdd ... 
查看关键词  black-words  uid  list  
开奖动态   islucky  uid  true/false
立即更新    update
帮助菜单   help
*功能性指令只能由机器人管理员操作*"""


curpath = dirname(__file__)
watcher_file = join(curpath, 'upperlist.json')
res_dir = join(curpath,'res/')
up_dir = join(curpath,'uppers/')


number = 0
up_latest = {}
up_list=[]

# 初始化日志系统
drawCard.initlog()

# 读取配置文件
conf = cfg.ConfigParser()
conf.read(join(curpath, 'config.ini'), encoding='utf-8')

# 从文件中读取up主配置列表和up主发送动态的历史
if exists(up_dir + 'list.json'):
    with open(join(up_dir,'list.json'), 'r') as f:
        up_group_info = json.load(f)

    for uid in list(up_group_info.keys()):
        if exists(up_dir+uid+'.json'):
            with open(up_dir+uid+'.json','r') as f:
                up_latest[uid] = json.load(f)["history"]
        else:
            up_latest[uid]=[]
            with open(up_dir+uid+'.json','w') as f:
                json.dump({"history":[]}, f, ensure_ascii=False)
    up_list = list(up_group_info.keys())



async def get_update():
    """主要功能实现，轮询各up，解析动态列表，发送最新的动态信息和卡片

    Returns:
        _type_: _description_
        rst(num):    返回动态结果和数量
        dylist(list):   具体的动态内容

        rst = 0     无更新
        rst = 1     得到更新（数量）
        rst = -1    关键词或转发抽奖验证不通过（被过滤，数量）
        如果连续有多条动态，那么只会返回正常发送的数量，不会返回-1。
        如果多条动态都是被过滤的，那么返回-n

        dylist = {
            nickname:   str     (昵称，字符串)
            uid：       num     (uid，数字)
            type:       num/str (动态类型，由配置文件决定)
            subtype:    num     (动态子类型。如果非转发，则subtype=type，不会留空)
            time:       num/str (时间戳或字符串时间，配置文件决定)
            pic:        str     (base64编码的图片)
            link:       str     (动态的链接)
            sublink:    str     (如果是视频文章等，这里写他们的链接。普通动态与link相同)
            group:      list    (需要发给的群,[num])
        }

        
    """
    global number,up_latest, up_list
    msg,dyimg,dytype = None,None,None
    rst, suc, fai=0,0,0
    dynamic_list=[]
    
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
            log.info('Err: Get dynamic list failed.')
        dylist = json.loads(res.text)
        dynamic = drawCard.Card(dylist)

        if not dynamic.nickname == this_up["uname"]:
            up_group_info[up_list[number]]["uname"] = dynamic.nickname
            with open(join(up_dir,'list.json'), 'w') as f:
                json.dump(up_group_info, f, ensure_ascii=False)

        
        if dynamic.dyid not in up_latest[up_list[number]]:  # 查到新的动态
            log.info('========== New Dynamic Card =========')
            log.info(f"UP={dynamic.nickname}({dynamic.uid}), Dynamic_id={dynamic.dyid}, Type={int(dynamic.dytype)}")
            
            if not dynamic.check_black_words(this_up["ad_keys"], this_up["islucky"]):  # 如果触发过滤关键词，则忽视该动态
                if dynamic.is_realtime(30):             # 太久的动态不予发送
                # if True:
                    if dynamic.dytype in available_type or (dynamic.dytype==1 and dynamic.dyorigtype in available_type):
                        drawBox = drawCard.Box(650, 1200)
                        dyimg, dytype = dynamic.draw(drawBox)
                
                        msg = f"{dynamic.nickname} {dytype}, 点击链接直达：\n https://t.bilibili.com/{dynamic.dyidstr}  \n[CQ:image,file={dyimg}]"
                        group_list = this_up["group"]
                        suc+=1
                        dyinfo = {
                            "nickname": dynamic.nickname,
                            "uid":      dynamic.dyid,
                            "type":     dytype,
                            "subtype":  dynamic.dyorigtype,
                            "time":     dynamic.dytime,         # 时间戳，非字符串时间
                            "pic":      dyimg,
                            "link":     f'https://t.bilibili.com/{dynamic.dyidstr}',
                            "sublink":  "",
                            "group":    group_list
                        }
                        dynamic_list.append(dyinfo)
                    
                else:
                    log.info(f"This dynamic({dynamic.dyid}) is too old: {(int(time.time()) - dynamic.dytime)/60} minutes ago")
                    fai -=1
            else:
                log.info("({dynamic.dyid})触发过滤词，或者是转发抽奖动态。")
                fai -= 1 
    number = 0 if number+1>=len(up_list) else number+1

    up_latest[uid_str].append(dynamic.dyid)         # 完成后把动态加入肯德基豪华午餐
    with open(up_dir+uid_str+'.json','w') as f:
            json.dump({"history":up_latest[uid_str]}, f, ensure_ascii=False)
    rst = fai if suc==0 else suc
    return rst, dynamic_list


def follow(uid, group):
    global number,up_latest, up_list
    """关注UP主，并创建和修改对应的记录文件

    Args:
        uid (num): up主的uuid，仅接受通过uuid来关注
        gruop (num): 申请的群

    Returns:
        rst (bool): 申请的结果。
        msg (str):  结果的原因。成功后是  昵称[id]
    """
    if not uid.isdigit():
        msg = '请输入正确的UID!'
        log.info(f"关注失败，UID错误: {uid}")
        return False, msg

    if uid not in up_list:  # 从未添加过
        try:
            para={"mid":str(uid)}
            header = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Connection': 'keep-alive',
                'Host': 'api.bilibili.com',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.124 Mobile Safari/537.36 Edg/102.0.1245.44'
            }
            res = requests.get(url=f'http://api.bilibili.com/x/space/acc/info', params=para, headers=header)
        except:
            msg="网络出错了，请稍后再试~"
            log.info('关注失败，网络错误')
            return False, msg

        resj = json.loads(res.text)
        if not resj["code"] == 200:
            if resj["code"] == 0:
                upinfo = {}
                upinfo["uid"]   = int(uid)
                upinfo["uname"] = resj["data"]["name"]
                upinfo["group"] = [group]
                upinfo["watch"] = True
                upinfo["islucky"]= False
                upinfo["ad_keys"]= ["恰饭","广告"]

                up_group_info[uid]=upinfo
                try:
                    with open(join(up_dir,'list.json'), 'w') as f:      # 更新UP主列表
                        json.dump(up_group_info, f, ensure_ascii=False)  

                    with open(up_dir+uid+'.json','w') as f:             # 给up主创建和添加动态历史列表
                        json.dump({"history":[]}, f, ensure_ascii=False)
                        print(f'add {upinfo["uname"]}({uid}) history json to {up_dir+uid}.json')

                    up_list = list(up_group_info.keys())

                    up_latest[uid]=[]
                except:
                    msg="UP主文件写入失败，未知错误，请手动检查配置文件。"
                    log.info('关注失败,无法修改list文件或无法创建用户记录文件')
                    return False,msg

                msg=f'{upinfo["uname"]}[{uid}]'
            else:
                msg = f'服务器错误(code={resj["code"]}, message={resj["message"]})'
                log.info(f'关注失败，服务器返回(code={resj["code"]}, message={resj["message"]})')
                return False, msg
        else:
            msg = "UID有误。"
            log.info(f'关注失败，查无此人(输入{uid})')
            return False, msg
    else:                       # 已经关注过了，那么只需要添加group
        if group in up_group_info[uid]["group"]:
            log.info(f'关注失败，已经关注过了')
            msg = "已经关注过惹~"
            return False,msg
        else:    
            up_group_info[uid]["group"].append(group)
            try:
                with open(join(up_dir,'list.json'), 'w') as f:
                    json.dump(up_group_info, f, ensure_ascii=False)
            except:
                log.info('关注失败,无法修改list文件或无法创建用户记录文件')
                return False, "UP主文件写入失败，未知错误，请手动检查配置文件。"
            msg=f'{up_group_info[uid]["uname"]}[{uid}]'
    log.info('关注成功，群: {group}，用户: {up_group_info[uid]["uname"]}({uid})')
    return True, msg


def unfollow(uid, group):
    global number,up_latest, up_list
    """取关UP主，并更新有关文件

    Args:
        uid (num): 被取关的UP主ID
        group (num): 申请取关的群

    Returns:
        bool: 执行结果。
        str:  结果信息。
    """
    rst = False
    msg = "未知错误。"
    if not uid.isdigit():
        msg = '请输入正确的UID!'
        log.info(f'取关失败，UID错误: "{uid}"')
    else:
        if uid not in up_list:
            msg="没有关注ta哦~"
            log.info(f'取关失败，该用户({uid})从未添加。')
        else:
            if group not in up_group_info[uid]["group"]:
                msg="没有关注ta哦~"
                log.info(f'取关失败，该群({group})未关注用户({uid})')
                log.debug(f'用户{uid} 被关注的群包含{up_group_info[uid]["group"]}')
            else:
                try:
                    up_group_info[uid]["group"].remove(group)
                    with open(join(up_dir,'list.json'), 'w') as f:
                        json.dump(up_group_info, f, ensure_ascii=False)
                    del up_latest[uid]
                except:
                    log.info('取关失败,无法修改list文件')
                    return False, "UP主文件修改失败，未知错误，请手动检查配置文件。"
                msg = f'已经取关{up_group_info[uid]["uname"]}({uid})惹~'
                rst = True
                log.info(f'取关成功，群: {group}，用户: {up_group_info[uid]["uname"]}({uid})')
    return rst, msg


def shell(group, para, right):
    """类指令的热管理工具

    Args:
        group (num): 发起设置的群号
        para (str): 完整指令
        right (bool): 权限判断。
    """
    global up_group_info, up_list
    msg = '指令有误，请检查! "bili-ctl help" 可以查看更多信息'
    try:
        cmd = para[0]
    except:
        cmd = "help"
    paranum = len(para)

    if cmd == "black-words":
        if paranum >= 3:
            uid = para[1]
            fun = para[2]
            if uid not in up_list:
                msg = 'UP主未关注,请检查uid!'
            else:
                if fun == "list":
                    uname = up_group_info[uid]["uname"]
                    msg = f'您已经为 {uname} 设置了以下过滤关键词：\r\n{up_group_info[uid]["ad_keys"]}'
                elif fun == "add":
                    if not right:
                        return False, "你没有权限这么做"
                    if paranum >3:
                        keys = para[3:]
                        try:
                            up_group_info[uid]["ad_keys"].extend(keys)
                            with open(join(up_dir,'list.json'), 'w') as f:      # 更新UP主列表
                                json.dump(up_group_info, f, ensure_ascii=False)
                            msg = f'添加成功.'
                        except:
                            msg = f'添加失败'
                elif fun == "remove":
                    if not right:
                        return False, "你没有权限这么做"
                    if paranum>3:
                        keys = para[3:]
                        erkeys=[]
                        for wd in keys:
                            try:
                                up_group_info[uid]["ad_keys"].remove(wd)
                            except:
                                erkeys.append(wd)
                        with open(join(up_dir,'list.json'), 'w') as f:      # 更新UP主列表
                            json.dump(up_group_info, f, ensure_ascii=False)
                        msg = '移除成功。'
                        if erkeys:
                            msg = msg+f'以下关键词移除失败，可能是没有这些关键词:\n{erkeys}'
    elif cmd == "islucky":
        if not right:
            return False, "你没有权限这么做"
        if paranum == 3:
            uid = para[1]
            fun = para[2]
            if uid not in up_list:
                msg = 'UP主未关注,请检查uid!'
            else:
                msg = f'已为 {up_group_info[uid]["uname"]} 更新抽奖开奖动态的设置。'
                if fun.upper() == "TRUE":
                    up_group_info[uid]["islucky"] = True
                elif fun.upper() == "FALSE":
                    up_group_info[uid]["islucky"] = False
                else:
                    msg = "参数错误，请重试。"
                with open(join(up_dir,'list.json'), 'w') as f:      # 更新UP主列表
                            json.dump(up_group_info, f, ensure_ascii=False)
    elif cmd.upper() == "UPDATE":
        if not right:
            return False, "你没有权限这么做"
        with open(join(up_dir,'list.json'), 'r') as f:
            up_group_info = json.load(f)
        msg = "信息更新完成!"

    elif cmd == "help":
        msg = help_info

    msg = msg.replace("'", '')
    msg = msg.replace('[','')
    msg = msg.replace(']','')
    print(f'bili-ctl return msg: {msg}')
    return True, msg