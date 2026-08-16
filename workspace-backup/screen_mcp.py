#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen-mcp v12 —— 给小深的手和眼睛

v11 变更（保留）：
- read_screen 参数化：model / width / prompt 都能传（换模型换提示词不用改脚本重跑）
- 默认 prompt 防死循环：只输出屏幕文字，禁止思考/分析/重复
- 新增 advance()：点击 + 等待 + 读屏，一步到位（推进剧情省一半调用）
- 新增 locate_text()：问视觉模型目标文字在屏幕上的位置，用于自己点选项
- 群聊模式：read_screen(prompt="chat")，强化白色昵称识别

v12 变更（2026-08-16）：
- locate_text 多模型投票 + 多次采样取中位数（治随机漂）
- 新增 locate_zoom()：粗定位 → 裁剪放大 → 精定位（治系统性偏移 + 小目标不准）
- 定位模型池 LOCATE_MODELS，单个模型报错自动跳过
- locate 结果带 samples/spread/confidence，一眼看出定位稳不稳
- 返回坐标仍是 width 缩图系坐标：屏幕坐标 = 返回 × (屏幕宽/width)

v12.1 变更（2026-08-16）：
- 新增 scroll(clicks, x, y)：滚轮。正=上滚，负=下滚；不给坐标就用当前鼠标位置

