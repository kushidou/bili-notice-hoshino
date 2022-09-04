import os, json, time, io, re, base64
from loguru import logger as log
from math import ceil
from os.path import dirname, join, exists
from PIL import Image,ImageFont,ImageDraw,ImageFilter
import configparser as cfg

from .getImg import get_ico, get_Image, save_Image

curpath = dirname(__file__)
# 读取配置文件
conf = cfg.ConfigParser()
conf.read(join(curpath, '../config.ini'), encoding='utf-8')
# comcfg = conf.items('common')
# drawcfg = conf.items('drawCard')

# 生成动态卡片的具体代码
# 各个程序，传入参数为json代码和子卡片标志
#   （转发动态也是传入整串json代码，由他调用其他的卡片绘制）
class Card(object):
    # important to outside:
    # Card.dyid, .dytime, .dytype, .nickname
    def __init__(self, dylist: dict):
        # 初始化时，解析部分基础信息，然后判断Type等
        # self.latest = dylist["data"]["cards"][0]
        self.json_decode_result = False
        self.latest = dylist
        self.dytype = self.latest["desc"]["type"]
        self.dyorigtype=self.latest["desc"]["orig_type"]
        self.dyid   = self.latest["desc"]["dynamic_id"]
        self.dyidstr= self.latest["desc"]["dynamic_id_str"]
        self.dytime = self.latest["desc"]["timestamp"]
        self.nickname=self.latest["desc"]["user_profile"]["info"]["uname"]
        self.uid   = self.latest["desc"]["user_profile"]["info"]["uid"]
        card_content= self.latest["card"]

        try:
            self.card = json.loads(card_content)
            if self.card.get("item"):
                if self.card["item"].get("at_control"):
                    self.card["item"]["at_control"] = json.loads(self.card["item"]["at_control"])
                if self.card["item"].get("ctrl"):
                    self.card["item"]["ctrl"] = json.loads(self.card["item"]["ctrl"])
            if(self.dytype == 1):
                self.card["origin"] = json.loads(self.card["origin"])
                self.card["origin_extend_json"] = json.loads(self.card["origin_extend_json"])
                if self.card["origin"].get("item"):
                    if self.card["origin"]["item"].get("at_control"):
                        self.card["origin"]["item"]["at_control"] = json.loads(self.card["origin"]["item"]["at_control"])
                    if self.card["origin"]["item"].get("ctrl"):
                        self.card["origin"]["item"]["ctrl"] = json.loads(self.card["origin"]["item"]["ctrl"])
        except:
            # if exists(join(curpath,'../log/')
            print('Error while decode card data json')
            fname = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime()) + '_' + self.dyidstr
            with open(join(curpath,'../log/') + fname + '_raw.json' , 'w') as f:
                json.dump(dylist, f, ensure_ascii=False)
            with open(join(curpath,'../log/') + fname + '_rep.json' , 'w') as f:
                f.write(str(card_content))
            log.error(f'エロ发生！动态卡片内容解码错误:uid={self.uid}, dynamic_id={self.dyid}. 已经保存至"log/{fname}.json"')
            return

        if not self.dyid == int(self.dyidstr):
            self.dyid = int(self.dyidstr)
        self.extra = {} # 各种变蓝文字的信息
        log.trace(f'Object decode finish. Name={self.nickname}, Type={int(self.dytype)}')
        self.json_decode_result=True

        
    
    def is_realtime(self, timeinterval: int):
        return False if timeinterval*60 < (int(time.time()) - self.dytime) else True

    def check_black_words(self, gblk, ublk, islucky):
        ret = False
        txt = ""
        gblk = re.sub(r' ?, ?', ',', gblk)
        blk = gblk.split(',') + ublk

        # 根据不同的动态内容，提取特定的区块来过滤。
        #txt = json.dumps(self.card, ensure_ascii=False) 
        if self.dytype == 2:
            txt = self.card["item"]["description"]    
        elif self.dytype == 4 or self.dytype == 1:
            txt = self.card["item"]["content"]
        if self.dytype == 1:
            if self.dyorigtype == 2:
                txt += self.card["origin"]["item"]["description"]
            elif self.dyorigtype == 4:
                txt += self.card["origin"]["item"]["content"]
        for b in blk:
            # if txt.count(b):
            if b[0] == '\\':
                c = re.findall(b[1:], txt)
                c = len(c) if c else 0
                log.debug(f'black-words: find {b} {c} times!')
            else:
                c = txt.count(b)
                log.debug(f'black-words: find {b} {c} times!')
            if c:
                ret = True
                log.info(f'Find black word(s) {b} in dynamic {self.dyidstr}, which is posted by {self.nickname}')
                break
        if islucky == True:
            if self.dytype == 1 or conf.getboolean('common','sharelucky'):
                if "互动抽奖" in str(self.card["origin"]):
                    log.info('动态为转发的抽奖内容，即将屏蔽。')
                    ret = True
                else:
                    log.info('动态为普通转发内容，放行。')
        return ret


    @log.catch
    def draw(self, box:object(), dy_cache:bool=False):
        # 解析通用的信息，并绘制头像、昵称、背景、点赞box，然后调用其他绘制动态主体，最后把所有box合成
        # 制作头像  == faceimg ==
        
        log.info("~~ Start to draw dynamic card pciture ~~")
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
            log_avatar_type='企业'
            log.debug('This is an account of Group.')
        elif avatar_type == 0:     #个人认证
            face_avatar = get_ico('persional')
            log_avatar_type='个人'
            log.debug('This is an account of Professional Persion')
        elif avatar_type == -1:
            avatar_url = self.latest["desc"]["user_profile"]["vip"]["avatar_subscript_url"]
            if not avatar_url == "":
                face_avatar = get_Image(Type="avatar",url=avatar_url)
                log_avatar_type='年度会员'
                log.debug('This is an account of BigVIP(Year)')
            else:
                face_avatar = None
                log_avatar_type='普通人'
                log.debug('This is a normal persion.')
        faceimg = box.face(face, pendant=face_pendant, avatar_subscript=face_avatar)
        log.info(f'FaceBox: 头像框={bool(face_pendant)}, 头像角标={log_avatar_type}; BoxSize={faceimg.size}', )

        # 制作昵称  == nickimg ==
        nickname = self.latest["desc"]["user_profile"]["info"]["uname"]
        isVIP    = True if (self.latest["desc"]["user_profile"]["vip"]["vipType"] == 2) else False
        pubtime  = time.strftime("%y-%m-%d %H:%M", time.localtime(float(self.dytime)))
        nickimg = box.nickname(nick=nickname, time=pubtime, isBigVIP=isVIP)
        log.info(f'Name&Time Box: nickname={nickname}, color={"pink" if isVIP else "black"}, time="{pubtime}"({self.dytime});BoxSize={nickimg.size}')

        #制作一键三连   == bottom ==
        sharenum   = self.latest["desc"]["repost"]
        if self.dytype in [1,2,4]:  # 转发、图文、纯文字  从desc里获得评论
            commentnum = self.latest["desc"]["comment"]
            log.debug(f'Get comment number={commentnum} form dynamic.desc.comment because Type={self.dytype}')
        elif self.dytype == 8:      # 视频，card.stat获得评论
            commentnum = self.card["stat"]["reply"]
            log.debug(f'Get comment number={commentnum} form dynamic.card.stat.comment because Type={self.dytype}')
        elif self.dytype == 64:     # 专栏，从card.stats获得评论
            commentnum = self.card["stats"]["reply"]
            log.debug(f'Get comment number={commentnum} form dynamic.card.stat.comment because Type={self.dytype}')
        elif self.dytype == 256:    # 音频，从card.replyCnt获得评论
            commentnum = self.card["replyCnt"]
            log.debug(f'Get comment number={commentnum} form dynamic.card.replyCnt because Type={self.dytype}')
        else:
            commentnum = 114514
            log.debug('Get comment num fail! Set commentnum = 114514')
        likenum    = self.latest["desc"]["like"]
        bottomimg = box.bottom(sharenum, commentnum, likenum)
        log.info(f'BottomBox: share={sharenum}, comment={commentnum}, like={likenum}; BoxSize={bottomimg.size}')

        #根据类型制作body  ==  body ==
        # == 准备有关材料 ==
        self.extra = analyze_extra(self.latest, self.card)
        ret_txt=""
        # print(self.extra)
        if self.dytype == 1:    #转发   
            bodyimg = self.drawRepost(self.card, box)
            ret_txt="转发"
        elif self.dytype == 2:  #图片
            bodyimg = self.drawImage(self.card, box)
            ret_txt="图文"
        elif self.dytype == 4:  #文字
            bodyimg = self.drawobj(self.card, box)
            ret_txt="动态"
        elif self.dytype == 8:  #视频
            bodyimg = self.drawVideo(self.card, box)
            ret_txt="视频"
        elif self.dytype == 16:  #小视频
            bodyimg = self.drawsmallVideo(self.card, box)
            ret_txt="视频"
        elif self.dytype == 64: #专栏
            bodyimg = self.drawArticle(self.card, box)
            ret_txt="专栏文章"
        elif self.dytype == 256: #音频
            bodyimg = self.drawAudio(self.card, box)
            ret_txt="音频"
        elif self.dytype == 512: #番剧
            bodyimg = self.drawBangumi(self.card, box)
            ret_txt="番剧"
        elif self.dytype == 2048:    #H5
            bodyimg = self.drawH5Event(self.card, box)
            ret_txt="H5动态"
        elif self.dytype == 2049:   #漫画
            bodyimg = self.drawComic(self.card, box)
            ret_txt="漫画"
        else:
            bodyimg = Image.new('RGBA', (50,50), 'white')
            ret_txt=""
        log.info(f'BodyBox: type={ret_txt}; BoxSize={bodyimg.size}')


        #根据所有的长度制作背景图   == bg ==
        bgcard = self.latest["desc"]["user_profile"].get("decorate_card")
        if bgcard:
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
        log.info(f'BackgroundBox: 卡片挂件={bool(decorate_img)}')
        bgimg = box.bg(decorate_card=decorate_img, fan_number=decorate_num, fancolor=decorate_col)

        img = box.combine(face=faceimg, nick=nickimg, body=bodyimg, bottom=bottomimg, bg=bgimg, is_reposted=True if self.dytype==1 else False)

        if dy_cache:
            try:
                dy_pic_name = f'{self.uid}_{self.nickname}_{self.dyid}_{self.dytype}_{self.dyorigtype}.png'
                save_Image(img, 'dynamic_card', name = dy_pic_name)
                log.info(f'Sace Dynamic Card Pic as "{dy_pic_name}" -->  res/cache/dynamic_card/ ')
            except:
                log.warning(f'Save Dynamic Card Pic failed! ')
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        base64_img = 'base64://' + base64.b64encode(bio.getvalue()).decode()
        log.info('Congratulations! Dynamic Card Image is generated successfully. Encode as "base64" and send to QQbot.\n')

        dy_flag = conf.getboolean('cache', 'dycard_cache')
        if dy_flag:
            save_Image(img, 'dynamic_card', f'{self.uid}_{self.dyid}_{self.dytype}_{self.nickname}.png')

        return base64_img, ret_txt
        

    #Type=1     转发    repost
    def drawRepost(self, content, box, is_rep=False):
        # 解析出现在动态内容、原始动态信息
        # 先按类型绘制原始动态,贴身灰色背景，然后绘制当前动态（纯文字），拼接，最后返回完整图片
        log.info('Type = Repost')
        oritype = self.latest["desc"]["orig_type"]
        if oritype in [2,4,8,64,256,2048]:
            orname =content["origin_user"]["info"]["uname"]
            orface = get_Image(Type = "face", url=content["origin_user"]["info"]["face"])
        elif oritype in [512]:
            orname = content["origin"]["apiSeasonInfo"]["title"]
            orface = get_Image(Type="cover", url=content["origin"]["apiSeasonInfo"]["cover"] )

        img_now = box.text(content["item"]["content"], self.extra)

        
        if oritype == 2:    # 转发带图动态
            img_ori = self.drawImage(content["origin"], box, is_rep=True)
        elif oritype == 4:  # 转发别人的动态
            img_ori = self.drawobj(content["origin"], box, is_rep=True)
        elif oritype == 8:  # 转发视频
            img_ori = self.drawVideo(content["origin"], box, is_rep=True)
        elif oritype == 64: # 转发专栏文章
            img_ori = self.drawArticle(content["origin"], box, is_rep=True)
        elif oritype == 256:# 转发音频
            img_ori = self.drawAudio(content["origin"], box, is_rep=True)
        elif oritype == 512: # 转发番剧剧集
            img_ori = self.drawBangumi(content["origin"], box, is_rep=True)
        elif oritype == 2048:   # 转发h5活动
            img_ori = self.drawH5Event(content["origin"], box, is_rep=True)
        

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
        return self.drawVideo(content, box, is_rep)

    # Type=64   专栏        Article
    def drawArticle(self, content, box, is_rep=False):
        imgs = []
        img_urls = content["image_urls"]
        for url in img_urls:
            imgs.append(get_Image(Type="article_cover", url=url))
        title = content["title"]
        summary= content["summary"]
        template = content["template_id"]

        img = box.article(title, summary, imgs, template, is_rep)
        return img

    # Type=256  音频        Audio
    def drawAudio(self, content, box, is_rep=False):
        cover_url = content["cover"]
        cover = get_Image(Type="cover", url=cover_url)
        desc = content["intro"]
        title = content["title"]
        subtype = content["typeInfo"]

        img = box.audio(title, desc, cover, subtype, is_rep)
        return img


    # Type=512  番剧        Bangumi         （貌似只出现在转发里）
    def drawBangumi(self, content, box, is_rep=False):
        sptitle = content["apiSeasonInfo"]["title"]
        spcover = get_Image(Type="cover", url=content["apiSeasonInfo"]["cover"])
        eptitle = content["index_title"]
        epcover = get_Image(Type="cover", url=content["cover"])
        epplay  = content["play_count"]
        epdanmu = content["bullet_count"]

        img = box.bangumi(sptitle, spcover, eptitle, epcover, epplay, epdanmu, is_rep)
        return img

    # Type=2048 H5活动      H5Event
    def drawH5Event(self, content, box, is_rep=False):
        h5title = content["sketch"]["title"]
        h5desc  = content["sketch"]["desc_text"]
        h5cover = get_Image(Type="cover", url=content["sketch"]["cover_url"])
        desc    = content["vest"]["content"]

        img = box.h5( h5title, h5desc, h5cover, desc, ex=self.extra, is_reposted=is_rep)
        return img

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

    # def __init__(self, width, max_height):
    def __init__(self, conf:object):
        self.maxheight = conf.getint('drawCard','height_max')
        self.width = conf.getint('drawCard','width')
        self.minheight = int(conf.getint('drawCard','width') / 2)
        self.path = dirname(__file__)
        self.msyh = join(self.path, 'fonts/pinfang.ttf')
        self.fanfont = join(self.path, 'fonts/fans_num.ttf')
        self.fontsize_large = conf.getint('drawCard','font_size_1')
        self.fontsize_medium = conf.getint('drawCard','font_size_2')
        self.fontsize_small = conf.getint('drawCard','font_size_3')
        self.box_gap_agni = conf.getfloat('drawCard','box_size_agnification')
        self.image_max = conf.getint('drawCard','image_max_size')
        self.img_min    = conf.getint('drawCard','image_min_size')



    # ====================box.combine====================
    # 按顺序组合box，计算整体长度
    def combine(self, face:object, nick:object, body:object, bottom:object, bg=None, is_reposted:bool=False):
        len = 27 + nick.size[1] + 4 + body.size[1] + 4 + bottom.size[1]
        log.debug(f'Height of dynamic pic = {len}. Start splicing.')
        img = Image.new('RGBA', (self.width, len), 'white')
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(((0,0),(img.size[0]-1,img.size[1]-1)), radius=8, fill=(255,255,255,255))

        img.paste(face, (9,9), mask=face)
        img.paste(nick, (88,27), mask=nick)
        if is_reposted:
            img.paste(body, (88, 75), mask=body)
        else:
            img.paste(body, (76, 75), mask=body)
        img.paste(bottom, (88, len-48), mask=bottom)
        if bg:
            img.paste(bg, (self.width-48-bg.size[0],18 ), mask=bg)
        return img




    # ====================box.face()====================
    # 绘制头像box，输入参数有头像、头像框、右下角标（大会员、蓝黄闪电），图片对象
    # return 图片对象
    # offset 9,9
    def face(self, face, pendant=None, avatar_subscript=None):
        fsize,psize,asize = 42, 72, 18
        img = Image.new('RGBA', (psize,psize), color='white')
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
        ts=(self.width - 88, 46)        # target size
        img = Image.new('RGBA', ts, (255,255,255,255))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(self.msyh, self.fontsize_large)

        nick_color = (251, 114, 153, 255) if isBigVIP else (32,32,32,255)
        draw.text((0,3), nick, fill=nick_color,font=font)
        
        font = ImageFont.truetype(self.msyh,self.fontsize_small)
        time_color = (153, 162, 170,255)
        draw.text((0,31), time, fill=time_color,font=font)
        return img

        
    
    # ====================box.bottom====================
    # 底部栏，如果数据都趋近于0，就绘制预设数字(114514),如果采集时已经有一定数据，那么用原始数据
    # return 图片对象，高
    def bottom(self, share, comm, like):
        img = Image.new('RGBA', (92*3, 48), 'white')
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(self.msyh, 12)
        color = (153, 162, 170, 255)

        ico = get_ico('share', em=20)
        img.paste(ico, (0,16), ico)
        draw.text((20+4, 18), num_human(share) if share else '分享', fill=color,font=font)

        ico = get_ico('comment', em=20)
        img.paste(ico, (0+96,16), ico)
        draw.text((96+20+4, 18), num_human(comm) if comm else '评论', fill=color,font=font)

        ico = get_ico('like', em=20)
        img.paste(ico, (0+192,16), ico)
        draw.text((192+20+4, 18), num_human(like) if like else '点赞', fill=color,font=font)

        return img


    # ====================box.bg====================
    # 动态卡片的整体背景，包括外围动态卡片白色背景和右上角的装扮、三个点
    # 输入内容包括整体高度、装扮的图片和数字。整体高度由 nickname + body + buttom 三部分组成
    # return 图标对象
    def bg(self, decorate_card=None, fan_number="00000", fancolor=(31,31,31,255)):
        img = None
        if decorate_card:
            # 动态装扮两种尺寸，横竖比大于2:1=>146x44，否则60 × 34
            s=decorate_card.size
            if s[0]/s[1] > 2:
                log.debug(f'Got decorate card object, its size={s}, target size=(146,44)')
                img = Image.new('RGBA', (146,44), 'white')
                dimg = decorate_card.resize((146,44), Image.ANTIALIAS)
                img.paste(dimg, (0,0), dimg)
                draw = ImageDraw.Draw(img)
                font = ImageFont.truetype(self.fanfont, 12)
                draw.text((40,17), fan_number, fill=fancolor, font=font)
            else:
                log.debug(f'Got decorate card object, its size={s}, target_size(60,34)')
                img = Image.new('RGBA', (146,44), 'white')
                dimg = decorate_card.resize((60,34), Image.ANTIALIAS)
                img.paste(dimg, (0,0), dimg)
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
        bgcolor = (244, 245, 247,255) if is_reposted else (255,255,255,255)
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
        imgl = Image.new('RGBA', (self.width-88 - 24, 22), bgcolor)
        draw = ImageDraw.Draw(imgl)
        font = ImageFont.truetype(self.msyh, 14)
        fulltextcard = []

        while True and len(text):
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
                imgl = Image.new('RGBA', (self.width-88 -24, 22), bgcolor)
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
                        point = point + int(chgap(link_ch, link_ch_nxt, 7.5))
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
            point = point + int(chgap(ch, chnxt, 7.5))
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
        log.debug(f'ImageBox: num of pics = {pic_count}')
        # 总之把文字画完，然后画图片
        text_img = self.text(content,ex, is_reposted)
        log.debug(f'ImageBox -> TextBox, ')
        # img = Image.new('RGBA', (text_img.size[0], text_img[1] + maxx*seil(pic_count/3))), (0,0,0,0))
        target = int((text_img.size[0] - 40) / 3 - 5)   # 多图图片大小，尽量放大些
        length = text_img.size[1] + 10 + (target + 5)*ceil(pic_count/3)
        log.debug(f'ImageBox: length => {text_img.size[1]} + 10 + {target+5} x ({pic_count}/3) = {length}')
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

        bgcolor = (244, 245, 247,255) if is_reposted else (255,255,255,255)
        img = Image.new('RGBA', (text_img.size[0], length), bgcolor)
        img.paste(text_img, (0,0), text_img)
        # ====error====
        for n, im in enumerate(nimage):
            pointx = 0 + ((target+5) * (n%line))
            pointy = text_img.size[1]+10 + ((target+5)*int(n/line))
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
        bgcolor = (244, 245, 247,255) if is_reposted else (255,255,255,255)
        vimg = Image.new('RGBA', (self.width-88 - 24, 129), bgcolor)
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
            if line>0 and point+22 > maxx and len(title)-n>1:
                draw.text((point, offsety+line*19), '...', fill=color_title, font=fontbig)
                break
            draw.text((point, offsety + line*19), ch, fill=color_title, font=fontbig)
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
        bgcolor = (244, 245, 247,255) if is_reposted else (255,255,255,255)
        img = Image.new('RGBA', (self.width-88 - 24, card_point+129), bgcolor)
        if (not is_reposted) and dynamic_text:
            img.paste(img_dynamic, (0,0), img_dynamic)
        img.paste(vimg, (0, card_point), vimg)
        return img

    
    # ====================box.article====================
    # 绘制专栏的卡片，未确定
    # return 图片对象，高
    def article(self, title:str, summary:str, images:list, template:int, is_reposted=False):
        width_of_card = self.width - 88 - 12 - 30
        img = Image.new('RGBA', (width_of_card, 200), 'white')
        log.debug(f'Size of atricle-box=({width_of_card}, 200)')
        draw = ImageDraw.Draw(img)
        fontbig = ImageFont.truetype(self.msyh, 16)
        fontsmall=ImageFont.truetype(self.msyh, 12)
        # 头图
        if template == 4:       # 单头图
            log.info('头图数量：1')
            timg = images[0]
            tsize = timg.size
            if tsize[0]/tsize[1] < width_of_card/120:        # 图片较方
                timg = timg.resize((width_of_card, int(width_of_card * (tsize[1]/tsize[0]))), Image.ANTIALIAS)
            else:               # 图片狭长
                timg = timg.resize((int(120 * (tsize[0]/tsize[1])), 120), Image.ANTIALIAS)
            log.debug(f'头图缩放: raw{tsize} ==> new{timg.size}')
            tsize = timg.size
            tsize_win = ( (
                tsize[0]/2 - (width_of_card-4)/2, 0,
                tsize[0]/2 + (width_of_card-4)/2, 120
            ) )
            log.debug(f'头图裁切: win={tsize_win}')
            timg = timg.crop(tsize_win)
            img.paste(timg, (0,0))
        elif template == 3:         # 三头图
            log.info('头图数量：3')
            xsize=int((width_of_card - 10) /3)
            log.debug(f'头图宽度为{xsize}')
            for n,im in enumerate(images):
                tsize = im.size
                if tsize[0]/tsize[1] < xsize/120:        # 图片较方
                    im = im.resize((xsize, int(xsize * (tsize[1]/tsize[0]))), Image.ANTIALIAS)
                else:               # 图片狭长
                    im = im.resize((int(120 * (tsize[0]/tsize[1])), 120), Image.ANTIALIAS)
                tsize = im.size
                tsize_win = ( (
                    tsize[0]/2 - (xsize-4)/2, 0,
                    tsize[0]/2 + (xsize-4)/2, 120
                ) )
                im = im.crop(tsize_win)
                log.debug(f'头图{n}的缩放尺寸{tsize}, 裁剪尺寸{tsize_win}')
                img.paste(im, (0+n*(xsize+5), 0))
                log.debug(f'第{n}幅头图位置:({0+n*(xsize+5)}, 0)')
        # 标题
        point = (20, 120+10)
        if len(title)>35:
            title = title[0:30] + '......'
        draw.text(point, text=title, fill=(33,33,33,255), font=fontbig)

        # 简介文字
        point = (20, 120 + 10 + 22 + 6) # 头图+间隔+标题+间隔
        line, cha = 0,0
        while(1):
            ch = summary[0]
            draw.text(point, ch, fill=(102, 102, 102, 255), font=fontsmall)
            if len(summary) > 2:
                ch1 = summary[1]
                gap = chgap(ch, ch1, 12/2)
            point = (point[0]+gap, point[1])
            if point[0] + 6 + 20 > width_of_card:
                line +=1
                point = (20, 120 + 10 + 22 + 6 + line*19)
            if line>=1 and point[0] + 36 + 20> width_of_card:       # 文字过长，需要截断并省略
                draw.text(point, '...', fill=(102, 102, 102, 255), font=fontsmall)
                break
            if len(summary) == 1:       # 文字展示结束
                break
            summary=summary[1:]
        
        bg = Image.new('RGBA', (img.size[0]+2, img.size[1]+2), (0,0,0,0))
        bgdraw = ImageDraw.Draw(bg)
        color_info = (153, 153, 153, 255)
        bgdraw.rounded_rectangle(((0,0),(bg.size[0]-1,bg.size[1]-1)), 
                    radius=4, fill=(0,0,0,0), outline=(color_info),width=1)
        bg.paste(img, (1,1), mask=img_rounded(img.size, r=4))
        return bg


    # ====================box.audio====================
    # 番剧发布和分享的卡片，未确认
    # return 图片对象，高
    def audio(self, title: str, desc:str, cover, subtype:str, is_reposted=False):
        descbox = self.text(desc)

        width_of_card = self.width - 88 - 18 - 10
        audiobox = Image.new('RGBA', (width_of_card, 82), (0,0,0,0))
        fontbig = ImageFont.truetype(self.msyh, 14)
        fontsmall = ImageFont.truetype(self.msyh, 12)
        draw = ImageDraw.Draw(audiobox)

        draw.rounded_rectangle(((0,0),(width_of_card-1, 81)), radius=4, fill='white', outline=(150, 150, 150,255),width=1)
        audiobox.paste(cover.resize((80,80), Image.ANTIALIAS), (1,1), mask = img_rounded((80,80), 4))
        log.debug(f'Cover size={cover.size}, resize to 80x80')
        point = (80+15, 16)
        # 绘制标题文字
        while(1):
            ch = title[0]
            draw.text(point, ch, fill=(34, 34, 34, 255), font=fontbig)
            if len(title) == 1:       # 文字展示结束
                break
            else:
                ch1 = title[1]
                gap = chgap(ch, ch1, 14/2)
                point = (point[0]+gap, point[1])
                if point[0] + 36 + 16> width_of_card:       # 文字过长，需要截断并省略
                    log.info('Title of audio is too long, cut!')
                    draw.text(point, '...', fill=(34, 34, 34, 255), font=fontbig)
                    break
            title=title[1:]
        # 绘制音频分区
        point=(80+15, 16+20+8)
        draw.text(point, subtype, (153, 162, 170, 255), fontsmall)
        log.debug(f'audio box: 文字部分绘制完成')
        
        h = descbox.size[1] + 10 + audiobox.size[1]
        w = max(descbox.size[0], audiobox.size[0])
        log.info(f'Size of audio card = ({w}, {h})')
        img = Image.new('RGBA', (w,h), (0,0,0,0))
        img.paste(descbox,(0,0))
        img.paste(audiobox, (0, descbox.size[1]+10))
        return img
        


    # ====================box.bangumi====================
    # 番剧发布和分享的卡片
    # return 图片对象，高
    def bangumi(self, sptitle, spcover, eptitle, epcover, epplay, epdanmu, is_reposted=False):
        card_point = 0

        # 视频小卡片，封面203x127，贴合小边缩放、裁切；标题最多两行，简介最多两行，
        # 创建基础卡片
        vimg = Image.new('RGBA', (self.width-88 - 24, 129), (255,255,255,255))
        draw = ImageDraw.Draw(vimg)
        fontbig = ImageFont.truetype(self.msyh, 14)
        fontsmall=ImageFont.truetype(self.msyh, 12)
        color_title= (33,33,33,255)
        color_info = (153, 153, 153, 255)
        draw.rounded_rectangle(((0,0),(vimg.size[0]-1,vimg.size[1]-1)), radius=4, fill=(255,255,255,255), outline=(color_info),width=1)

        # 放置封面
        s =epcover.size
        if s[0]/s[1] == (203/127):
            epcover_stand = epcover.resize((203,127),Image.ANTIALIAS)
        elif s[0]/s[1] > (203/127):
            s0 = int(s[1] * 203/127 /2)
            epcover = epcover.crop((s[0]/2-s0,0,s[0]/2+s0,s[1]-1))
            epcover_stand = epcover.resize((203,127),Image.ANTIALIAS)
        else:
            s1 = int(s[0] * 127/203 /2)
            epcover = epcover.crop((0,s[1]/2-s1 ,s[0]-1,s[1]/2+s1 ))
            epcover_stand = epcover.resize((203,127), Image.ANTIALIAS)
        log.info(f'size of epcover={s}, size of epcover_stand={epcover_stand.size}')
        mask=Image.new('RGBA', (203,127), (0,0,0,0))    
        maskdr = ImageDraw.Draw(mask)
        maskdr.rounded_rectangle((0,0,202,126), radius=4, fill=(0,0,0,255))
        # print(f'size of mask={mask.size}')
        vimg.paste(epcover_stand, (1,1),mask)

        # 封面上放一个番剧的字符
        draw.rounded_rectangle(((133,8),(175,26)), radius=2, fill=(251, 114, 153,255))
        draw.text((140,10), text=("番 剧"), fill=(255,255,255,255),font=fontsmall)
        # 写标题
        offsetx, offsety = 203+12, 9+2
        maxx = vimg.size[0]-16
        point,line = offsetx,0
        for n,ch in enumerate(eptitle):
            chnxt = eptitle[n+1] if n+1<len(eptitle) else None
            if line>0 and point+22 > maxx and len(eptitle)-n>1:
                draw.text((point, offsety+line*19), '...', fill=color_title, font=fontbig)
                break
            draw.text((point, offsety + line*19), ch, fill=color_title, font=fontbig)
            if point + 16 > maxx:
                point = offsetx
                line = line+1
                continue
            point = point + chgap(ch, chnxt, 8)

        # 写播放量和弹幕量
        offsetx, offsety= 203+12, vimg.size[1]-18
        ico = get_ico('play_sec',em=16)
        vimg.paste(ico, (offsetx, offsety), ico)
        draw.text((offsetx+20, offsety-1), num_human(epplay), color_info, fontsmall)
        offsetx = offsetx+20+50
        ico = get_ico('danmuku',em=16)
        vimg.paste(ico, (offsetx, offsety), ico)
        draw.text((offsetx+20, offsety-1), num_human(epdanmu), color_info, fontsmall)        
        # 图片拼接
        img = Image.new('RGBA', (self.width-88 - 24, card_point+129), (0,0,0,0))
        img.paste(vimg, (0, card_point), vimg)
        return img

    # ====================box.h5====================
    # h5活动页卡片
    # 输入：h5活动的标题简介封面、附带文字和特殊字符。
    # return 图片对象，高
    def h5(self, h5title:str, h5desc:str, h5cover:dict, desc:str=None, ex:dict=None, is_reposted=False):
        
        #bgcolor = (244, 245, 247,255) if is_reposted else (255,255,255,255)
        fontbig = ImageFont.truetype(self.msyh, 14)
        fontsmall=ImageFont.truetype(self.msyh, 12)
        color_title= (33,33,33,255)
        color_desc = (102, 102, 102, 255)

        
        color_info = (153, 153, 153, 255)
        # 文字部分
        timg = self.text(desc, ex, is_reposted=is_reposted)
        # 主体部分画个框
        himg = Image.new("RGBA", (580,80), (0,0,0,0))
        himgdr = ImageDraw.Draw(himg)
        himgdr.rounded_rectangle(((0,0),(himg.size[0]-1,himg.size[1]-1)), radius=4,   \
            fill=(255,255,255,255), outline=(color_info),width=1)
        # 封面,可能不是正方形，取短边缩放到78x78，然后裁剪
        s=h5cover.size
        if s[0] == s[1]:
            cover = h5cover.resize((78,78),Image.ANTIALIAS)
        elif s[0]>s[1]:
            cover = h5cover.crop(((s[0]-s[1])/2, 0, (s[0]+s[1])/2, s[1])).resize((78,78), Image.ANTIALIAS)
        else:
            cover = h5cover.crop((0, (s[1]-s[0])/2, s[0], (s[0]+s[1])/2)).resize((78,78), Image.ANTIALIAS)
        mask=Image.new('RGBA', (78,78), (0,0,0,0))    
        maskdr = ImageDraw.Draw(mask)
        maskdr.rounded_rectangle((0,0,78,78), radius=4, fill=(0,0,0,255))
        log.debug(f'h5cover, size=({h5cover.size}) -> (78,78)')
        # print(f'size of mask={mask.size}')
        himg.paste(cover, (1,1),mask)
        # 标题
        offsetx, offsety, maxx = 80+15, 15+3, 580 - 15
        point = offsetx
        for n,ch in enumerate(h5title):
            chnxt = h5title[n+1] if n+1<len(h5title) else None
            if point + 22 > maxx:
                himgdr.text((point, offsety), '...', fill=color_title, font=fontbig)
                break
            himgdr.text((point, offsety), ch, fill=color_title, font=fontbig)
            point += chgap(ch, chnxt, 8)
        # 简介，仅一行
        offsetx, offsety, maxx = 80+15, 15+30+4, 580 - 15
        point = offsetx
        for n,ch in enumerate(h5desc):
            chnxt = h5title[n+1] if n+1<len(h5title) else None
            if point + 22 > maxx:
                himgdr.text((point, offsety), '...', fill=color_desc, font=fontsmall)
                break
            himgdr.text((point, offsety), ch, fill=color_desc, font=fontsmall)
            point += chgap(ch, chnxt, 6)
        # 拼接

        fullsize = (580, timg.size[1] + 8 + himg.size[1])
        img = Image.new('RGBA', fullsize, (0,0,0,0))
        img.paste(timg, (0,0), timg)
        img.paste(himg, (0, img.size[1]-80), himg)
        return img




