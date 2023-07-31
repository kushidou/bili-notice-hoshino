import os
import httpx
import base64
from io import BytesIO
from os.path import dirname, join, exists
from PIL import Image, ImageDraw
# import cairosvg as svg
from loguru import logger as log

'''
    点赞    like        like.svg,40x40
    分享    share       icos.svg,40x40
    评论    comment     icos.svg,40x40
    链接    link        icos.svg,13x15
    抽奖    luck        icos.svg,17x16
    个人认证 persional  lighting_yellow.svg,64x64
    企业认证 group      lighting_blue.svg,64x64
'''

# 各图标的文件和默认大小信息
# ico_like    = {'file':'like.svg',       'size':(40,40)        }
# ico_share   = {'file':'share.svg',      'size':(40,40)        }
# ico_comment = {'file':'comment.svg',    'size':(40,40)        }
# ico_link    = {'file':'link.svg',       'size':(13,15)        }
# ico_luck    = {'file':'luck.svg',       'size':(17,16)        }
# ico_persional = {'file':'lighting_yellow.svg', 'size':(64,64) }
# ico_group   = {'file':'lighting_blue.svg',     'size':(64,64) }
# ico_danmuku = {'file':'danmuku.svg',    'size':(40,40)        }
# ico_playsec = {'file':'play_sec.svg',   'size':(40,40)        }

ico_like    = {'file':'like.png',       'size':(40,40)        }
ico_share   = {'file':'share.png',      'size':(40,40)        }
ico_comment = {'file':'comment.png',    'size':(40,40)        }
ico_link    = {'file':'link.png',       'size':(13,15)        }
ico_luck    = {'file':'luck.png',       'size':(17,16)        }
ico_persional = {'file':'persional.png', 'size':(64,64) }
ico_group   = {'file':'group.png',     'size':(64,64) }
ico_danmuku = {'file':'danmuku.png',    'size':(40,40)        }
ico_playsec = {'file':'play_sec.png',   'size':(40,40)        }

# 集合成一个字典
icos={  'like':ico_like,
        'share':ico_share,
        'comment':ico_comment,
        'link':ico_link,
        'luck':ico_luck,
        'persional':ico_persional,
        'group':ico_group,
        'danmuku':ico_danmuku,           
        'play_sec':ico_playsec      }

base64s={
    'play':"play_round.base64"
}

cur = dirname(__file__)


def get_ico(name, em=0):
    curpath = join(cur, 'ico_images')
    if name not in icos:
        if name in base64s:
            # base64转png图片
            base64_path = join(curpath, base64s[name])
            with open(base64_path, 'r') as f:
                base_png = base64.b64decode(f.read())
            img_png = Image.open(BytesIO(base_png)).convert('RGBA')
            em = em if em else 14
            img_png = img_png.resize((em,em), Image.ANTIALIAS)

            return img_png
        log.warning(f'Get_ICO: {name} No such file!')
        return None
    # 读取svg文件   !! 2022-08-08 所有SVG图像转换为PNG图像。
    svg_path = join(curpath, icos[name]['file'])
    # with open(svg_path,'r') as f:
    #     text = f.read()
    img = Image.open(svg_path)
    # 配置图片大小，如果没有传入大小参数，则使用默认大小
    if em == 0:
        size_width = icos[name]['size'][0]
        size_height = icos[name]['size'][1]
    else:
        size_width = em
        size_height = size_width * icos[name]['size'][1] / icos[name]['size'][0]
    # 替换svg中大小的关键字，然后渲染图片  !! 2022-08-08 所有SVG图像转换为PNG图像。
    # text=text.replace('$(SVG_WIDTH)', str(size_width))
    # text=text.replace('$(SVG_HEIGHT)', str(size_height))
    # svg_png = svg.svg2png(bytestring=text)
    # SVG对象传递给PIL对象，返回该对象和透明图层  !! 2022-08-08 所有SVG图像转换为PNG图像。
    # img_png = Image.open(BytesIO(svg_png)).convert('RGBA')
    img_png = img.resize((int(size_width), int(size_height)), Image.ANTIALIAS).convert('RGBA')
    # img_png.save(join(curpath,'test_ico_png_full.png'))


    return img_png