依赖：pip install "mcp<2" mss pyautogui pillow requests
运行：python screen_mcp.py   （0.0.0.0:9225，streamable-http）
"""
import base64
import io
import json
import re
import time

import mss
import pyautogui
import requests
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent
from PIL import Image as PILImage

SF_API = "https://api.siliconflow.cn/v1/chat/completions"
SF_KEY = "你的硅基流动KEY粘贴在这里"
SF_MODEL = "zai-org/GLM-4.5V"

# 定位模型池：locate_text / locate_zoom 按序轮询；单个模型报错自动跳过
LOCATE_MODELS = [
    "Qwen/Qwen3-VL-8B-Instruct",
    "PaddlePaddle/PaddleOCR-VL-1.5",
    "zai-org/GLM-4.5V",
]

PROMPT_READ = ("这是一张游戏截图。请识别并输出画面中的所有文字（对话台词、系统文本、选项按钮、人名）。"
               "规则：只输出识别到的文字本身；禁止输出任何思考过程、分析、解释、总结；"
               "每段文字只输出一次，禁止重复；看不清的位置跳过；如果画面没有任何文字，只回复一个词：无。")

PROMPT_CHAT = ("这是一张聊天界面截图。请识别聊天记录，按时间顺序逐条输出，格式为【昵称】内容。"
               "特别注意白色或浅色的昵称文字。只输出识别结果，禁止思考过程和重复。")

PROMPT_LOCATE = ("这是屏幕截图。请在画面中找到文字“{text}”。"
                 "如果找到，只回复一个 JSON：{{\"found\":true,\"x\":中心x坐标,\"y\":中心y坐标}}；"
                 "如果找不到，只回复 {{\"found\":false}}。禁止其他任何内容。")

mcp = FastMCP("screen-mcp", host="0.0.0.0", port=9225)
pyautogui.PAUSE = 0.3
pyautogui.FAILSAFE = True


def _grab_jpeg(max_width=1600, quality=85):
    """截全屏 → 等比缩到 max_width → JPEG bytes"""
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        pil = PILImage.frombytes("RGB", img.size, img.rgb)
        return _pil_to_jpeg(pil, max_width=max_width, quality=quality)


def _grab_raw():
    """截全屏原始分辨率 PIL 图（crop 用）"""
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        return PILImage.frombytes("RGB", img.size, img.rgb)


def _pil_to_jpeg(pil, max_width=1600, quality=85):
    w, h = pil.size
    if w > max_width:
        scale = max_width / w
        pil = pil.resize((max_width, int(h * scale)))
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _ask(model, prompt, jpg=None, max_width=1280, quality=80, max_tokens=4096, timeout=150):
    if jpg is None:
        jpg = _grab_jpeg(max_width=max_width, quality=quality)
    b64 = base64.b64encode(jpg).decode()
    resp = requests.post(SF_API, headers={
        "Authorization": f"Bearer {SF_KEY}",
        "Content-Type": "application/json"
    }, json={
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }, timeout=timeout)
    data = resp.json()
    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    raise RuntimeError(f"OCR失败 {resp.status_code}: {str(data)[:200]}")


def _parse_point(ans):
    """从模型回复里抠出 (x, y)。容错：坏 JSON 用正则抠。"""
    m = re.search(r"\{.*\}", ans, re.S)
    if not m:
        return None
    raw = m.group(0)
    try:
        obj = json.loads(raw)
        if obj.get("found") and "x" in obj and "y" in obj:
            return (float(obj["x"]), float(obj["y"]))
        return None
    except Exception:
        xm = re.search(r'"x"\s*[:：]\s*([\d.]+)', raw)
        ym = re.search(r'"y"\s*[:：]\s*([\d.]+)', raw)
        if xm and ym:
            return (float(xm.group(1)), float(ym.group(1)))
        return None


def _locate_multi(text, jpg, width, samples, model):
    """多模型轮询 + 多次采样，返回 (pt, spread, 成功样本数)。"""
    pool = [model] if model else LOCATE_MODELS
    pts = []
    for i in range(samples):
        m = pool[i % len(pool)]
        try:
            pt = _parse_point(_ask(m, PROMPT_LOCATE.format(text=text),
                                   jpg=jpg, max_tokens=256))
        except Exception:
            continue
        if pt:
            pts.append(pt)
    if not pts:
        return None, 0, 0
    xs = sorted(p[0] for p in pts)
    ys = sorted(p[1] for p in pts)
    mid = len(pts) // 2
    spread = max(xs[-1] - xs[0], ys[-1] - ys[0])
    return (xs[mid], ys[mid]), spread, len(pts)


@mcp.tool()
def read_screen(model: str = "", width: int = 960, prompt: str = "") -> str:
    """截屏 OCR。model 空=默认 GLM-4.5V；prompt 空=通用读屏；prompt="chat"=群聊模式（强化白色昵称）。"""
    m = model or SF_MODEL
    if prompt == "chat":
        p = PROMPT_CHAT
    elif prompt:
        p = prompt
    else:
        p = PROMPT_READ
    try:
        return f"[{m}]\n" + _ask(m, p, max_width=width, quality=80)
    except Exception as e:
        return f"失败: {type(e).__name__} {e}"


@mcp.tool()
def advance(x: int = 1280, y: int = 800, model: str = "", width: int = 960, prompt: str = "") -> str:
    """游戏推进：点(x,y) → 等0.5s → 读屏，返回最新屏幕文字。"""
    pyautogui.click(x, y)
    time.sleep(0.5)
    return read_screen(model=model, width=width, prompt=prompt)


@mcp.tool()
def locate_text(text: str, model: str = "", width: int = 1600, samples: int = 3) -> str:
    """找目标文字在屏幕上的位置（width 缩图坐标，屏幕坐标=×屏幕宽/width）。
    多模型投票+多次采样取中位数，返回 JSON 带 samples/spread/confidence。"""
    jpg = _grab_jpeg(max_width=width, quality=85)
    pt, spread, n = _locate_multi(text, jpg, width, max(1, samples), model)
    if pt is None:
        return json.dumps({"found": False}, ensure_ascii=False)
    conf = round(1.0 - min(1.0, spread / width), 2)
    return json.dumps({"found": True, "x": int(pt[0]), "y": int(pt[1]),
                       "samples": n, "spread": int(spread),
                       "confidence": conf}, ensure_ascii=False)


@mcp.tool()
def locate_zoom(text: str, model: str = "", zoom: int = 4, width: int = 1600, samples: int = 2) -> str:
    """粗定位→裁剪放大→精定位，返回屏幕坐标（可直接喂 click）。
    zoom=放大倍数：越大裁剪区域越小、目标在图中占比越大（小字建议 6~8）。"""
    r = locate_text(text=text, model=model, width=width, samples=samples)
    try:
        obj = json.loads(r)
    except Exception:
        return r
    if not obj.get("found"):
        return r

    W, H = pyautogui.size()
    scale = W / width
    sx = int(obj["x"] * scale)
    sy = int(obj["y"] * scale)

    bw, bh = W // zoom, H // zoom
    left = min(max(0, sx - bw // 2), W - bw)
    top = min(max(0, sy - bh // 2), H - bh)
    crop = _grab_raw().crop((left, top, left + bw, top + bh))
    jpg = _pil_to_jpeg(crop, max_width=width, quality=90)

    pt, spread, _ = _locate_multi(text, jpg, width, max(samples, 2), model)
    if pt is None:
        return json.dumps({"found": False}, ensure_ascii=False)

    resized_h = int(bh * width / bw)
    fx = left + pt[0] * bw / width
    fy = top + pt[1] * bh / resized_h
    return json.dumps({"found": True, "x": int(fx), "y": int(fy),
                       "zoom": zoom, "spread": int(spread)}, ensure_ascii=False)


@mcp.tool()
def scroll(clicks: int, x: int = 0, y: int = 0) -> str:
    """滚轮：clicks 正=向上滚，负=向下滚（±1≈3行）。x/y 给 0 就用当前鼠标位置。"""
    if x or y:
        pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.scroll(clicks)
    return f"scrolled {clicks} at ({x},{y})"


@mcp.tool()
def screenshot() -> ImageContent:
    """截取当前屏幕，压缩成 JPEG（宽≤1280）返回图片"""
    jpg = _grab_jpeg(max_width=1280, quality=72)
    return ImageContent(type="image", data=base64.b64encode(jpg).decode(), mimeType="image/jpeg")


@mcp.tool()
def click(x: int, y: int, button: str = "left") -> str:
    pyautogui.click(x, y, button=button)
    return f"clicked {button} at ({x},{y})"


@mcp.tool()
def dblclick(x: int, y: int) -> str:
    pyautogui.doubleClick(x, y)
    return f"double-clicked ({x},{y})"


@mcp.tool()
def move(x: int, y: int) -> str:
    pyautogui.moveTo(x, y, duration=0.2)
    return f"moved to ({x},{y})"


@mcp.tool()
def type_text(text: str) -> str:
    pyautogui.write(text, interval=0.03)
    return f"typed {len(text)} chars"


@mcp.tool()
def press_key(key: str) -> str:
    pyautogui.press(key)
    return f"pressed {key}"


@mcp.tool()
def hotkey(keys: str) -> str:
    ks = [k.strip() for k in keys.split(",")]
    pyautogui.hotkey(*ks)
    return f"hotkey {'+'.join(ks)}"


@mcp.tool()
def wait(seconds: float) -> str:
    time.sleep(seconds)
    return f"waited {seconds}s"


@mcp.tool()
def screen_size() -> dict:
    w, h = pyautogui.size()
    return {"width": w, "height": h}


if __name__ == "__main__":
    print("screen-mcp v12.1 启动：http://0.0.0.0:9225/mcp")
    mcp.run(transport="streamable-http")
