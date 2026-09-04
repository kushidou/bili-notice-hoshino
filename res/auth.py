# B站API的Cookies激活功能。
# _uuid 和 bvid_fp 生成的代码摘录自https://github.com/SocialSisterYi/bilibili-API-collect/issues/933#issuecomment-1931506993


import time
import random
import struct
import io
import httpx
import json
from os.path import dirname, join, exists
from . import wbi
from . import fp_raw
from .httpx_compat import async_client

browser_header = {
        "authority": "api.bilibili.com",
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "content-type": "application/json;charset=UTF-8",
        "dnt": "1",
        "origin": "https://space.bilibili.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58",
    }


idpayload={
    "3064": 1,
    "5062": "1720887356232",
    "03bf": "https%3A%2F%2Fwww.bilibili.com%2F",
    "39c8": "333.999.fp.risk",
    "34f1": "",
    "d402": "",
    "654a": "",
    "6e7c": "150x689",
    "3c43": {
        "2673": 0,
        "5766": 24,
        "6527": 0,
        "7003": 1,
        "807e": 1,
        "b8ce": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "641c": 0,
        "07a4": "zh-CN",
        "1c57": 8,
        "0bd0": 8,
        "748e": [
            768,
            1366
        ],
        "d61f": [
            728,
            1366
        ],
        "fc9d": -480,
        "6aa9": "Asia/Shanghai",
        "75b8": 1,
        "3b21": 1,
        "8a1c": 0,
        "d52f": "not available",
        "adca": "Win32",
        "80c9": [
            [
                "PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "Chrome PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "Chromium PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "Microsoft Edge PDF Viewer",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ],
            [
                "WebKit built-in PDF",
                "Portable Document Format",
                [
                    [
                        "application/pdf",
                        "pdf"
                    ],
                    [
                        "text/pdf",
                        "pdf"
                    ]
                ]
            ]
        ],
        "13ab": "MB4AAAAASUVORK5CYII=",
        "bfe9": "SAAskoALCSsZpEUcC+Av8DxpQVtSPLlMwAAAAASUVORK5CYII=",
        "a3c1": [
            "extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_clip_control;EXT_color_buffer_half_float;EXT_depth_clamp;EXT_disjoint_timer_query;EXT_float_blend;EXT_frag_depth;EXT_polygon_offset_clamp;EXT_shader_texture_lod;EXT_texture_compression_bptc;EXT_texture_compression_rgtc;EXT_texture_filter_anisotropic;EXT_texture_mirror_clamp_to_edge;EXT_sRGB;KHR_parallel_shader_compile;OES_element_index_uint;OES_fbo_render_mipmap;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_blend_func_extended;WEBGL_color_buffer_float;WEBGL_compressed_texture_s3tc;WEBGL_compressed_texture_s3tc_srgb;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBGL_multi_draw;WEBGL_polygon_mode",
            "webgl aliased line width range:[1, 1]",
            "webgl aliased point size range:[1, 1024]",
            "webgl alpha bits:8",
            "webgl antialiasing:yes",
            "webgl blue bits:8",
            "webgl depth bits:24",
            "webgl green bits:8",
            "webgl max anisotropy:16",
            "webgl max combined texture image units:32",
            "webgl max cube map texture size:16384",
            "webgl max fragment uniform vectors:1024",
            "webgl max render buffer size:16384",
            "webgl max texture image units:16",
            "webgl max texture size:16384",
            "webgl max varying vectors:30",
            "webgl max vertex attribs:16",
            "webgl max vertex texture image units:16",
            "webgl max vertex uniform vectors:4096",
            "webgl max viewport dims:[32767, 32767]",
            "webgl red bits:8",
            "webgl renderer:WebKit WebGL",
            "webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
            "webgl stencil bits:0",
            "webgl vendor:WebKit",
            "webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)",
            "webgl unmasked vendor:Google Inc. (Intel)",
            "webgl unmasked renderer:ANGLE (Intel, Intel(R) UHD Graphics (0x00009B41) Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "webgl vertex shader high float precision:23",
            "webgl vertex shader high float precision rangeMin:127",
            "webgl vertex shader high float precision rangeMax:127",
            "webgl vertex shader medium float precision:23",
            "webgl vertex shader medium float precision rangeMin:127",
            "webgl vertex shader medium float precision rangeMax:127",
            "webgl vertex shader low float precision:23",
            "webgl vertex shader low float precision rangeMin:127",
            "webgl vertex shader low float precision rangeMax:127",
            "webgl fragment shader high float precision:23",
            "webgl fragment shader high float precision rangeMin:127",
            "webgl fragment shader high float precision rangeMax:127",
            "webgl fragment shader medium float precision:23",
            "webgl fragment shader medium float precision rangeMin:127",
            "webgl fragment shader medium float precision rangeMax:127",
            "webgl fragment shader low float precision:23",
            "webgl fragment shader low float precision rangeMin:127",
            "webgl fragment shader low float precision rangeMax:127",
            "webgl vertex shader high int precision:0",
            "webgl vertex shader high int precision rangeMin:31",
            "webgl vertex shader high int precision rangeMax:30",
            "webgl vertex shader medium int precision:0",
            "webgl vertex shader medium int precision rangeMin:31",
            "webgl vertex shader medium int precision rangeMax:30",
            "webgl vertex shader low int precision:0",
            "webgl vertex shader low int precision rangeMin:31",
            "webgl vertex shader low int precision rangeMax:30",
            "webgl fragment shader high int precision:0",
            "webgl fragment shader high int precision rangeMin:31",
            "webgl fragment shader high int precision rangeMax:30",
            "webgl fragment shader medium int precision:0",
            "webgl fragment shader medium int precision rangeMin:31",
            "webgl fragment shader medium int precision rangeMax:30",
            "webgl fragment shader low int precision:0",
            "webgl fragment shader low int precision rangeMin:31",
            "webgl fragment shader low int precision rangeMax:30"
        ],
        "6bc5": "Google Inc. (Intel)~ANGLE (Intel, Intel(R) UHD Graphics (0x00009B41) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ed31": 0,
        "72bd": 0,
        "097b": 0,
        "52cd": [
            0,
            0,
            0
        ],
        "a658": [
            "Arial",
            "Arial Black",
            "Arial Narrow",
            "Calibri",
            "Cambria",
            "Cambria Math",
            "Comic Sans MS",
            "Consolas",
            "Courier",
            "Courier New",
            "Georgia",
            "Helvetica",
            "Impact",
            "Lucida Console",
            "Lucida Sans Unicode",
            "Microsoft Sans Serif",
            "MS Gothic",
            "MS PGothic",
            "MS Sans Serif",
            "MS Serif",
            "Palatino Linotype",
            "Segoe Print",
            "Segoe Script",
            "Segoe UI",
            "Segoe UI Light",
            "Segoe UI Semibold",
            "Segoe UI Symbol",
            "Tahoma",
            "Times",
            "Times New Roman",
            "Trebuchet MS",
            "Verdana",
            "Wingdings"
        ],
        "d02f": "124.04347527516074"
    },
    "54ef": "{\"b_ut\":null,\"home_version\":\"V8\",\"i-wanna-go-back\":null,\"in_new_ab\":true,\"ab_version\":{\"for_ai_home_version\":\"V8\",\"tianma_banner_inline\":\"CONTROL\",\"enable_web_push\":\"DISABLE\"},\"ab_split_num\":{\"for_ai_home_version\":54,\"tianma_banner_inline\":54,\"enable_web_push\":10}}",
    "8b94": "",
    "df35": "9A9AF3710-310F1-D6B1-C262-62108C2DD31F1028579infoc",
    "07a4": "zh-CN",
    "5f45": "null",
    "db46": 0
}

gcookies=dict()
gcookies_outtime = 0

curpath = dirname(__file__)
cookie_txt_path = join(curpath, 'bili_cookie.txt')
cookie_json_path = join(curpath, 'bili_cookie.json')

MOD = 1 << 64

class Mylog:
    def error(self, linfo):
        print(linfo)
    def warning(self, linfo):
        print(linfo)
    def info(self, linfo):
        print(linfo)
    def debug(self, linfo):
        print(linfo)
    def trace(self, linfo):
        print(linfo)


def parse_cookie_text(cookie_text):
    cookies = {}
    for item in cookie_text.replace('\n', ';').split(';'):
        item = item.strip()
        if not item or '=' not in item:
            continue
        key, value = item.split('=', 1)
        key = key.strip()
        value = value.strip()
        if key:
            cookies[key] = value
    return cookies


def load_login_cookies(log = Mylog()):
    cookies = {}
    if exists(cookie_json_path):
        try:
            with open(cookie_json_path, 'r', encoding='UTF-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                cookies.update(data)
            else:
                log.warning('bili_cookie.json 格式错误，应为JSON对象。')
        except Exception as e:
            log.warning(f'读取 bili_cookie.json 失败：{e}')

    if not cookies and exists(cookie_txt_path):
        try:
            with open(cookie_txt_path, 'r', encoding='UTF-8') as f:
                cookies.update(parse_cookie_text(f.read()))
        except Exception as e:
            log.warning(f'读取 bili_cookie.txt 失败：{e}')

    if cookies:
        required = ['SESSDATA', 'bili_jct', 'DedeUserID']
        missing = [key for key in required if not cookies.get(key)]
        if missing:
            log.warning(f'已读取登录cookie，但缺少关键字段：{missing}')
        else:
            log.info('已读取 bili_cookie 登录cookie。')
    return cookies


async def update_cookies(fail = 0, log = Mylog()):
    # 更新一次小饼干。优先使用 res/bili_cookie.txt 或 res/bili_cookie.json 中的登录cookie。
    global gcookies, gcookies_outtime
    cok_delay = 6
    if time.time() - gcookies_outtime > cok_delay*3600 or fail:
        login_cookies = load_login_cookies(log)
        if login_cookies:
            gcookies = login_cookies
            gcookies_outtime = time.time()
            log.info('成功加载登录cookie')
        else:
            # 没有登录cookie时退回游客cookie。游客cookie在动态接口上更容易触发 -412。
            url = "https://space.bilibili.com/2/dynamic"
            try:
                async with async_client() as client:
                    request = await client.get(url, headers=browser_header)
                gcookies = dict(request.cookies)
                gcookies_outtime = time.time()
                log.warning('未配置登录cookie，已使用游客cookie。动态接口可能返回 -412 request was banned。')
            except Exception as e:
                log.error(f'更新小饼干失败,code={e}')
                if gcookies:
                    gcookies_outtime = time.time() + cok_delay*3600 - 600
                    log.warning('未获取cookies, 沿用之前的cookies, 10分钟后再次尝试')
                else:
                    log.warning('未获取cookies, 重试')

        if gcookies:
            gcookies["_uuid"] = gen_uuid()
            gcookies["enable_web_push"] = "DISABLE"
            log.debug(f'当前cookie字段：{list(gcookies.keys())}')

            await activate_bvid(log)

        # 顺便更新wbi密钥
        r= await  wbi.update()
        if r:
            log.info('更新wbi密钥')
        else:
            log.warning('wbi密钥获取失败')

    return gcookies if gcookies else None


def _rotate_left(x: int, k: int) -> int:
    bin_str = bin(x)[2:].rjust(64, "0")
    return int(bin_str[k:] + bin_str[:k], base=2)


def gen_uuid() -> str:
    t = int(time.time() * 1000) % 100000
    mp = list("123456789ABCDEF") + ["10"]
    pck = [8, 4, 4, 4, 12]
    gen_part = lambda x: "".join([random.choice(mp) for _ in range(x)])
    return "-".join([gen_part(l) for l in pck]) + str(t).ljust(5, "0") + "infoc"


def gen_buvid_fp(key: str, seed: int):
    source = io.BytesIO(bytes(key, "ascii"))
    m = _murmur3_x64_128(source, seed)
    return "{}{}".format(
        hex(m & (MOD - 1))[2:], hex(m >> 64)[2:]
    )


async def get_buvid() -> str:
    url = "https://api.bilibili.com/x/frontend/finger/spi"
    async with async_client() as client:
        request = await client.get(url, headers=browser_header)
    content = request.json()
    return content["data"]["b_3"]


async def activate_bvid(log = Mylog()) -> int:
    global gcookies
    if not gcookies:
        log.warning('跳过激活bvid：cookies为空')
        return -1

    url = "https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi"
    try:
        async with async_client() as client:
            request = await client.post(url, cookies=gcookies, headers=browser_header, data=json.dumps({"payload":json.dumps(idpayload)}))
    except Exception as e:
        log.warning(f'激活bvid失败：{e}')
        return -1

    if request.status_code != 200:
        log.warning(f'激活bvid失败，HTTP={request.status_code}, body={request.text[:300]}')
        return -1

    try:
        return request.json()["code"]
    except Exception as e:
        log.warning(f'激活bvid响应解析失败：{e}, body={request.text[:300]}')
        return -1


def _murmur3_x64_128(source: io.BufferedIOBase, seed: int) -> str:
    C1 = 0x87C3_7B91_1142_53D5
    C2 = 0x4CF5_AD43_2745_937F
    C3 = 0x52DC_E729
    C4 = 0x3849_5AB5
    R1, R2, R3, M = 27, 31, 33, 5
    h1, h2 = seed, seed
    processed = 0
    while 1:
        read = source.read(16)
        processed += len(read)
        if len(read) == 16:
            k1 = struct.unpack("<q", read[:8])[0]
            k2 = struct.unpack("<q", read[8:])[0]
            h1 ^= (_rotate_left(k1 * C1 % MOD, R2) * C2 % MOD)
            h1 = ((_rotate_left(h1, R1) + h2) * M + C3) % MOD
            h2 ^= _rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
            h2 = ((_rotate_left(h2, R2) + h1) * M + C4) % MOD
        elif len(read) == 0:
            h1 ^= processed
            h2 ^= processed
            h1 = (h1 + h2) % MOD
            h2 = (h2 + h1) % MOD
            h1 = _fmix64(h1)
            h2 = _fmix64(h2)
            h1 = (h1 + h2) % MOD
            h2 = (h2 + h1) % MOD
            return (h2 << 64) | h1
        else:
            k1 = 0
            k2 = 0
            if len(read) >= 15:
                k2 ^= int(read[14]) << 48
            if len(read) >= 14:
                k2 ^= int(read[13]) << 40
            if len(read) >= 13:
                k2 ^= int(read[12]) << 32
            if len(read) >= 12:
                k2 ^= int(read[11]) << 24
            if len(read) >= 11:
                k2 ^= int(read[10]) << 16
            if len(read) >= 10:
                k2 ^= int(read[9]) << 8
            if len(read) >= 9:
                k2 ^= int(read[8])
                k2 = _rotate_left(k2 * C2 % MOD, R3) * C1 % MOD
                h2 ^= k2
            if len(read) >= 8:
                k1 ^= int(read[7]) << 56
            if len(read) >= 7:
                k1 ^= int(read[6]) << 48
            if len(read) >= 6:
                k1 ^= int(read[5]) << 40
            if len(read) >= 5:
                k1 ^= int(read[4]) << 32
            if len(read) >= 4:
                k1 ^= int(read[3]) << 24
            if len(read) >= 3:
                k1 ^= int(read[2]) << 16
            if len(read) >= 2:
                k1 ^= int(read[1]) << 8
            if len(read) >= 1:
                k1 ^= int(read[0])
            k1 = _rotate_left(k1 * C1 % MOD, R2) * C2 % MOD
            h1 ^= k1


def _fmix64(k: int) -> int:
    C1 = 0xFF51_AFD7_ED55_8CCD
    C2 = 0xC4CE_B9FE_1A85_EC53
    R = 33
    tmp = k
    tmp ^= tmp >> R
    tmp = tmp * C1 % MOD
    tmp ^= tmp >> R
    tmp = tmp * C2 % MOD
    tmp ^= tmp >> R
    return tmp
