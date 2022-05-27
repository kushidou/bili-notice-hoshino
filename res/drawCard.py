import os, json, time, io, re, base64
from loguru import logger as log

from math import ceil
from os.path import dirname, join, exists
from PIL import Image,ImageFont,ImageDraw,ImageFilter

from .getImg import get_ico, get_Image, round_mask

# Init log system
path_log = join(dirname(__file__), "../log/")
if not exists(path_log):
    os.mkdir(path_log)
log.add(
    path_log+'drawCard_{time:YYYY-MM-DD}.log',
    level="DEBUG",
    rotation="04:00",
    retention="7 days",
    backtrace=True,
    enqueue=True,
    diagnose=False,
    format='{time:MM-DD HH:mm:ss} [{level}]\t{module}.{function}({line}): {message}'
)


# 生成动态卡片的具体代码
# 各个程序，传入参数为json代码和子卡片标志
#   （转发动态也是传入整串json代码，由他调用其他的卡片绘制）
class Card(object):
    # important to outside:
    # Card.dyid, .dytime, .dytype, .nickname
    def __init__(self, dylist: dict):
        # 初始化时，解析部分基础信息，然后判断Type等
        self.latest = dylist["data"]["cards"][0]
        self.dytype = self.latest["desc"]["type"]
        self.dyid   = self.latest["desc"]["dynamic_id"]
        self.dyidstr= self.latest["desc"]["dynamic_id_str"]
        self.dytime = self.latest["desc"]["timestamp"]
        self.nickname=self.latest["desc"]["user_profile"]["info"]["uname"]
        card_content= self.latest["card"]
        while True:
            if card_content.count('\\\\"') >= 1 or card_content.count('\\\\/') >= 1:
                card_content = card_content.replace('\\\\','\\')
                
            else:
                # card_content = card_content.replace('\\/','/')
                # card_content = card_content.replace('\\"','"')
                # card_content = card_content.replace('"{','{')
                # card_content = card_content.replace('}"','}')
                # card_content = card_content.replace('\} ?\]"', '} ]')
                # card_content = card_content.replace('"\[ ?\{', '[ {')
                # 升级为正则替换
                card_content = re.sub(r'\\+\/', '/', card_content)
                card_content = re.sub(r'\\+\"', '"', card_content)
                card_content = re.sub(r'\" ?\{', '{', card_content)
                card_content = re.sub(r'\} ?\"', '}', card_content)
                card_content = re.sub(r'\} ?\]\"', '} ]', card_content)
                card_content = re.sub(r'\"\[ ?\{', '[ {', card_content)
                # print(card_content)
                log.trace(f'card detail content = {card_content}')
                break
        self.card=json.loads(card_content)
        if not self.dyid == int(self.dyidstr):
            self.dyid = int(self.dyidstr)
        self.extra = {} # 各种变蓝文字的信息
        log.trace(f'Object decode finish. UID={self.nickname}, Type={int(self.dytype)}')
        
    
    def is_realtime(self, timeinterval: int):
        return False if timeinterval*60 < (int(time.time()) - self.dytime) else True

    def check_black_words(self, blk):
        ret = False
        for b in blk:
            if json.dumps(self.card).count(b):
                ret = True
                log.debug(f'Find black word(s) {b} in dynamic {self.dyidstr}, which is posted by {self.nickname}')
        return ret


    @log.catch
    def draw(self, box:object()):
        # 解析通用的信息，并绘制头像、昵称、背景、点赞box，然后调用其他绘制动态主体，最后把所有box合成
        # 制作头像  == faceimg ==
        log.info("Start Draw dynamic card: UID={self.nickname}, Type={int(self.dytype)}")
        face=get_Image(Type="face",url=self.latest["desc"]["user_profile"]["info"]["face"])
        face_pendant_url= self.latest["desc"]["user_profile"]["pendant"]["image"]
        if not face_pendant_url == "":
            face_pendant = get_Image(Type="pendant", url=face_pendant_url)
            log.debug("Get pendant success.")
        else:
            face_pendant=None
            log.debug("NO pendant around his/her face.")
        avatar_type = self.latest["desc"]["user_profile"]["card"]["official_verify"].get("type")
        if avatar_type == 1:   #企业认证
            face_avatar = get_ico('group')
            log.debug('This is an account of Group.')
        elif avatar_type == 0:     #个人认证
            face_avatar = get_ico('persional')
            log.debug('This is an account of Professional Persion')
        elif avatar_type == -1:
            avatar_url = self.latest["desc"]["user_profile"]["vip"]["avatar_subscript_url"]
            if not avatar_url == "":
                face_avatar = get_Image(Type="avatar",url=avatar_url)
                log.debug('This is an account of BigVIP(Year)')
            else:
                face_avatar = None
                log.debug('This is a normal persion.')
        faceimg = box.face(face, pendant=face_pendant, avatar_subscript=face_avatar)

        # 制作昵称  == nickimg ==
        nickname = self.latest["desc"]["user_profile"]["info"]["uname"]
        isVIP    = True if (self.latest["desc"]["user_profile"]["vip"]["vipType"] == 2) else False
        pubtime  = time.strftime("%y-%m-%d %H:%M", time.localtime(float(self.dytime)))
        nickimg = box.nickname(nick=nickname, time=pubtime, isBigVIP=isVIP)

        #制作一键三连   == bottom ==
        sharenum   = self.latest["desc"]["repost"]
        if self.dytype in [1,2,4]:
            commentnum = self.latest["desc"]["comment"]
        if self.dytype == 8:
            commentnum = self.card["stat"]["reply"]
        else:
            commentnum = 114514
        likenum    = self.latest["desc"]["like"]
        bottomimg = box.bottom(sharenum, commentnum, likenum)

        #根据类型制作body  ==  body ==
        # == 准备有关材料 ==
        self.extra = analyze_extra(self.latest, self.card)
        ret_txt=""
        # print(self.extra)
        if self.dytype == 1:    #转发   
            bodyimg = self.drawRepost(self.card, box)
            ret_txt="转发了一则动态"
        elif self.dytype == 2:  #图片
            bodyimg = self.drawImage(self.card, box)
            ret_txt="发布了新图文动态"
        elif self.dytype == 4:  #文字
            bodyimg = self.drawobj(self.card, box)
            ret_txt="发布了新动态"
        elif self.dytype == 8:  #视频
            bodyimg = self.drawVideo(self.card, box)
            ret_txt="发布了一条新视频"
        elif self.dytype == 16:  #小视频
            bodyimg = self.drawsmallVideo(self.card, box)
            ret_txt="发布了一条小视频"
        elif self.dytype == 64: #专栏
            bodyimg = self.drawArticle(self.card, box)
            ret_txt="发布了一篇专栏文章"
        elif self.dytype == 256: #番剧
            bodyimg = self.drawBangumi(self.card, box)
            ret_txt="发布了一集番剧"
        elif self.dytype == 2048:    #H5
            bodyimg = self.drawH5Event(self.card, box)
            ret_txt="H5动态"
        elif self.dytype == 2049:   #漫画
            bodyimg = self.drawComic(self.card, box)
            ret_txt="漫画"
        else:
            bodyimg = Image.new('RGBA', (50,50), 'white')
            ret_txt=""


        #根据所有的长度制作背景图   == bg ==
        length = 27 + nickimg.size[1] + 4 + bodyimg.size[1] + 4 + bottomimg.size[1]
        bgcard = self.latest["desc"]["user_profile"].get("decorate_card")
        if bgcard:
            # print("Find Fans background (number)")
            card_url     = bgcard["card_url"]
            decorate_img = get_Image(Type="decorate_card", url=card_url)
            decorate_col = bgcard["fan"]["color"]
            decorate_num = bgcard["fan"]["num_desc"]
            if decorate_col == "":
                decorate_col = (0,0,0)
        else:
            decorate_img = None
            decorate_col = (0,0,0)
            decorate_num = 0
            log.debug('No card background.')
        bgimg = box.bg(height=length, decorate_card=decorate_img, fan_number=decorate_num, fancolor=decorate_col)

        log.debug(f'Height of dynamic pic = {length}. Start splicing.')
        bgimg.paste(faceimg, (9,9), mask=faceimg)
        bgimg.paste(nickimg, (88,27), mask=nickimg)
        if self.dytype == 1:
            bgimg.paste(bodyimg, (76,75), mask=bodyimg)
        else:
            bgimg.paste(bodyimg, (88,75), mask=bodyimg)
        bgimg.paste(bottomimg, (88, length-48), mask=bottomimg)

        bio = io.BytesIO()
        bgimg.save(bio, format="PNG")
        base64_img = 'base64://' + base64.b64encode(bio.getvalue()).decode()

        return base64_img, ret_txt
        

    #Type=1     转发    repost
    def drawRepost(self, content, box, is_rep=False):
        # 解析出现在动态内容、原始动态信息
        # 先按类型绘制原始动态,贴身灰色背景，然后绘制当前动态（纯文字），拼接，最后返回完整图片
        log.info('Type = Repost')
        orname =content["origin_user"]["info"]["uname"]
        orface = get_Image(Type = "face", url=content["origin_user"]["info"]["face"])

        img_now = box.text(content["item"]["content"], self.extra)

        oritype = self.latest["desc"]["orig_type"]
        if oritype == 2:    # 转发带图动态
            img_ori = self.drawImage(content["origin"], box, is_rep=True)
        elif oritype == 4:  # 转发别人的动态
            img_ori = self.drawobj(content["origin"], box, is_rep=True)
        elif oritype == 8:  # 转发视频
            img_ori = self.drawVideo(content["origin"], box, is_rep=True)

        img = box.repost(orface, orname, img_now, img_ori)
        return img


    # Type=2    图片动态    Image
    def drawImage(self, content, box, is_rep=False):
        # 文字部分
        text = content["item"]["description"]
        # img = box.text(text, self.extra)

        #图片部分
        pics = []
        url_list=[]
        pic_count = content["item"]["pictures_count"]
        for picinfo in content["item"]["pictures"]:
            pics.append(get_Image(Type='image', url=picinfo["img_src"]))

        img = box.image(content=text, ex=self.extra, pics=pics, pic_count=pic_count, is_reposted=is_rep)
        return img



    # Type=3    文字动态    obj
    def drawobj(self, content, box, is_rep=False):
        #解析出文字内容，白色背景。if repost，那么需要绘制原始动态的头像、昵称、时间以及灰色背景
        text = content["item"]["content"]
        img = box.text(text, self.extra, is_reposted=is_rep)

        return img

    # Type=8    发布视频    Video
    def drawVideo(self, content, box, is_rep=False):
        title = content["title"]
        desc_text = content["desc"]
        dy_text = content["dynamic"]
        coverurl = content["pic"]
        viewnum = content["stat"]["view"]
        danmunum = content["stat"]["danmaku"]
        is_coop = content["rights"]["is_cooperation"]
        link = content["short_link"]

        cover = get_Image(Type="cover",url=coverurl)

        img=box.video(title,desc_text, viewnum, danmunum, cover, is_coop, dy_text, is_reposted=is_rep)
        exinfo="abc"
        return img

    # Type=16   小视频      smallVideo      ( 其实叫短视频，但我突然就像这么称呼了。根据实际测试小视频的卡片和正常视频差不多)
    def drawsmallVideo(self, content, box, is_rep=False):
        pass

    # Type=64   专栏        Article
    def drawArticle(self, content, box, is_rep=False):
        pass

    # Type=256  番剧        Bangumi         （使用b站官号的一条动态来渲染）
    def drawBangumi(self, content, box, is_rep=False):
        pass

    # Type=2048 H5活动      H5Event
    def drawH5Event(self, content, box, is_rep=False):
        pass

    # Type=2049 霹雳霹雳慢话
    def drawComic(self, content, box, is_rep=False):
        pass



