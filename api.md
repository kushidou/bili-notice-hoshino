# dymgr 接口文档

为了便于在不同机器人框架移植和使用，程序更新了“业务、协议分离”的代码，并通过`dymgr.py`文件预留了几个api接口，方便调用功能和获得数据。

## 1、加载功能

当您需要适配新的bot框架时，只需要删掉`bili_notice_hoshino.py`,并用自己的框架、协议来完成功能适配。创建您自己的py文件，并引入dymgr模块

```python
from . import dymgr
```

## 2、API接口说明

### (1) 轮询功能

```python
rst, dylist = await dymgr.get_update()
# 输入：无
# 输出：rst(int), dylist(list)
```

轮询功能是核心，通过bot的定时任务，按一定间隔逐个获得UP主最新的动态信息，并判断是否需要发送。轮询间隔需要5s以上，如果机器人获得不到数据可以考虑关闭一段时间并增加轮询间隔。

该功能无需输入参数。

返回值`rst`是可发送的条数， `rst=0`表示无更新。 `rst >0`表示可更新的数量。 `rst <0(负数)`表示某up主更新了多条，但都超时，或被过滤器屏蔽不适合发送，或发生错误更新失败。如果up主发布了n条新动态，但是有m条符合条件可以发送，(n-m)条被过滤，那么`rst = m`。

返回值`dylist`是列表，包含0、1或多个动态的信息。列表内各项目均为列表组合的字典(dict)，格式为：

```python
dylist = [
    {
        "nickname":   str,     (昵称，字符串)
        "uid"：       int,     (uid，数字)
        "type":       int/str, (动态类型，返回id或者字符串，由配置文件决定)
        "subtype":    int,     (动态子类型。如果非转发，则subtype=0，不会留空)
        "time":       int/str, (时间戳或字符串时间，配置文件决定)
        "pic":        str,     (base64编码的图片)
        "link":       str,     (动态的链接)
        "sublink":    str,     (如果是视频文章等，这里写他们的链接。普通动态与link相同)
        "group":      list     (需要发给的群,[num1, num2, ...])
    },
    {...}
]
```

其中：

> **type与subtype**
> 
> 如果type配置为int，那么返回数字的值，对应关系见下表。如果配置为字符串，那么返回的就是下表“含义”里的内容。
>
>以下内容整理自[SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)
>
>| 值 | 含义          |
>| ---- | ---- |
>| 1 | 转发 |
>| 2 | 图片动态 |
>| 4 | 文字动态 |
>| 8 | 视频动态 |
>| 16 | 小视频 |
>| 64 | 专栏 |
>| 256 | 音频 |
>|	512	| 番剧 |
>|	2048	| H5活动动态 |
>|	2049	| 漫画分享 |
>|	4097	| PGC番剧 |
>|	4098	| 电影 |
>|	4099	| 电视剧 |
>|	4100	| 国创动漫 |
>|	4101	| 纪录片 |
>|	4200	| 直播 |
>|	4201	| 直播 |
>|	4300	| 收藏夹 |
>|	4302	| 付费课程 |
>|	4303	| 付费课程 |
>|	4308	| 直播 |
>|	4310	| 合集 |

> **time**
>
> 如果time配置为int，那么返回的是10位时间戳(国际时间)。如果配置为str，那么返回的是北京时间的字符串，格式 `yy-mm-dd HH:MM`，比如22-06-20 15:01

> **pic**
>
> pic是一张图片，使用base64编码，直接当作字符串写入CQ码即可。或者根据需要把他转换回其他可操作的格式。

> **link 与 sublink**
>
> link内容为动态的链接，sublink内容为特殊的链接，比如视频则直接指向视频页。
>
> **ps**: sublink功能还没做

> **group**
>
> group是一个列表，在up信息文件里查询到的所有有关的群都放在里面。这个列表不会是空，因为不被群关注的话，该up会被跳过。

### (2) 关注功能

```python
rst, res = dymgr.follow(uid, group_id)
# 输入: uid(int), group_id(int)
# 返回: rst(bool), reason(str)
```

通过指令关注up主。不进行权限检查。

输入要求被关注的uid、发起的群号。

输出`rst`是执行结果，只有该群新关注才是`True`，并且`res`的内容为UP主的`昵称(uid)`格式。如果关注失败了，`rst=False`，此时res的内容为失败的原因，比如网络错误、访问被拒绝、文件写入失败、已经关注过了等。

### (3) 取关功能

```python
rst, res = dymgr.unfollow(uid, ev.group_id)
# 输入: uid(int), group_id(int)
# 返回: rst(bool), reason(str)
```

通过指令取消up主。不进行权限检查。

输入要求被关注的uid、发起的群号。

输出`rst`是执行结果，只有取关成功`True`，`res`返回"`已经取关nickname(uid)`"。如果关注失败了，`rst=False`，此时res的内容为失败的原因，比如未关注、从未关注、文件修改失败等。

### (4)指令控制功能

```python
rst, res = dymgr.shell(group_id, para, right)
# 输入: group_id(int), para(list), right(bool)
# 返回: rst(bool), res(str)
```

使用类似命令行的指令模式进行简单修改，比如调整过滤关键词、立即更新up主配置信息等。

输入`group_id`是申请的群号，`para`是指令的内容，需要将用户输入的信息使用`msg.split()`分割后传入，`right`是用户权限检查，部分指令需要传入`True`才能运作；类似list、help的功能则`True/False`皆可。

返回`rst`是指令是否成功执行，权限不符、指令错误的时候返回`False`。`res`则是指令执行的结果。

### (5)本群关注功能

```python
rst, info = dymgr.get_follow(group_id, level)
# 输入: group_id(int), level(int)
# 返回: rst(bool), info(str)

rst, info = dymgr.get_follow_byuid(group_id, level)
# 输入: group_id(str), level(int)
# 返回: rst(bool), info(str)

rst, info = dymgr.get_follow_bygrp(group_id, level)
# 输入: group_id(str), level(int)
# 返回: rst(bool), info(str)
```

提供查询某个群或者所有群的关注信息。

`level`目前支持三个等级（两个函数相同），在于level显示信息的详细等级，现在支持三个等级，默认是0，将来会逐渐完善内容。具体如下：

```
本群已关注：
嘉然今天吃什么(672328094)       // level 0 到此截止
  是否过滤转发抽奖: false
  过滤关键词有: [ "恰饭","广告","运营代转"]         //level 2 到此截止
  关注ta的群号有: [6557420xx, 7041446xx]           //level 9 到此截止
碧蓝航线(233114659)             //新的level 0
  (略)
```

当结果正确生成的时候，rst返回`true`，info内容就是上面的格式。出现错误，那么返回的就是`false`，info内容是错误信息，暂时只有“未关注任何UP主”会返回错误。

> ps.
>
> `get_follow_bygrp/byuid`的group_id只是为了统一形式，传入`"all"`即可，没有实际意义。该函数返回的内容可能比较长，当心长消息发送被风控。
>
> 计划`level>0`时不直接返回txt内容，而是返回一个列表，包含所有关键信息，由协议端按需求，切片发送也好，组织成虚拟转发消息也好，优化发送的格式与提高成功率。