#=============================EX functions====================================
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
                    a_ty = a["type"]
                    a_le = a["length"]-1 if a_ty==2 else a["length"]
                    
                    at["now"][a_lo]=[a_le, a_ty]
        if card["item"].get("ctrl"):
            ats = card["item"]["ctrl"]
            if not ats == {}:
                for a in ats:
                    a_lo = a["location"]
                    a_ty = a["type"]
                    a_le = a["length"]-1 if a_ty==2 else a["length"]
                    
                    at["now"][a_lo]=[a_le, a_ty]

    if card.get("origin"):
        if card["origin"].get("item"):
            if card["origin"]["item"].get("at_control"):
                ats = card["origin"]["item"]["at_control"]
                if not ats == {}:
                    for a in ats:
                        a_lo = a["location"]
                        a_ty = a["type"]
                        a_le = a["length"]-1 if a_ty==2 else a["length"]
                        at["ori"][a_lo]=[a_le, a_ty]
            if card["origin"]["item"].get("ctrl"):
                ats = card["origin"]["item"]["ctrl"]
                if not ats == {}:
                    for a in ats:
                        a_lo = a["location"]
                        a_ty = a["type"]
                        a_le = a["length"]-1 if a_ty==2 else a["length"]
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
            if latest["display"]["origin"]["topic_info"].get("topic_details"):
                topics = latest["display"]["origin"]["topic_info"]["topic_details"]
                for t in topics:
                    t_name=t["topic_name"]
                    t_len =len(t_name)
                    topic[t_name]=t_len
            if latest["display"]["origin"]["topic_info"].get("new_topic"):
                ntopic = latest["display"]["origin"]["topic_info"]["new_topic"]
                t_name=ntopic["name"]
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
    if ch == " ":
        return int(base)
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
        2022-05-27 深夜     规则重写
        只处理单图的情况。
        横向最大分辨率为320不动（可配置）
        横图，纵向最大240；横图，纵向最大430；总体保持4:3的比例
    '''
    target_min=104
    target_max=320
    x,y=s[0],s[1]
    B=max(s)
    S=min(s)
    cut = 0
    if x==y:        #正方形的图
        log.debug('方形图，缩放到合理范围')
        if x<target_min:
            ns=(target_min,target_min)
        elif(x>target_max):
            ns=(target_max,target_max)
        else:
            ns=(x,y)
    else:                           # 矩形图
        if B< target_max and S > target_min:    # 图像大小在范围内，保持原始分辨率
            log.debug('矩形图，但比例合理，缩放到合理范围内')
            nx,ny=x,y  
        else:                       # 图像太小或者太大
            log.debug('长图或宽图，缩放到合理大小并裁剪')
            if B/S < 4/3 :               # 图像比例正常
                if S > target_max:
                    if x>y:
                        nx = target_max
                        ny = (nx*y/x)
                    else:
                        ny=target_max
                        nx=(ny*x/y)
            else:                       # 长图，需要截取
                if x<y:                     # 纵图 ，y要长一点
                    nx = x if (x<target_max) else target_max
                    ny = nx * 4/3
                    cut = x * 4/3

                else:       # x>y, 横图，x要长一点
                    ny = int(y if (y<target_max * 3/4) else (target_max * 3/4))
                    nx = ny * 4/3
                    cut = y * 4/3

        ns=(int(nx),int(ny))
    log.info(f'Resize pic in Dynamic, origin size={s}, output size={ns}, cut={cut}')
    return ns,int(cut)


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
