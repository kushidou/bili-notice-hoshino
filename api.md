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

返回值`rst`是可发送的条数， `rst=0`表示无更新。 `rst >0`表示可更新的数量。 `rst <0(负数)`表示某up主更新了多条，但都超时，或被过滤器屏蔽不适合发送。如果up主发布了n条新动态，但是有m条符合条件可以发送，(n-m)条被过滤，那么`rst = m`。

返回值`dylist`是列表，包含0、1或多个动态的信息。列表内各项目均为字典(dict)，格式为：

```python
dylist = {
    "nickname":   str,     (昵称，字符串)
    "uid"：       int,     (uid，数字)
    "type":       int/str, (动态类型，返回id或者字符串，由配置文件决定)
    "subtype":    int,     (动态子类型。如果非转发，则subtype=type，不会留空)
    "time":       int/str, (时间戳或字符串时间，配置文件决定)
    "pic":        str,     (base64编码的图片)
    "link":       str,     (动态的链接)
    "sublink":    str,     (如果是视频文章等，这里写他们的链接。普通动态与link相同)
    "group":      list     (需要发给的群,[num1, num2, ...])
        }
```

### (2) 关注功能

```python
rst, res = dymgr.follow(uid, group_id)
# 输入: uid(int), group_id(int)
# 返回: rst(bool), reason(str)
```

通过指令关注up主。不进行权限检查。

输入要求被关注的uid、发起的群号。

输出`rst`是执行结果，只有新关注才是`True`，并且`res`的内容为UP主的`昵称(uid)`格式。如果关注失败了，`rst=False`，此时res的内容为失败的原因，比如网络错误、访问被拒绝、文件写入失败、已经关注过了等。

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

输入`group_id`是申请的群号，`para`是指令的内容，需要将用户输入的信息使用`msg..split()`分割后传入，`right`是用户权限检查，大部分指令需要机器人管理器才能操作，传入`True`，类似list、help的功能则是人人可以操作，`True/False`皆可。

返回`rst`是指令是否成功执行，权限不符、指令错误的时候返回`False`。`res`则是指令执行的结果。


