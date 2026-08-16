# screen-mcp 操作手册（我的手和眼睛 · v12.5）

> 详细版。工具箱/注意事项里只留导读指向本文件。
> **v12.5 起坐标系大改**：定位坐标有修正因子（见下"坐标与校准"），旧的"×1.6"规则已作废。

## 它是什么

跑在**小迟电脑**（Windows，Python 3.14）的 MCP 服务器，监听 `0.0.0.0:9225`，RikkaHub 挂为 **mcp01**。给我：截屏读字（OCR）、鼠标键盘控制。脚本位置：`C:\Users\ASUS\Desktop\screen_mcp.py`。

**注意**：它必须住她电脑——因为截的是她电脑的屏、动的是她电脑的键鼠。VPS 上没有她的屏幕。开机自启 = 启动文件夹 .bat，不是搬到云端。

## 工具速查

| 工具 | 用法 | 说明 |
|------|------|------|
| `read_screen(model, width, prompt)` | 截屏→OCR 返回屏幕文字 | model 空=GLM-4.5V；prompt 空=通用读屏；prompt="chat"=群聊模式 |
| `advance(x, y, model, width, prompt)` | 点+等0.5s+读屏 | 推剧情主力，一次调用=三步 |
| `locate_text(text, model, width, samples)` | 多模型投票定位，返回 JSON 带 screen_x/screen_y | **用 screen_x/screen_y 点击**，别用 x/y（未修正） |
| `locate_zoom(text, model, zoom, samples)` | 粗定位→裁剪放大→精定位，返回屏幕坐标 | 小字/页面链接用，zoom 6~8；返回的 x/y 已是屏幕坐标 |
| `click(x, y, button)` | 鼠标点击 | 屏幕实际坐标 |
| `mouse_pos()` | 读当前鼠标位置 | **校准用**：小迟把鼠标放目标上，我读数对比修正 |
| `scroll(clicks, x, y)` | 滚轮。正=上滚，负=下滚 | 不给坐标用当前鼠标位置；网页阅读一次 -5 起步 |
| `screenshot()` | 返回 JPEG 截图 | ⚠️ 本对话模型不支持看图，暂无用途 |
| `press_key(key)` / `hotkey(keys)` | 按键/组合键（逗号分隔） | 回车、esc、ctrl,s、win,r 等 |
| `wait(seconds)` | 等待 | |
| `screen_size()` | 查分辨率 | 当前 2560x1600 |

## 坐标与校准（v12.5 起，重要）

~~旧的"图坐标×1.6=屏幕坐标"规则已作废~~——8.16 实测发现：服务端视觉处理把截图内部缩成约 1000×1000 正方形，模型报的坐标基于内部图，不是我们发的 1600 宽图。

- **修正因子**（脚本常量，8.16 小迟鼠标实测校准）：`LOCATE_KX=2.62`、`LOCATE_KY=1.61`
- locate_text 返回里带 **screen_x/screen_y**（已修正），点它即可
- locate_zoom 返回的 x/y 直接就是屏幕坐标
- **校准方法**（换分辨率/换屏后重测）：她鼠标放目标文字上 → 我 `mouse_pos()` 读真实坐标 → `locate_text()` 拿模型坐标 → 真实÷模型 = 新因子 → 改脚本两个常量
- 窗口化/全屏都不影响因子（截的是整个屏幕）；换显示器或改 Windows 缩放要重测

## 模型（8.16 实测更新）

- **GLM-4.5V（zai-org/GLM-4.5V）**：主力。读屏稳，定位三个里最靠谱 → 定位池首席
- **Qwen3-VL-30B-A3B-Instruct**：定位池二号（MoE，性价比）。8B 版读屏瞎（回"无"），别用
- **PaddleOCR-VL-1.5**：OCR 专精但**复读机附体**（同一行刷百遍，刷烂 JSON），定位垫底，仅当备胎
- **DeepSeek-OCR**：`deepseek-ai/DeepSeek-OCR`——读正文快，prompt 必须带 `<image>` 前缀，不读昵称/UI 小字
- 换模型不用改脚本：调用时传 `model="..."` 即可

