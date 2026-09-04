# bili 动态监视器（Hoshino 插件）

B 站 UP 主动态监视与群推送插件，适用于 HoshinoBot。

本版本在原插件基础上增加了 RSSHub 支持：优先从自建 RSSHub 获取动态标题、正文、视频标题和媒体，RSSHub 不可用时再回退到 B 站 API。

> 本 README 按当前 RSSHub 路由和本项目改版代码编写。

## 重要说明

B 站动态接口近年来多次变化。原插件依赖的旧动态详情接口已经无法稳定处理新版 opus 动态，常见现象包括：

- 动态列表可以读取，但详情接口返回 `404`
- 返回 `-352` 风控校验失败或 `-412 request was banned`
- 图文动态的正文、标题和图片字段结构不固定
- 视频动态能检测到，但无法读取视频标题或封面

本版本推荐搭建自己的 RSSHub，由 RSSHub 负责获取动态内容，Hoshino 负责轮询、去重、生成图片和群推送。

## 功能

- 获取指定 UP 主的最新动态并推送到群。
- 支持动态、图文、视频、短视频、专栏、音频、番剧、相簿和部分特殊动态。
- RSSHub 优先提供标题、正文、视频标题、图片和视频封面。
- 图片可以生成图片卡片；图片渲染失败时自动发送动态链接。
- 视频没有正文时使用视频标题。
- 默认标题为“`UP主名的动态`”时，从正文截取一段作为标题并添加省略号。
- 正文不完整展开，只作为默认标题的来源。
- 保留分享、评论、点赞数量。
- 支持过滤转发抽奖动态和关键词过滤。
- 支持群级别关注、取关和关注列表查询。
- 支持昵称搜索和昵称绑定。
- 保留原 B 站 API 作为 RSSHub 失败时的备用方式。

## 目录结构

插件安装后目录大致如下：

```text
hoshino/modules/bili-notice-hoshino/
├── bili_notice_hoshino.py
├── dymgr.py
├── config.ini
├── requirements.txt
├── res/
│   ├── auth.py
│   ├── getImg.py
│   ├── httpx_compat.py
│   ├── wbi.py
│   ├── drawCard.py
│   └── bili_cookie.txt
├── uppers/
│   ├── list.json
│   └── UID.json
└── log/
```

`uppers/list.json` 保存关注列表，`uppers/UID.json` 保存对应 UP 主已经处理过的动态 ID。

## 部署 Hoshino 插件

进入 HoshinoBot 的 modules 目录：

```bash
cd /www/wwwroot/HoshinoBot-master/hoshino/modules
```

克隆插件：

```bash
git clone https://github.com/kushidou/bili-notice-hoshino.git
```

安装插件依赖：

```bash
cd /www/wwwroot/HoshinoBot-master/hoshino/modules/bili-notice-hoshino
python3 -m pip install -r requirements.txt
```

如果 Hoshino 使用虚拟环境，请在对应虚拟环境中执行：

```bash
cd /www/wwwroot/HoshinoBot-master
source venv/bin/activate
python -m pip install -r hoshino/modules/bili-notice-hoshino/requirements.txt
```

准备配置文件：

```bash
cp config_example.ini config.ini
```

如果需要清空示例关注列表，不要直接删除整个目录，只修改：

```text
uppers/list.json
```

原仓库示例列表中包含嘉然 UID `672328094`。使用自己的关注列表时，应删除这个示例记录。

在 Hoshino 的 `config/__bot__.py` 中，将插件加入 `MODULES_ON`：

```python
MODULES_ON = [
    # 其他模块
    "bili-notice-hoshino",
]
```

然后重启 HoshinoBot。

## 配置 Hoshino

推荐配置：

```ini
[common]
# 单位：秒。每次只轮询一个 UP 主。
# 关注人数较多时，建议 60 或 120，不建议使用 8。
poll_time = 60

# 每多少轮普通轮询检查一次直播。
pool_live = 10

# 日志级别
log_level = debug

# 动态超过该分钟数时忽略
available_time = 360

# 是否只推送视频
only_video = false

# 是否只推送普通动态
only_dynamic = false

# 是否推送转发动态
repost = true
```

不要把 `poll_time` 设得过小。图片下载和卡片渲染需要时间，如果上一轮尚未结束，下一轮就会出现：

```text
maximum number of running instances reached (1)
```

推荐至少使用：

```ini
poll_time = 60
```

## 部署自己的 RSSHub

RSSHub 官方提供 Docker 镜像和 Docker Compose 部署方式。默认端口为 `1200`，当前官方镜像支持 `diygod/rsshub` 和 `ghcr.io/diygod/rsshub`。[cite:dbbd58be-1]

在服务器创建目录：

```bash
mkdir -p /www/wwwroot/rsshub
cd /www/wwwroot/rsshub
```

下载官方 Compose 文件：

```bash
wget https://raw.githubusercontent.com/DIYgod/RSSHub/master/docker-compose.yml
```