async def get_Image(Type, url=None, md5=None, path=None): # sync to async
    curpath = join(cur,'cache')
    if url:
        if "?" in url:
            # 处理url中的参数 2022-12-29
            filename = url.split('/')[-1].split("?")[0]
        else:
            filename = url.split('/')[-1]

        # filename = url_n.split('/')[-1]

        path_url = join(join(curpath, Type),filename)
        if exists(path_url):
            # print(f'Image {filename} exist, load from file.')
            log.debug(f"Getting image form Internet, from files, type={Type}, name={filename}")
            img = Image.open(path_url)
            return img.convert('RGBA')
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(url=url)
        # resp = requests.get(url)
        log.debug(f"Getting image form Internet, downloading, type={Type}, name={filename}")
        img = Image.open(BytesIO(resp.content))
        dirpath = join(curpath, Type)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        path_url = join(dirpath, filename)
        print(path_url)

        
        if img.mode == 'RGBA' and 'jpg' in path_url:
            img = img.convert('RGB')
            print('Image type convert: RGBA -> RGB')
        img.save(path_url)                # 保存文件

        return img.convert('RGBA')

    if md5:
        dirpath = join(curpath, Type)
        path_url = join(dirpath,md5)
        if(exists(path_url + 'png')):
            path_url = path_url + 'png'
            log.debug(f"Getting image form MD5, from file, type={Type}, name={md5+'.png'}")
            return Image.open(path_url).convert('RGBA')
        if(exists(path_url + 'jpg')):
            path_url = path_url + 'jpg'
            log.debug(f"Getting image form MD5, from file, type={Type}, name={md5+'.jpg'}")
            return Image.open(path_url).convert('RGBA')
        # 文件不存在，则根据类型拼接url后联网获取
        if Type == 'face':
            url_md5 = "https://i1.hdslb.com/bfs/face/" + md5
        elif Type == 'cover':
            url_md5 = "https://i1.hdslb.com/bfs/archive/" + md5
        else:
            return Image.new('RGBA',(104,104), 'white')
        log.debug(f"Getting image form MD5, downloading, type={Type}, name={md5}")
        async with httpx.AsyncClient() as client:
            resp = await client.get(url_md5)
        # resp = requests.get(url_md5)
        img = Image.open(BytesIO(resp.content))
        
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
            log.warning(f'Make dir of {dirpath}')
        if Type in ('face', 'cover'):
            path_url = path_url + 'jpg'
        elif Type in ('pendant', 'avatar_subscript'):
            path_url = path_url + 'png'
        img.save(path_url)
        return img.convert('RGBA')

    if path:
        log.info(f'Getting image from file path.')
        return Image.open(path).convert('RGBA')
    return None

def save_Image(img:object, Type:str, name:str, path=None):
    if not path:
        curpath = join(cur, 'cache')
        if not exists(join(curpath, Type)):
            os.makedirs(join(curpath, Type))
        img.save(join(join(curpath, Type), name))
    else:
        img.save(join(path, name))

# 获得一个圆形的蒙版，根据头像大小来获得
# img为头像的PIL对象
# 使用方法: bg.paste(face, location, roudn_mask(face) )
def round_mask(img=None, size=None):
    #输入图像 或 尺寸
    # alpha图层绘图部分参考 https://www.jianshu.com/p/cdea3ba63cd7
    if img:
        size_raw = img.size
    elif size:
        size_raw = size
    else:
        mask = Image.new('RGBA', size_raw, color=(0,0,0,255))
        return mask

    new_size = (size_raw[0] * 2, size_raw[1] * 2)
    mask = Image.new('RGBA', new_size, color=(0,0,0,0))
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse(((0,0) + new_size), fill=(0,0,0,255))
    # 使用两倍大小进行画圆，然后缩小来抗锯齿
    mask = mask.resize(size_raw, Image.ANTIALIAS)
    return mask

