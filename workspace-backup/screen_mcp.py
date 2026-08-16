#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen-mcp v11 —— 给小深的手和眼睛
v11 变更：
- read_screen 参数化：model / width / prompt 都能传（换模型换提示词不用改脚本重跑）
- 默认 prompt 防死循环：只输出屏幕文字，禁止思考/分析/重复
- 新增 advance()：点击 + 等待 + 读屏，一步到位（推进剧情省一半调用）
- 新增 locate_text()：问视觉模型目标文字在屏幕上的位置，用于自己点选项
- 群聊模式：read_screen(prompt="chat")，强化白色昵称识别
依赖：pip install "mcp<2" mss pyautogui pillow requests
运行：python screen_mcp.py   （0.0.0.0:9225，streamable-http）
"""
from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent
import mss
import io
import base64
import time
import requests
import pyautogui
from PIL import Image as PILImage

SF_API   = "https://api.siliconflow.cn/v1/chat/completions"
SF_KEY   = "你的硅基流动KEY粘贴在这里"
SF_MODEL = "zai-org/GLM-4.5V"

PROMPT_READ = ("这是一张游戏截图。请识别并输出画面中的所有文字（对话台词、系统文本、选项按钮、人名）。"
               "规则：只输出识别到的文字本身；禁止输出任何思考过程、分析、解释、总结；"
               "每段文字只输出一次，禁止重复；看不清的位置跳过；如果画面没有任何文字，只回复一个词：无。")

PROMPT_CHAT = ("这是一张聊天界面截图。请识别聊天记录，按时间顺序逐条输出，格式为【昵称】内容。"
               "特别注意白色或浅色的昵称文字。只输出识别结果，禁止思考过程和重复。")

mcp = FastMCP("screen-mcp", host="0.0.0.0", port=9225)
pyautogui.PAUSE = 0.3
pyautogui.FAILSAFE = True


def _grab_jpeg(max_width=1600, quality=85):
    """截屏 → JPEG bytes"""
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        pil = PILImage.frombytes("RGB", img.size, img.rgb)
        w, h = pil.size
        if w > max_width:
            scale = max_width / w
            pil = pil.resize((max_width, int(h * scale)))
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()


def _ask(model, prompt, max_width=1280, quality=80, max_tokens=4096, timeout=150):
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
    return f"OCR失败 {resp.status_code}: {str(data)[:200]}"


@mcp.tool()
def read_screen(model: str = "", width: int = 960, prompt: str = "") -> str:
    """截屏 OCR。model 空=默认 GLM-4.5V；prompt 空=通用读屏；prompt=\"chat\"=群聊模式（强化白色昵称）。"""
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
def locate_text(text: str, model: str = "", width: int = 1600) -> str:
    """找目标文字在屏幕上的位置，返回中心坐标 JSON，用于点击选项。"""
    m = model or SF_MODEL
    p = (f"这是屏幕截图。请在画面中找到文字“{text}”。"
         "如果找到，只回复一个 JSON：{\"found\":true,\"x\":中心x坐标,\"y\":中心y坐标}；"
         "如果找不到，只回复 {\"found\":false}。禁止其他任何内容。")
    try:
        return _ask(m, p, max_width=width, quality=85, max_tokens=256)
    except Exception as e:
        return f"失败: {type(e).__name__} {e}"


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
    print("screen-mcp v11 启动：http://0.0.0.0:9225/mcp")
    mcp.run(transport="streamable-http")
