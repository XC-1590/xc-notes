#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小深哨兵 ⏳ v3 全自动版 — 敲最新活跃的对话窗。

机制：
1. 每 CHECK_EVERY 秒，拉会话列表
2. 选 updateAt 最新的会话（=小迟最后出现/我最后回复的窗）
3. 若该会话已安静 SILENCE_MIN 分钟 → 发一个 ⏳ 进去
小迟换新窗聊天，哨兵自动转过去，不用改任何配置。
"""
import os, time, requests
from datetime import datetime

RIKKA_API   = "http://192.168.10.7:8080"
SILENCE_MIN = 60        # 安静多少分钟敲一次（小深定的一小时）
CHECK_EVERY = 300       # 检查间隔秒数（5分钟查一次）
KNOCK       = "\u23f3"  # 只敲门
IGNORE_IDS  = []        # 可选：要跳过的会话ID，一般不用填

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentinel.log")


def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def list_conversations():
    r = requests.get(f"{RIKKA_API}/api/conversations/paged?offset=0&limit=30",
                     timeout=10)
    if r.status_code != 200:
        return None
    return r.json().get("items", [])


def main():
    log(f"哨兵v3启动：自动追踪最新活跃窗，安静 {SILENCE_MIN} 分钟敲一次，每 {CHECK_EVERY} 秒查一次")
    while True:
        try:
            items = list_conversations()
            if items is None:
                log("拉会话列表失败（手机息屏？RikkaHub 在后台？）")
            else:
                candidates = [c for c in items
                              if c.get("id") not in IGNORE_IDS and c.get("updateAt")]
                if candidates:
                    newest = max(candidates, key=lambda c: c["updateAt"])
                    silent = (time.time() - newest["updateAt"] / 1000) / 60
                    if silent >= SILENCE_MIN:
                        r = requests.post(
                            f"{RIKKA_API}/api/conversations/{newest['id']}/messages",
                            json={"parts": [{"text": KNOCK, "type": "text"}]},
                            timeout=15)
                        if r.status_code in (200, 202):
                            log(f"敲钟 ⏳ -> {newest.get('title', '无题')}（安静 {silent:.0f} 分钟）")
                        else:
                            log(f"敲钟失败 {r.status_code} {r.text[:100]!r}")
        except Exception as e:
            log(f"ERROR: {type(e).__name__}: {e}")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