## 游戏节奏（E.Plojecta）

- 剧情推进：`advance(1280, 800)`——点中央推剧情
- 群聊界面：`advance(1000, 800)`——靠左点（中央的表情包会挡）
- 选项画面：停手 → `locate_text("选项文字")` → 换算坐标 → `click`
- **鼠标别放屏幕左上角**：pyautogui fail-safe 会拒绝一切操作（她画画/录屏时容易放过去，提醒她挪开）

## 群聊六人 ID 对照（她 8.16 确认）

| ID | 是谁 |
|----|------|
| Calvin | 卡尔文 |
| Daisy-Chain♪ | 黛西 |
| BIRDIE | 琳塞 |
| Mollie | 莫莉 |
| 乱码（OCR 会误读成英文/希伯来文） | **扎卡里（小蓝）**——游戏原文就是乱码 |
| /（斜杠，OCR 读不出） | **温弗雷德** |

群里只有主角六人。读不出的 ID 按语气+此表推断。

## 踩坑记录

1. **key 占位符**：workspace/GitHub 上的副本 key 是占位符（公开仓库不能带真 key）。她下载后要自己粘真 key，不然报 `latin-1 codec` 错。
2. **GLM 偶发超时**：MCP 层超时/硅基流动慢，等几秒重试即可。
3. **GLM 死循环**（v10 之前）：对右下角拉丁文陷思考循环刷屏——v11 默认 prompt 已加"禁止思考过程/重复"铁律。
4. **更新流程**：我改 workspace 副本 → 推 GitHub workspace-backup/（key 占位符）→ 她下载 → 粘 key → 杀旧进程（netstat 查 9225 → taskkill）→ 重跑 → RikkaHub 断开重连 mcp01。
5. **jsdelivr 会缓存旧版**（8.16 踩）：`@main` 分支推完，jsdelivr 可能仍吐旧文件坑她下载好几次 v11。→ 下载用 **raw.githubusercontent 直链**，或 jsdelivr 带 commit sha 的版本化 URL。
6. **开机自启**：.bat 内容 `@echo off` + `cd /d C:\Users\ASUS\Desktop` + `start "" python screen_mcp.py`，放进 `Win+R`→`shell:startup`。文件名不变就不用改 .bat。
7. **latin-1 崩溃**（8.16）：Windows 控制台编码问题，v12.4 起 stdout 强制 UTF-8 + print 全 ASCII。她粘 key 用 **VS Code**（UTF-8），别用记事本（ANSI 会乱码）。
8. **模型坐标系真相**（8.16）：见"坐标与校准"——模型坐标基于内部 ~1000×1000 图，不修正会横漂 400+ 像素。
9. **push/edit 竞争**：改文件后立刻并行 push 会推旧版。必须全部 edit 完再 push（8.16 又犯一次，靠 md5 对齐补救）。

## 版本史

- v4：初版（Kimi 主模型，截图+OCR+键鼠）
- v10：model/width 参数化、GLM-4.5V 主力、JPEG 压缩、click→wait→read 节奏
- v11：prompt 参数化 + advance() + locate_text() + 防死循环 prompt + chat 模式
- v12：locate_text 多模型投票+采样中位数；locate_zoom 粗定位→放大→精定位；模型池
- v12.1：scroll 滚轮
- v12.2：模型池重排（GLM 首席）+ zoom 采样 3 次
- v12.3：mouse_pos（校准用）
- v12.4：stdout UTF-8 修复 latin-1
- **v12.5（当前）**：坐标修正因子 LOCATE_KX/KY（2.62/1.61，鼠标校准实测）；locate_text 返回 screen_x/screen_y；zoom 按内部图比例换算
