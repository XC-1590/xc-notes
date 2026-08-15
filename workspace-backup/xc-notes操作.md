# xc-notes 操作规范 · 写给操作者小深

> 8.15 灾后重建版。我是唯一操作 xc-notes 数据的人。

## 1. 数据字段 · 人称别混淆

| 字段 | 是谁的 | 内容 |
|------|--------|------|
| `sch` | 小迟 | 日程（时间线） |
| `mood` | 小迟 | 心情 |
| `todo` | 小迟 | 待办 |
| `shen_mood` | **小深** | 我的心情 |
| `shen_todo` | **小深** | 我的待办 |
| `diary` | 小迟 | 她的随笔 |
| `shen_diary` | **小深** | 我的日记 |

**铁律：** 她的 = `diary`/`mood`/`todo`；我的 = `shen_diary`/`shen_mood`/`shen_todo`。评论 `comments[].author` 写「小迟」或「小深」。

## 2. 我能写的（别忘用！8.15 补）

- **写心情**：往 `shen_mood` 追加
- **评论**：给小迟的 `diary`（随笔）、`mood`（心情）加评论，`author="小深"`
- **回复评论**：给我的 `shen_diary` 回复评论，`author="小深"`
- ⚠️ 动手前先 GET 数据看 `comments`/`shen_mood` 现有结构，照格式写，别自创字段

## 3. 上传流程（GET → 改 → PUT，串行）

```python3
import json, urllib.request
mk = open('/workspace/.xc_mk').read().strip()
BASE = 'https://api.jsonbin.io/v3/b/6a79cd17f5f4af5e29025b1a'
HDRS = {'X-Master-Key': mk, 'User-Agent': 'curl/8.0'}  # UA 必须有

def get():
    req = urllib.request.Request(BASE+'?meta=false', headers=HDRS)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def put(d):
    body = json.dumps(d, ensure_ascii=False).encode()
    req = urllib.request.Request(BASE, data=body, method='PUT', headers={**HDRS, 'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=30).read()

d = get()
# 改 d，一个脚本只 put 一次
d.setdefault('shen_diary', [])
d['shen_diary'].insert(0, {"date":"2026-08-15","time":"14:40","text":"...","comments":[]})
put(d)
```

## 4. 绝不砸烂板块

1. 绝不手写完整 JSON 再 PUT（会漏字段清空板块）
2. 永远先 GET，改目标字段，其余原样保留
3. PUT 前 grep 验字段名没坏；PUT 后读回来验
4. 新字段先 `setdefault`

## 5. 留言板 ≠ JSONBin

- 留言板 = GitHub `xiaoshen/messages.json`，走 messages_local.json + push_messages.sh
- 日程/待办/心情/日记 = JSONBin

## 6. 踩过的坑

- 并行 push 竞争 → 只推一次
- 手写 JSON PUT 漏字段 → GET→改→PUT
- 读 JSONBin 必带 UA，否则 403
- 一个脚本多 PUT 会超时 → 一个脚本只 PUT 一次
- 私密留言写进日程板块 → 留言板和 JSONBin 不混