官方 Compose 配置默认包含：

- RSSHub
- Redis
- Browserless Chrome

如果希望使用官方 Compose 文件里的 Browserless 配置，保留 `browserless` 服务和：

```yaml
PLAYWRIGHT_WS_ENDPOINT: 'ws://browserless:3000'
```

## 配置 RSSHub Cookie

RSSHub 的 B 站用户动态路由使用按 UID 命名的环境变量：

```text
BILIBILI_COOKIE_{UP主UID}
```

例如：

```yaml
services:
  rsshub:
    environment:
      NODE_ENV: production
      CACHE_TYPE: redis
      REDIS_URL: 'redis://redis:6379/'
      PLAYWRIGHT_WS_ENDPOINT: 'ws://browserless:3000'

      BILIBILI_COOKIE_353840826: '你的完整Cookie'
      BILIBILI_COOKIE_161775300: '你的完整Cookie'
      BILIBILI_COOKIE_1265652806: '你的完整Cookie'
```

同一条 B 站 Cookie 可以复用给多个 UP，但变量名必须按照每个 UP 的 UID 分别填写。不能只写：

```yaml
BILIBILI_COOKIE: '你的Cookie'
```

当前 B 站动态路由要求完整 Cookie，至少应包含：

```text
SESSDATA
bili_jct
DedeUserID
DedeUserID__ckMd5
```

不要把真实 Cookie 提交到 GitHub、公开网页、群聊或日志中。

修改 Compose 文件后，必须重新创建 RSSHub 容器，让新的环境变量生效：

```bash
cd /www/wwwroot/rsshub
docker compose up -d --force-recreate rsshub
```

旧版 Docker Compose 使用：

```bash
docker-compose up -d --force-recreate rsshub
```

查看容器状态：

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
```

查看 RSSHub 日志：

```bash
docker logs --tail=150 rsshub-rsshub-1
```

## 测试 RSSHub

RSSHub B 站用户动态路由格式：

```text
http://服务器IP:1200/bilibili/user/dynamic/UP主UID
```

例如：

```text
http://服务器IP:1200/bilibili/user/dynamic/161775300
```

如果 Hoshino 和 RSSHub 在同一台服务器，并且 Hoshino 直接运行在宿主机上，推荐使用：

```text
http://127.0.0.1:1200/bilibili/user/dynamic/161775300
```

在服务器本机测试：

```bash
curl -i --max-time 60 \
  "http://127.0.0.1:1200/bilibili/user/dynamic/161775300"
```

正常应返回：

```text
HTTP/1.1 200 OK
```

并且响应正文为 RSS/XML。

如果只访问：

```text
http://服务器IP:1200
```

只能说明 RSSHub 主服务可以打开，不能说明 B 站路由已经成功。

## Hoshino 使用 RSSHub

当前改版代码默认启用 RSSHub，并默认访问：

```text
http://127.0.0.1:1200
```

也可以通过环境变量调整：

```bash
export BILINOTICE_RSSHUB_ENABLED=1
export BILINOTICE_RSSHUB_URL=http://127.0.0.1:1200
export BILINOTICE_RSSHUB_TIMEOUT=20
```

建议把环境变量写进 Hoshino 的启动脚本或 systemd service 中，而不是只在临时终端执行。

如果 Hoshino 也是 Docker 容器，不能使用：

```text
http://127.0.0.1:1200
```

因为容器中的 `127.0.0.1` 指向 Hoshino 容器自身。此时应使用同一个 Docker Compose 网络中的服务名：

```text
http://rsshub:1200
```

如果 Hoshino 运行在宿主机，RSSHub 在 Docker 中，使用：

```text
http://127.0.0.1:1200
```

## RSSHub 读取内容

Hoshino 会读取 RSS/Atom 中的：

```text
title
description
content:encoded
summary
guid
link
pubDate
published
updated
media:content
enclosure
img
video
```

标题处理规则：

1. 有正式标题时使用正式标题。
2. 标题是“`UP主名的动态`”时，截取 RSS 正文前 50 个字符并添加 `...`。
3. 视频没有正文时使用视频标题。
4. 没有可读取文字时使用“发布了一条动态”。

媒体处理规则：

1. 优先读取 RSS 中的图片和附件。
2. 视频动态优先使用视频封面。
3. 能生成图片卡片就发送图片卡片。
4. 图片下载或渲染失败时发送动态链接，避免完全漏推。

## 使用方法

### 关注 UP 主

在群内 @机器人发送：

```text
关注 UID
```

例如：

```text
关注 353840826
```

也可以使用昵称：

```text
关注 公主连结ReDive
```

昵称搜索依赖 B 站登录 Cookie 和 WBI。网络核查失败时，建议不要开启非法关注兜底：

```ini
allow_follow_illegal = false
```

否则联网核查失败时可能只记录 UID，并不代表真的成功获取了 UP 信息。

### 取关 UP 主

```text
取关 UID
```

例如：

```text
取关 353840826
```

### 查看本群关注

```text
看看成分
```

或：

```text
本群关注
```

### 查看所有关注

机器人管理员可以发送：

```text
所有关注
```

或：

```text
所有群关注
```

### 关键词管理

添加关键词：

```text
bili-ctl black-words 353840826 add 恰饭 广告
```

查看关键词：

```text
bili-ctl black-words 353840826 list
```

删除关键词：

```text
bili-ctl black-words 353840826 remove 广告
```

### 昵称管理

给 UP 主添加短昵称：

```text
bili-ctl add-nick 353840826 公主连结
```

查看昵称：

```text
bili-ctl list-nick 353840826
```

删除昵称：

```text
bili-ctl del-nick 353840826 公主连结
```

### 重新加载关注列表

修改 `uppers/list.json` 后，可以使用：

```text
bili-ctl reload
```

也可以直接重启 HoshinoBot。

## 常见问题

### RSSHub 首页能打开，但 B 站路由一直转圈

先测试：

```bash
curl -i --max-time 60 \
  "http://127.0.0.1:1200/bilibili/user/dynamic/161775300"
