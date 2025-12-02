# bs_plugin_message_filter
基于BotShepherd的消息过滤插件

## 框架介绍

[🐑 BotShepherd](https://github.com/syuan326/BotShepherd)
BotShepherd 是一个基于OneBot v11协议WebSocket代理和管理系统，统一管理和协调多个Bot实例，实现一对多的连接管理、消息统计、跨框架黑名单、全框架分群组功能开关和别名防冲突。

人话：一个账号只需要一个ws连接接入本系统，就可以自由的连接到下游框架。本系统可以方便的统计单个账号消息量，管理黑名单，进行指令转化等。你不再需要为每个账号创建一个Nonebot或配置 账号数量x框架数量 个ws连接

## 灵光一现

**BotShepherd**既然是QQ与Bot的桥梁，那么就可以在**BotShepherd**拦截OneBot消息体，修改然后放行，那么这里面就有大文章了（bushi）

## 刨坑（咕咕咕）

除了更改消息体，我们还可以从中提取text类型，经过渲染之后可以变成`旮旯给木`的图片

## 使用教程

在`框架根目录`下执行

```bash
git clone https://github.com/syuan326/bs_plugin_message_filter.git ./app/plugins/bs_plugin_message_filterter
```

运行一次框架后会得到一个原始json文件，可参考下一章节去配置

```json
{
  "enabled": true
}
```

## Json结构

```json
{
  "enabled": true, 

  "text": [
    {
      "mode": "replace",
      "args": [
        ["原词", "新词"],
        ["坏话", "***"]
      ]
    },
    {
      "mode": "prepend",
      "args": "【前缀】"
    },
    {
      "mode": "append",
      "args": "【后缀】"
    }
  ],

  "image": [
    {
      "mode": "set_summary",
      "args": "这是一张图片"
    },
    {
      "mode": "append_summary",
      "args": "（已处理）"
    },
    {
      "mode": "replace_file",
      "args": "file:///C:/xxx/xxx.png"
    },
    {
      "mode": "remove"
    }
  ]
}
```

enabled: 插件启停开关
第一层是OneBot消息类型
第二层是具体操作
第三层是操作参数

---

## 测试

![111](https://gitee.com/Elvin-Apocalys/pic-bed/raw/master/git_img/gitpng.png)

## 增减操作或获取OneBot消息体另谋他路

在**plugin.py**第192行到第200行间，`segments`变量是捕获到的原始消息体，`new_segments`是处理过的消息体

## 鸣谢

- [小维](https://github.com/Loping151) - xw跑路
- [小维的框架](https://github.com/syuan326/BotShepherd) - 让Bot管理变得简单而强大 🐑✨
