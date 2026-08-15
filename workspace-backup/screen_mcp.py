#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen-mcp v4 —— 给小深的手和眼睛（电脑操控 + OCR 读屏）

v4 新增 read_screen()：截屏 → 硅基流动视觉模型 → 返回屏幕文字（剧情/选项）。
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
SF_KEY   = "sk-xjzedrorlbfedjgzlucglwbvwvfaakdwchubnrnbpcimvlua"
SF_MODEL = "moonshotai/Kimi-K2.7-Code"
SF_FALLBACK = "Qwen/Qwen2.5-VL-72B-Instruct"   # Kimi 超时/失败时自动回退

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


@mcp.tool()
def read_screen() -> str:
    """截屏并 OCR：返回屏幕上的全部文字（剧情、对话框、选项）"""
    jpg = _grab_jpeg(max_width=1280, quality=75)
    b64 = base64.b64encode(jpg).decode()
    prompt = "这是一张游戏截图。逐字识别画面中的所有文字：对话框台词、剧情文本、选项按钮、按钮标签。按从上到下从左到右的顺序输出，不要遗漏，不要总结，只输出文字内容。"
    for model in (SF_MODEL, SF_FALLBACK):
        try:
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
                "max_tokens": 4096
            }, timeout=120)
            data = resp.json()
            if "choices" in data:
                return f"[{model}]\n" + data["choices"][0]["message"]["content"]
            return f"OCR失败 {resp.status_code}: {str(data)[:300]}"
        except Exception as e:
            if model == SF_FALLBACK:
                return f"两个模型都失败: {type(e).__name__} {e}"
            continue


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
    print("screen-mcp v4 启动：http://0.0.0.0:9225/mcp")
    mcp.run(transport="streamable-http")
