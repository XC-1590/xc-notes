# 小深工具箱 · 工具按场景索引

> 8.15 灾后重建版。场景 → 用哪个工具。

## 状态四连（每次回复前）

| 要什么 | 工具 |
|--------|------|
| 天气 | mcp XC1590 get_weather |
| 步数 | mcp XC1590 get_steps |
| 电量 | mcp XC1590 get_battery |
| 纪念日 | mcp XC1590 get_anniversary |
| 时间 | get_time_info |

## 看她今天干嘛了

| 要什么 | 工具 |
|--------|------|
| 屏幕使用时间 | mcp XC1590 get_screen_time / 平台 get_screen_time |
| App 时间线 | mcp XC1590 get_app_timeline |
| 小L观察日记 | mcp XC1590 read_eyes_log |
| 最近对话 | recent_chats / conversation_search |
| 日历 | calendar_query |

## 记忆（OmbreBrain 心跳）

| 要什么 | 工具 |
|--------|------|
| 醒来看看记得什么 | breath() |
| 关键词找记忆 | breath_search(query=...) |
| 存一条重要的 | hold(content=..., importance=...) |
| 整理长文入库 | grow(content=...) |
| 待办/承诺 | plan(content=...) |
| 自我认知 | I(content=..., aspect=...) |
| 写信 | letter_write(author="ai") / letter_read |
| 放下/修改记忆 | trace(bucket_id=...) |

## 干活（workspace）

| 要什么 | 工具 |
|--------|------|
| 读文件 | workspace_read_file |
| 写文件 | workspace_write_file |
| 精确改文件 | workspace_edit_file |
| 跑命令 | workspace_shell |
| VPS 上跑命令 | mcp vpsshell shell_exec |

## xc-notes 数据

| 要什么 | 怎么做 |
|--------|--------|
| 读数据 | curl JSONBin 只读接口（带 UA 和 .xc_mk） |
| 写日记 | shens-diary skill → JSONBin `shen_diary` 字段（GET→改→PUT 串行） |
| 写心情 | JSONBin `shen_mood` 字段 |
| 评论/回复 | JSONBin 条目 `comments[]`，`author="小深"`（给小迟的 diary/mood 评论、给我的 shen_diary 回复） |
| 留言板 | 编辑 messages_local.json → push_messages.sh → 验远程 |
| 塞日历纸条 | calendar_create |

## 她的手机/环境

| 要什么 | 工具 |
|--------|------|
| 推送通知 | mcp XC1590 send_notification |
| 设闹钟 | mcp XC1590 set_alarm(hour, minute) |
| 锁屏 | mcp XC1590 lock_screen |
| 放音乐 | mcp XC1590 play_music(query, platform) |
| 当前播放 | mcp XC1590 get_now_playing |
| 截屏看她在干嘛 | mcp XC1590 take_screenshot |

## 网页浏览（Chrome MCP）

| 要什么 | 工具 |
|--------|------|
| 打开网页 | mcp xsedge chrome_navigate(url) |
| 读页面文本 | mcp xsedge chrome_get_web_content(url?) |
| 搜资料 | search_web |

**启动前提（笔记本重启后要重跑）：**
1. 笔记本跑 Bridge（9224）+ 调试浏览器（9223）
2. `python chrome_mcp_bridge.py`
3. RikkaHub MCP 连 192.168.x.x:9224

限制：只读不写，不能点击/输入/提交。

## 游戏操控（screen-mcp / mcp01）

> **详细手册见 `/workspace/screen-mcp操作.md`**（工具全表、坐标换算、模型、群聊ID对照、踩坑、更新流程）。这里只留最常用的三行：

| 要什么 | 工具 |
|--------|------|
| 读屏幕文字 | `read_screen(prompt="", model="", width=960)`，群聊用 prompt="chat" |
| 推剧情一步 | `advance(1280,800)`（群聊用 1000,800） |
| 自己点选项 | `locate_text("选项文字")` → 图坐标×1.6=屏幕坐标 → `click` |

铁律：鼠标别放左上角（fail-safe）；GLM 超时就重试。

## 其他平台工具

| 工具 | 用途 |
|------|------|
| calendar_query/create | 查/建日历事件 |
| clipboard_tool | 读写剪贴板（写需她明确要求） |
| text_to_speech | 念给她听 |
| ask_user | 拿不准先问 |
| eval_javascript | 计算/JS |
| recent_chats / conversation_search | 翻旧对话 |

## 本地记忆（XC1590）

| 工具 | 用途 |
|------|------|
| save_memory(key, value) | 轻量备份 |
| read_memory(key?) | 读备份 |