class Box(object):
    # box对象包含一组函数，用来按照box的形式绘制各个元素，最后再合成动态图片
    # 这个类不能接触到获取图片的操作，所有图片、文字等信息都需要调用时传入
    # 如果两个元素有白色间隔，那么由左边、上面的box带上，算入该box高度。
    #   除了底部互动栏自带向上的间隔！

    # self.maxheight = 600
    # self.width = 300
    # self.minheight = 100

    def __init__(self, width, max_height):
        self.maxheight = max_height
        self.width = width
        self.minheight = int(width / 2)
        self.path = dirname(__file__)
        self.msyh = join(self.path, 'fonts/pinfang.ttf')
        self.fanfont = join(self.path, 'fonts/fans_num.ttf')

    # ====================box.combine====================
    # 按顺序组合box，计算整体长度
    # 其中背景、...
    # 大概不需要这个了


    # ====================box.face()====================
    # 绘制头像box，输入参数有头像、头像框、右下角标（大会员、蓝黄闪电），图片对象
    # return 图片对象
    # offset 9,9
    def face(self, face, pendant=None, avatar_subscript=None):
        fsize,psize,asize = 42, 72, 18
        img = Image.new('RGBA', (psize,psize), color=(0,0,0,0))
        # round face mask
        mask = Image.new('RGBA', (fsize*2, fsize*2), color=(0,0,0,0))
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse(((0,0) +(fsize*2,fsize*2)), fill=(0,0,0,255))
        mask = mask.resize((fsize,fsize), Image.ANTIALIAS)

        face = face.resize((fsize,fsize), Image.ANTIALIAS)
        img.paste(face, (15,15), mask=mask)

        if not pendant == None:
            pendant = pendant.resize((psize,psize), Image.ANTIALIAS)
            img.paste(pendant, (0,0), mask=pendant)

        if not avatar_subscript == None:
            avatar_subscript = avatar_subscript.resize((asize,asize), Image.ANTIALIAS)
            img.paste(avatar_subscript, (38,39), mask=avatar_subscript)
        self.face_img = img
        return img


    # ====================box.nickname====================
    # 绘制名称、时间等元素，字符串
    # 昵称字号约16，行高24；时间字号12，行高18；行间距4；卡片总长度570，总高度46
    # 4 -> 16(nickname) -> 4 + 4 + 3 -> 12(time) -> 3
    # return 图片对象
    # offset 88,27
    def nickname(self, nick, time, isBigVIP=False):
        img = Image.new('RGBA', (self.width - 88, 46), (0,0,0,0))
        draw = ImageDraw.Draw(img)

        font = ImageFont.truetype(self.msyh, 18)
        nick_color = (251, 114, 153, 255) if isBigVIP else (32,32,32,255)
        draw.text((0,3), nick, fill=nick_color,font=font)
        
        font = ImageFont.truetype(self.msyh,12)
        time_color = (153, 162, 170,255)
        draw.text((0,31), time, fill=time_color,font=font)

        return img

        
    
    # ====================box.bottom====================
    # 底部栏，如果数据都趋近于0，就绘制预设数字(114514),如果采集时已经有一定数据，那么用原始数据
    # return 图片对象，高
    def bottom(self, share, comm, like):
        img = Image.new('RGBA', (92*3, 48), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(self.msyh, 12)
        color = (153, 162, 170, 255)

        ico = get_ico('share', em=20)
        img.paste(ico, (0,16), ico)
        draw.text((20+4, 18), num_human(share), fill=color,font=font)

        ico = get_ico('comment', em=20)
        img.paste(ico, (0+96,16), ico)
        draw.text((96+20+4, 18), num_human(comm), fill=color,font=font)

        ico = get_ico('like', em=20)
        img.paste(ico, (0+192,16), ico)
        draw.text((192+20+4, 18), num_human(like), fill=color,font=font)

        return img


    # ====================box.bg====================
    # 动态卡片的整体背景，包括外围动态卡片白色背景和右上角的装扮、三个点
    # 输入内容包括整体高度、装扮的图片和数字。整体高度由 nickname + body + buttom 三部分组成
    # return 图标对象
    def bg(self, height, decorate_card=None, fan_number="00000", fancolor=(31,31,31,255)):
        img = Image.new('RGBA', (self.width, height), (0,0,0,0))
        draw=ImageDraw.Draw(img)
        draw.rounded_rectangle(((0,0),(img.size[0]-1,img.size[1]-1)), radius=8, fill=(255,255,255,255))

        if decorate_card:
            # 动态装扮两种尺寸，横竖比大于2:1=>146x44，否则60 × 34
            s=decorate_card.size
            
            if s[0]/s[1] > 2:
                log.debug(f'Got decorate card object, its size={s}, target size=(146,44)')
                dimg = decorate_card.resize((146,44), Image.ANTIALIAS)
                draw = ImageDraw.Draw(dimg)
                font = ImageFont.truetype(self.fanfont, 12)
                draw.text((40,17), fan_number, fill=fancolor, font=font)

                img.paste(dimg, (self.width - 48 - 146,18), dimg)
            else:
                log.debug(f'Got decorate card object, its size={s}, target_size(60,34)')
                dimg = decorate_card.resize((60,34), Image.ANTIALIAS)
                img.paste(dimg, (self.width - 48 - 60,18), dimg)
        return img


    # ====================box.repost==================
    # 把主体内容加一个框，以及原来的发送者信息。
    # 解析出原始发送者信息，并且套上一个 上下8，左右12的灰色框。
    def repost(self, orface: object(), orname: str, new_card:object(), card: object()):
        oimg = Image.new('RGBA', (card.size[0]+24,card.size[1]+16 + 30 + 8), (244, 245, 247,255))
        #头像
        fsize=24
        mask = Image.new('RGBA', (fsize*2,fsize*2), (0,0,0,0))
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse(((0,0) + (fsize*2, fsize*2)), fill=(0,0,0,255))
        mask = mask.resize((fsize,fsize), Image.ANTIALIAS)
        face = orface.resize((fsize, fsize), Image.ANTIALIAS)
        oimg.paste(face, (12, 8), mask=mask)

        #昵称
        draw = ImageDraw.Draw(oimg)
        font = ImageFont.truetype(self.msyh, 14)
        nickcolor = (0, 161, 214, 255)
        draw.text((44, 13), orname, fill=nickcolor, font=font)

        #主体
        oimg.paste(card, (12, 8+24+6), card)

        img = Image.new('RGBA', (oimg.size[0], oimg.size[1] + new_card.size[1] + 10), (0,0,0,0))
        log.info(f'splice new card and origin card. Size = {img.size}')
        img.paste(new_card, (12,0), new_card)
        img.paste(oimg, (0, new_card.size[1] + 10), img_rounded(oimg.size,16))

        return img


    # ====================box.text====================
    # 绘制纯文字动态，输入文字即可。自动换行，过长截断，/n强制换行
    # 文字区域为动态卡主体区域，距右边边界不小于12px。
    # 字号14，行高22，表情包大小20，字符间距0.5
    # return 图片对象，高
    #offset: 88-图片左边缘，10-nickname
    def text(self, content: str, ex: dict=None, is_reposted=False):
        # 分行 -> 替换表情包 -> 按段渲染 -> 输出图片
        # 二阶段：过长的文本进行回行、省略和截断
        
        # 测试方法：逐字解析，并逐行绘制，最后贴到一张图上
        text = content
        black_color = (34,34,34,255)
        blue_color = (23, 139, 207, 255)

        rep = "ori" if is_reposted else "now"
        if ex:
            # print(f'ex:{ex}')
            emote = ex["emolist"]
            at = ex["at"][rep]
            topic = ex["topic"]
            link = ex["link"]
        else:
            emote,at,topic,link={},{},{},{}

        if(at):
            at_start = list(at.keys())
            at_point = 0
            at_pos = at_start[0]
            at_len = at[at_pos][0]
            at_type= at[at_pos][1]
        

        flag_topic = -1

        if link:
            link_urls = list(link.keys())
            lk_point = 0
            lk_url = link_urls[0]
            lk_txt = link[lk_url][0]
            lk_type= link[lk_url][1]
            lk_len = len(lk_url)
       

        point = 0   # 文字位置指针(宽)
        ch_num = 0  # 文字数量指针
        imgl = Image.new('RGBA', (self.width-88 - 24, 22), (0,0,0,0))
        draw = ImageDraw.Draw(imgl)
        font = ImageFont.truetype(self.msyh, 14)
        fulltextcard = []

        while True:
            ch = text[0]
            # 强制换行或者遇到换行符
            if ch == '\n' or point >= (self.width -88 -24 - (24 + 22)):     # <== 自然换行的界定：宽度上，卡片左边去掉88，右边去掉24，还有字符宽度最高22，
                point = 0
                if point >= (self.width -88 -24 - (24 + 22)):
                    ch_num = ch_num + 1
                if len(text) <= 1:
                    break
                if ch == '\n':
                    text = text[1:]
                    ch_num = ch_num + 1
                fulltextcard.append(imgl)
                imgl = Image.new('RGBA', (self.width-88 -24, 22), (0,0,0,0))
                draw = ImageDraw.Draw(imgl)
                continue
            # 遇到[，判断是否遇到了表情包
            elif ch == '[' and emote:
                emo_len = text.find(']')
                if emo_len > 1:
                    emo_name = text[:emo_len+1]
                    if emo_name in emote.keys():        # 全匹配才能算作表情包
                        emo = emote[emo_name]
                        emo = emo.resize((20,20),Image.ANTIALIAS)
                        imgl.paste(emo,((point+1), 1),emo)
                        point = point + 22
                        ch_num = ch_num + emo_len
                        if len(text) <= emo_len + 1:
                            break
                        text = text[emo_len+1:]
                        continue  
            # 遇到#，判断是否遇到的topic
            elif ch == "#" and topic:
                # print("find #")
                topic_len = text[1:].find('#')+1
                if topic_len > 1:
                    topic_name = text[1:topic_len]      # 提取文字不带#号
                    if topic_name in topic.keys():
                        flag_topic = topic[topic_name] + 1
            # 正常打印
            text_color = black_color
            # 处理@变蓝信息
            if(at):
                if 0 <= ch_num - at_pos <= at_len:
                    if at_pos == ch_num:
                        if at_type == 2:
                            ico = get_ico("luck",16)
                        elif at_type == 3:
                            ico = get_ico("vote",16)
                        else:
                            ico = None
                        if ico:
                            imgl.paste(ico, (point, 3), ico)
                            point = point + 22
                    text_color = blue_color
                    if ch_num - at_pos == at_len:
                        at_point = (at_point+1) if at_point+1 < len(at_start) else at_point
                        at_pos = at_start[at_point]
                        at_len = at[at_pos][0]
                        at_type= at[at_pos][1]
            # 处理#变蓝信息
            if topic:
                if flag_topic >= 0:
                    text_color = blue_color
                    flag_topic = flag_topic-1
            # 处理超链接文字替换及变蓝
            if link:
                if text[:lk_len] == lk_url:
                    if lk_type==1:
                        ico = get_ico('play',16)
                    elif lk_type == 2:
                        ico = get_ico('link',16)
                    imgl.paste(ico, (point, 3), ico)
                    point = point + 22
                    for n, link_ch in enumerate(lk_txt):
                        if point >= (self.width -88 -14 - (24 + 22)):
                            point = 0
                            fulltextcard.append(imgl)
                            imgl = Image.new('RGBA', (self.width-88 -24, 22), (0,0,0,0))
                            draw = ImageDraw.Draw(imgl)
                        draw.text((point,4), link_ch, fill=blue_color, font=font)
                        link_ch_nxt = None if n+1>=len(lk_txt) else lk_txt[n+1]
                        point = point + chgap(link_ch, link_ch_nxt, 7.5)
                    ch_num = ch_num + lk_len
                    text = text[lk_len+1:]

                    
                    lk_point = (lk_point+1) if lk_point+1 < len(link_urls) else lk_point
                    lk_url = link_urls[lk_point]
                    lk_len = len(lk_url)
                    lk_txt = link[lk_url][0]
                    lk_type= link[lk_url][1]

                    continue
                    

            draw.text(((point), 4), ch, fill=text_color,font=font)
            if len(text) > 1:
                chnxt = text[1]
            else:
                chnxt = None
                # 中英文以及符号设置不同的间距。放弃特殊语言的支持。仅支持常见的中、日、英。
            point = point + chgap(ch, chnxt, 7.5)
            ch_num = ch_num + 1
            if len(text) <= 1:
                break
            text = text[1:]


        fulltextcard.append(imgl)

        img = Image.new('RGBA', (self.width-88 - 24, len(fulltextcard) * 22), (0,0,0,0))
        for i, im in enumerate(fulltextcard):
            img.paste(im, (0, i * 22))
        
        return img


    # ====================box.image====================
    # 绘制带图的动态，文字部分调用text，图片根据数量进行处理，单图过长则按照4：3截断
    # return 图片对象，高
    def image(self, content: str, ex: dict, pics: list, pic_count: int, is_reposted=False):
        # 总之把文字画完，然后画图片
        text_img = self.text(content,ex, is_reposted)
        # img = Image.new('RGBA', (text_img.size[0], text_img[1] + maxx*seil(pic_count/3))), (0,0,0,0))
        length = text_img.size[1] + 10 + ceil(108*(1+pic_count/3))
        nimage=[]
        if pic_count==1:
            # 一张图片，尽量画完

            pic = pics[0]
            s=pic.size
            ns, cut = img_resize(s)     # 获得新的大小，并判断是否裁切
            if cut:
                if s[0] > s[1]:         # 横图，裁掉过长部分
                    cu = (cut/2, s[1]/2)
                    cu2= (cut,s[1])
                    c = (s[0]/2,s[1]/2)
                    win = (c[0]-cu[0], c[1]-cu[1], c[0]+cu[0], c[1]+cu[1])
                else:
                    cu = (s[0]/2, cut/2)    # 纵图，从顶上开始裁剪
                    cu2= (s[0],cut)
                    win=((0,0)+cu2)

                pic = pic.crop(win)
                # pic = pic.crop((0,0) + cu2)     # 裁剪
            pic = pic.resize(ns, Image.ANTIALIAS)
            length =  text_img.size[1] + 10 + ns[1]
            nimage.append(pic)

        else:
            # 多图，固定104x104大小 ==> 104太小，尺寸扩大
            target = self.width - 100 / 3 - 20
            log.debug(f'Multi images, size fix to {target}x{target}')
            for im in pics:
                s=im.size
                s2=[0,0]
                if s[0] >= s[1]:
                    s2[1] = target
                    s2[0] = int(target * (s[0] / s[1]))
                else:
                    s2[0] = target
                    s2[1] = int(target * (s[1] / s[0]))
                pic = im.resize(s2,Image.ANTIALIAS)
                win = ( s2[0]/2-target/2, s2[1]/2-target/2, s2[0]/2+target/2, s2[1]/2+target/2 )    #从中间切出一个正方形
                nimage.append(pic.crop(win))
        
        if pic_count == 1:
            line=1
        elif pic_count == 4:
            line=2
        else:
            line=3
        log.debug(f'Got {pic_count} pics, {line} pics per line.')

        img = Image.new('RGBA', (text_img.size[0], length), (0,0,0,0))
        img.paste(text_img, (0,0), text_img)
        # ====error====
        for n, im in enumerate(nimage):
            pointx = 0 + (108 * (n%line))
            pointy = text_img.size[1]+10 + (108*int(n/line))
            img.paste(im, (pointx, pointy), img_rounded(im.size, 8))

        return img
      

    # ====================box.video====================
    # 绘制带视频的动态，输入视频标题、简介、播放量、弹幕量、封面(图片对象)，以及或许存在的动态文字
    # return 图片对象，高
    def video(self,title, desc, view, danmuku, cover, is_coop, dynamic_text, is_reposted=False):
        card_point = 0
        if (not is_reposted) and dynamic_text:
            img_dynamic = self.text(dynamic_text)
            card_point = img_dynamic.size[1] + 10

        # 视频小卡片，封面203x127，贴合小边缩放、裁切；标题最多两行，简介最多两行，
        # 创建基础卡片
        vimg = Image.new('RGBA', (self.width-88 - 24, 129), (0,0,0,0))
        draw = ImageDraw.Draw(vimg)
        fontbig = ImageFont.truetype(self.msyh, 14)
        fontsmall=ImageFont.truetype(self.msyh, 12)
        color_title= (33,33,33,255)
        color_desc = (102, 102, 102, 255)
        color_info = (153, 153, 153, 255)
        draw.rounded_rectangle(((0,0),(vimg.size[0]-1,vimg.size[1]-1)), radius=4, fill=(0,0,0,0), outline=(color_info),width=1)

        # 放置封面
        s =cover.size
        if s[0]/s[1] == (203/127):
            cover_stand = cover.resize((203,127),Image.ANTIALIAS)
        elif s[0]/s[1] > (203/127):
            s0 = int(s[1] * 203/127 /2)
            cover = cover.crop((s[0]/2-s0,0,s[0]/2+s0,s[1]-1))
            cover_stand = cover.resize((203,127),Image.ANTIALIAS)
            # cover = cover.resize((s0, 127), Image.ANTIALIAS)
            # cover_stand = cover.crop((s0/2-101,0, s0/2+101, 126))
        else:
            s1 = int(s[0] * 127/203 /2)
            cover = cover.crop((0,s[1]/2-s1 ,s[0]-1,s[1]/2+s1 ))
            cover_stand = cover.resize((203,127), Image.ANTIALIAS)
            # cover = cover.resize((203,s1), Image.ANTIALIAS)
            # cover_stand = cover.crop((0,s1/2-63, 202,s1/2+63))
        print(f'size of cover={s}, size of cover_stand={cover_stand.size}')
        mask=Image.new('RGBA', (203,127), (0,0,0,0))    
        maskdr = ImageDraw.Draw(mask)
        maskdr.rounded_rectangle((0,0,202,126), radius=4, fill=(0,0,0,255))
        # print(f'size of mask={mask.size}')
        vimg.paste(cover_stand, (1,1),mask)
        # 封面上放一个投稿视频/联合投稿的字符
        draw.rounded_rectangle(((133,8),(195,26)), radius=2, fill=(251, 114, 153,255))
        draw.text((140,10), text=("联合投稿" if is_coop else "投稿视频"), fill=(255,255,255,255),font=fontsmall)
        # 写标题
        offsetx, offsety = 203+12, 9+2
        maxx = vimg.size[0]-16
        point,line = offsetx,0
        for n,ch in enumerate(title):
            chnxt = title[n+1] if n+1<len(title) else None
            draw.text((point, offsety + line*19), ch, fill=color_title, font=fontbig)
            if line>0 and point+22 > maxx and len(title)-n>1:
                draw.text((point, offsety+line*19), '...', fill=color_title, font=fontbig)
                break
            if point + 16 > maxx:
                point = offsetx
                line = line+1
                continue
            point = point + chgap(ch, chnxt, 8)

        # 写简介
        offsetx, offsety = 203+12, 28+line*19 + 10 + 3
        maxx = vimg.size[0] - 16
        point,line = offsetx,0
        for n,ch in enumerate(desc):
            chnxt = desc[n+1] if n+1<len(desc) else None
            draw.text((point, offsety + line*19), ch, fill=color_desc, font=fontsmall)
            if point + 16 > maxx:
                point = offsetx
                line = line+1
                continue
            else:
                point = point + chgap(ch, chnxt, 8)
            if line>0 and point+22 > maxx and len(desc)-n>1:
                draw.text((point, offsety+line*19), '...', fill=color_title, font=fontsmall)
                break
        # 写播放量和弹幕量
        offsetx, offsety= 203+12, vimg.size[1]-18
        ico = get_ico('play_sec',em=16)
        vimg.paste(ico, (offsetx, offsety), ico)
        draw.text((offsetx+20, offsety-1), num_human(view), color_info, fontsmall)
        offsetx = offsetx+20+50
        ico = get_ico('danmuku',em=16)
        vimg.paste(ico, (offsetx, offsety), ico)
        draw.text((offsetx+20, offsety-1), num_human(danmuku), color_info, fontsmall)        
        # 图片拼接
        img = Image.new('RGBA', (self.width-88 - 24, card_point+129), (0,0,0,0))
        if (not is_reposted) and dynamic_text:
            img.paste(img_dynamic, (0,0), img_dynamic)
        img.paste(vimg, (0, card_point), vimg)
        return img

    
    # ====================box.article====================
    # 绘制专栏的卡片，未确定
    # return 图片对象，高
    def article(self,a, is_reposted=False):
        pass

    # ====================box.bangumi====================
    # 番剧发布和分享的卡片，未确认
    # return 图片对象，高
    def bangumi(a, is_reposted=False):
        pass

    # ====================box.h5====================
    # h5活动页卡片，未确认
    # return 图片对象，高
    def h5(a, is_reposted=False):
        pass

def num_human(input):
    # 小于9.9k则返回原来状态
    if input < 9900:
        output = str(input)
    elif input == 114514:
        output = str(input)
    else:
        wan = int(input / 10000)
        qian = int((input % 10000) / 1000)
        bai = input - 10000*wan - 1000*qian
        if(bai > 500):
            qian = qian + 1
            if qian == 10:
                wan = wan+1
                qian = 0
        output = f'{wan}.{qian}万'
    return output



def analyze_extra(latest: dict, card: dict):
    #####
    #   emolist: "name": pic_pil
    #   at     : "now/ori": location:[length, type]
    #   topic  : "text": length
    #   link   : "link": ["text", type]
    #####
    emolist, at, topic, link = {},{},{},{}
    if latest["display"].get("emoji_info"):
        emotes = latest["display"]["emoji_info"]["emoji_details"]
        for emo in emotes:
            emo_name = emo["text"]
            emo_url  = emo["url"]
            emo_img  = get_Image(Type='emote', url=emo_url)
            emolist[emo_name]=emo_img
    if latest["display"].get("origin"):
        if latest["display"]["origin"].get("emoji_info"):
            emotes = latest["display"]["origin"]["emoji_info"]["emoji_details"]
            for emo in emotes:
                emo_name = emo["text"]
                emo_url  = emo["url"]
                emo_img  = get_Image(Type='emote', url=emo_url)
                emolist[emo_name]=emo_img

    # @、抽奖、投票 蓝色字体，如果可以的话最好能加上符号
    at["now"]={}
    at["ori"]={}
    if card.get("item"):
        if card["item"].get("at_control"):
            ats = card["item"]["at_control"]
            if not ats == {}:
                for a in ats:
                    a_lo = a["location"]
                    a_le = a["length"]
                    a_ty = a["type"]
                    at["now"][a_lo]=[a_le, a_ty]
        if card["item"].get("ctrl"):
            ats = card["item"]["ctrl"]
            if not ats == {}:
                for a in ats:
                    a_lo = a["location"]
                    a_le = a["length"]
                    a_ty = a["type"]
                    at["now"][a_lo]=[a_le, a_ty]

    if card.get("origin"):
        if card["origin"].get("item"):
            if card["origin"]["item"].get("at_control"):
                ats = card["origin"]["item"]["at_control"]
                if not ats == {}:
                    for a in ats:
                        a_lo = a["location"]
                        a_le = a["length"]
                        a_ty = a["type"]
                        at["ori"][a_lo]=[a_le, a_ty]
            if card["origin"]["item"].get("ctrl"):
                ats = card["origin"]["item"]["ctrl"]
                if not ats == {}:
                    for a in ats:
                        a_lo = a["location"]
                        a_le = a["length"]
                        a_ty = a["type"]
                        at["ori"][a_lo]=[a_le, a_ty]
            


    # #话题蓝色字体
    if latest["display"].get("topic_info"):
        topics = latest["display"]["topic_info"]["topic_details"]
        for t in topics:
            t_name=t["topic_name"]
            t_len =len(t_name)
            topic[t_name]=t_len
    if latest["display"].get("origin"):
        if latest["display"]["origin"].get("topic_info"):
            topics = latest["display"]["origin"]["topic_info"]["topic_details"]
            for t in topics:
                t_name=t["topic_name"]
                t_len =len(t_name)
                topic[t_name]=t_len


    # 超链接替换成文字
    if latest["display"].get("rich_text"):
        links=latest["display"]["rich_text"]["rich_details"]
        for li in links:
            txt = li["text"]
            ori = li["orig_text"]
            ico = li["icon_type"]
            link[ori]=[txt, ico]
    if latest["display"].get("origin"):
        if latest["display"]["origin"].get("rich_text"):
            links = latest["display"]["origin"]["rich_text"]["rich_details"]
            for li in links:
                txt = li["text"]
                ori = li["orig_text"]
                ico = li["icon_type"]
                link[ori]=[txt, ico]

    return {"emolist":emolist, "at":at, "topic":topic, "link":link}



def chgap(ch:str, chnxt, base):
    #计算字符间距，都是英文则正常间距，且li等字符较瘦。中英、英中及中文之间2倍宽度，日文同理
    #瘦长
    if chnxt == None:
        chnxt = '\uffff'
    num = 2*base
    # 如果英文后加中文，那么两倍宽度
    if chnxt <= '\u007e':
        # 最窄间距
        if ch in ":.fiIjklrt[]{}":
            num=base * 0.6
        #稍窄间距
        elif ch in '1/':
            num = base *0.85
        # 稍宽间距1
        elif ch in 'o8#@%':
            num = 1.3 * base
        # 稍宽间距2
        elif ch in 'wmNW':
            num = 1.5 * base
        # 稍宽间距--大写字母
        elif '\u0041' <= ch <= '\u005a':
            num = 1.3 * base
        # 基础间距
        elif ch <= '\u007e':
            num = base
    # 后面是中文
    else:
        if ch <= '\u007e':
            num = base * 1.6
    # print(f'ch = {ch}, gap={num} ==> {ceil(num)}')
    return ceil(num)


def img_resize(s):
    '''
    规则：
        每条边最长为320。比例4:3
        如果图很大且超比例，那么尺寸限制在320x240(横图)或240x320（纵图）
        图大且未超比例，那长边靠近320
        如果正方形的图，104~320，缩放
        小图，放大至小边
    '''
    target_min=104
    target_max=320
    x,y=s[0],s[1]
    B=max(s)
    S=min(s)
    cut = None
    if B==S:        #正方形的图
        if B<target_min:
            ns=(target_min,target_min)
        elif(B>target_max):
            ns=(target_max,target_max)
        else:
            ns=(x,y)
    else:
        if B/S > 4/3:       # 长图，需要截取
            cut = 3 * B / 4
            # print(f"pic be cuted to ({B},{cut})")
            if B < target_min:
                nS = target_min
                nB = target_min * 4 /3
            elif S>target_max:
                nB = target_max
                nS = target_max * 3 / 4
        else:               # 比例合规
            if B < target_min:
                nS=120
                nB=int(B*120/S)
            elif S>target_max:
                nB=target_max
                nS=int(S*target_max/B)
        if x>y:
            ns=(nB,nS)
        else:
            ns=(nS,nB)
    return ns,cut


def img_rounded(s: tuple(), r):
    mask = Image.new('RGBA', s, (0,0,0,0))
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0,0, s[0]-1, s[1]-1), radius=r, fill=(0,0,0,255))
    return mask


def hex2rgb(hex:str, alpha=255):
    hex=hex[1:] if hex[0]=='#' else hex
    if not len(hex) == 6:
        log.error('Input color hex wrong, got {hex}, return white color.')
        return(255,255,255,255)
    # print(hex)
    r = int(hex[0:2],16)
    g = int(hex[2:4],16)
    b = int(hex[4:6],16)
    return (r,g,b,alpha)