```

再查看：

```bash
docker logs --tail=200 rsshub-rsshub-1
```

如果日志只有：

```text
GET /bilibili/user/dynamic/161775300
```

没有返回日志，说明路由在抓取 B 站时卡住。

### RSSHub 返回 `-101 账号未登录`

说明 RSSHub 没有收到对应 UID 的 Cookie。检查：

```yaml
BILIBILI_COOKIE_161775300: '你的完整Cookie'
```

然后重新创建容器：

```bash
docker compose up -d --force-recreate rsshub
```

检查环境变量是否存在，但不显示 Cookie 内容：

```bash
docker exec rsshub-rsshub-1 sh -c \
'env | grep "^BILIBILI_COOKIE_" | sed "s/=.*$/=[已配置]/"'
```

### B 站返回 `-352` 或 `-412`

这表示 B 站风控，不是 RSS XML 解析错误。建议：

- 停止频繁刷新和测试。
- 增大 Hoshino 的 `poll_time`。
- 确认 Cookie 没有过期。
- 不要多个服务高频共用同一 Cookie。
- 必要时更换网络出口。

### Hoshino 只发链接，不发图片

查看日志中是否有：

```text
图片下载失败
图片卡片生成失败
RSSHub请求失败
```

只发链接是保护性兜底，不表示动态没有读取到。

### 动态图片有了，但文字为空

先确认日志级别：

```ini
log_level = debug
```

如果使用 RSSHub，检查 RSS 中是否有 `title` 或 `description`。有些动态是纯图片动态，文字只存在图片像素中，普通 RSS/XML 解析无法读取，需要 OCR 才能识别。

### 视频没有图片

确认：

- 已替换最新版 `dymgr.py`
- 已替换兼容版 `res/getImg.py`
- 已放置 `res/httpx_compat.py`
- Pillow 版本满足其它插件要求
- 日志中没有图片下载异常

视频标题优先使用 RSS 的标题或 B 站视频卡片标题，视频封面优先使用 RSS 附件或视频卡片封面。

### 同一个动态重复推送

检查对应文件：

```text
uppers/UID.json
```

其中的 `history` 保存已处理动态 ID。不要随意清空整个 history；测试单条动态时只删除对应动态 ID。

### 嘉然自动出现

检查：

```text
uppers/list.json
```

删除 UID：

```text
672328094
```

这是原仓库示例关注数据，不是代码自动关注。

## 安全注意事项

- B 站 Cookie 等同于登录凭证，不能公开分享。
- 不要把 `bili_cookie.txt`、Compose 文件中的真实 Cookie 或完整 Docker 环境变量提交到 Git。
- 修改 Cookie 后需要重新创建 RSSHub 容器。
- 建议限制 Cookie 文件权限：

```bash
chmod 600 /www/wwwroot/HoshinoBot-master/hoshino/modules/bili-notice-hoshino/res/bili_cookie.txt
```

- 建议限制 RSSHub 的公网访问，或使用 Nginx、访问密钥和防火墙控制访问来源。

## API 说明

插件内部动态结果的基本结构：

```python
{
    "nickname": str,
    "uid": int,
    "type": str,
    "subtype": str,
    "time": int,
    "pic": str,
    "link": str,
    "sublink": str,
    "group": list,
}
```

其中：

- `pic` 是 `base64://` 开头的图片字符串；
- `link` 是动态链接；
- `group` 是需要接收推送的群号列表。

## 鸣谢

- [Ice-Cirno/HoshinoBot](https://github.com/Ice-Cirno/HoshinoBot)
- [kushidou/bili-notice-hoshino](https://github.com/kushidou/bili-notice-hoshino)
- [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)
- [DIYgod/RSSHub](https://github.com/DIYgod/RSSHub)
- [AstrBot-Elementary-School/astrbot_plugin_rsshub](https://github.com/AstrBot-Elementary-School/astrbot_plugin_rsshub)
