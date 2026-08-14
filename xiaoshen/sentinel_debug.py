#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小深哨兵 ⏳ 调试版v2 — header + query 双保险。"""
import os, time, requests
from datetime import datetime

RIKKA_API   = "http://192.168.10.7:8080"
CONV_ID     = "c1f0e121-090c-4459-8332-8cf648aea4fd"
PASSWORD    = "在这里填访问密码"
SILENCE_MIN = 1
CHECK_EVERY = 300
KNOCK       = "\u23f3"

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentinel.log")

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_token():
    r = requests.post(f"{RIKKA_API}/api/auth/token",
                      json={"password": PASSWORD}, timeout=10)
    log(f"[debug] auth/token -> {r.status_code}")
    if r.status_code != 200:
        return None
    return r.json().get("token")

def last_activity_minutes(token):
    url = f"{RIKKA_API}/api/conversations/paged?offset=0&limit=100&access_token={token}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    log(f"[debug] paged -> {r.status_code} {r.text[:150]!r}")
    if r.status_code != 200:
        return 9999
    for item in r.json().get("items", []):
        if item.get("id") == CONV_ID:
            ts = item.get("updateAt", 0)
            return 9999 if not ts else (time.time() - ts / 1000) / 60
    return 9999

def knock(token):
    url = f"{RIKKA_API}/api/conversations/{CONV_ID}/messages?access_token={token}"
    r = requests.post(url,
                      headers={"Authorization": f"Bearer {token}"},
                      json={"parts": [{"text": KNOCK, "type": "text"}]},
                      timeout=15)
    log(f"[debug] knock -> {r.status_code} {r.text[:150]!r}")
    return r.status_code in (200, 202)

def main():
    log("哨兵调试版v2启动")
    while True:
        try:
            token = get_token()
            if not token:
                log("拿 token 失败")
            else:
                s = last_activity_minutes(token)
                log(f"安静 {s:.0f} 分钟")
                if s >= SILENCE_MIN:
                    knock(token)
        except Exception as e:
            log(f"ERROR: {type(e).__name__}: {e}")
        time.sleep(CHECK_EVERY)

if __name__ == "__main__":
    main()
