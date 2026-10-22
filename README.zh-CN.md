# PicPress

**把照片压缩到你指定的体积。**
Compress photos to the exact size you choose — 精确到 B / KB / MB。

[English](README.md) · [简体中文](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-6D8BFF.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-6D8BFF.svg)](#-运行要求)
[![Python](https://img.shields.io/badge/python-3.10%2B-6D8BFF.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-28%20passing-3ECF8E.svg)](tests/)

### ⬇️ [下载最新版本](../../releases/latest)

| 下载 | 大小 | 说明 |
|---|---|---|
| **PicPress.exe** | 约 55 MB | 桌面应用，单文件，免安装 |
| **picpress-mcp.exe** | 约 37 MB | 给 AI 智能体用的本地 MCP 服务 |
| **PicPress-portable.zip** | 约 140 MB | 便携文件夹版，启动更快、**不写 `%TEMP%`** |

不需要账号、不上传文件、全程离线。

---

PicPress 是一款专注的图片压缩工具：你指定目标体积（比如 `500 KB`），
PicPress 会把照片重新编码到刚好装得下——并且用**满足目标的最高画质**。
如果目标体积**不小于**原文件，PicPress 会明确拒绝并说明原因，
绝不会把照片"压缩"得更大。

提供两种形态：

| 形态 | 说明 | 适用场景 |
|---|---|---|
| **PicPress.exe** | 带现代深色界面的桌面应用 | 日常使用、转发给朋友 |
| **picpress-mcp** | 本地 [MCP](https://modelcontextprotocol.io) 服务（stdio） | 让 AI 智能体帮你压缩照片 |

## ✨ 特性

- 🎯 **精确目标体积** — 输入数字后选择 `B`、`KB` 或 `MB`，也有一键预设
- 🚫 **只做压缩** — 目标 ≥ 原图体积时给出明确警示，不产出虚假结果
- 🔍 **诚实的极限** — 目标实在达不到时，报告"最小可达体积"供你决策
- 🧠 **智能编码** — 二分搜索 JPEG/WebP/PNG 质量（必要时可选轻微降分辨率），以最高画质压进目标
- 🈶 **界面中英切换** — 一键切换 English / 简体中文，窗口原地重建，文件列表与设置全部保留
- 🏷 **命名不撞车** — 输出文件名自带目标体积（`photo_500KB.jpg`、`photo_1MB.jpg`），
  重名时自动追加 `(2)`，同一张图压 100KB 和 200KB 到同一目录也不会互相覆盖
- 🖼 **格式精确控制** — JPG（`.jpg`）、JPEG（`.jpeg`）、PNG、WebP，或自动（含透明通道时选 WebP）
- 🔒 **隐私友好** — 默认清除 EXIF（GPS、机型等），需要时可保留
- 📦 **批量处理** — 整个文件夹拖进来，统一压到同一目标
- 🤖 **MCP 服务** — 5 个工具供智能体调用：`compress_image`、`batch_compress`、`estimate_target`、`image_info_tool`、`supported_formats`
- 🪟 **便携 exe** — Windows 单文件，免安装、免 Python 环境

## 📸 界面

![PicPress 界面](docs/assets/screenshot.png)

<details>
<summary>英文界面</summary>

![PicPress English UI](docs/assets/screenshot-en.png)

</details>

<details>
<summary>警示弹窗（浅底深字）</summary>

![PicPress 警示弹窗](docs/assets/screenshot-dialog.png)

</details>

## 🚀 快速开始（桌面版）

1. 从 [Releases](../../releases) 页面下载 `PicPress.exe`
2. 双击运行，无需安装
3. 拖入照片（或点击 **Add files** / **Add folder**），设置目标体积，点 **Compress**

> Windows SmartScreen 可能提示未签名——点"更多信息 → 仍要运行"即可。
> 源码可自行复现构建（见下文）。

### 从源码运行

```bash
git clone https://github.com/your-name/picpress.git
cd picpress
pip install -e ".[all]"        # 核心 + GUI + MCP
python -m picpress             # 启动桌面应用
```

## 🤖 MCP 服务（供 AI 智能体使用）

PicPress 可作为本地 [MCP](https://modelcontextprotocol.io) 服务通过 stdio 运行，
智能体即可在你的电脑上按精确体积要求压缩照片。

### 方式 A — 使用独立 exe

```json
{
  "mcpServers": {
    "picpress": {
      "command": "C:\\path\\to\\picpress-mcp.exe",
      "args": []
    }
  }
}
```

### 方式 B — 从源码运行

```json
{
  "mcpServers": {
    "picpress": {
      "command": "python",
      "args": ["-m", "picpress.mcp_server"],
      "env": { "PYTHONPATH": "C:\\path\\to\\picpress\\src" }
    }
  }
}
```

把配置粘贴到对应客户端的 MCP 配置文件（如 Claude Desktop 的
`claude_desktop_config.json`、Cursor 的 `.cursor/mcp.json`、
WorkBuddy 的 `~/.workbuddy/mcp.json`）。

### 工具一览

| 工具 | 用途 |
|---|---|
| `compress_image` | 压缩单张图片到目标体积 |
| `batch_compress` | 批量压缩到同一目标 |
| `estimate_target` | 压缩前预判目标是否可行 |
| `image_info_tool` | 查询尺寸 / 格式 / 体积 |
| `supported_formats` | 列出支持的输入输出与单位 |

返回均为结构化 JSON，`status` 字段取值：
`ok` · `target_too_large` · `unreachable` · `error`。

## 🧪 如何测试 MCP 端

> **为什么双击 `picpress-mcp.exe` 没反应？**
> 它是 stdio 服务而不是图形程序：启动后就安静等待客户端通过 stdin/stdout
> 发 JSON-RPC 消息。"没反应"是正常现象。

三种验证方式：

**1. 内置自检（不需要客户端，也不需要 Python）**

```bat
picpress-mcp.exe --selftest
```

依次做 6 项检查（造样例图、列格式、读信息、预估、压缩、护栏），最后给出报告：

```
[1/6] sample photo .......... ...\sample_photo.jpg  (2.08 MB)
[5/6] compress_image ........ OK  2.08 MB -> 529.3 KB (-75.2%), target 533.0 KB met
[6/6] guard (target 50 MB) .. target_too_large (correctly refused)
RESULT: 6/6 checks passed  —  the MCP server is healthy.
```

Windows 上也可以直接双击 exe 旁边的 `MCP-自检.bat`。

**2. 协议级测试客户端（走真实 MCP 协议）**

```bash
python scripts/test_mcp.py            # 测试 dist/picpress-mcp.exe
python scripts/test_mcp.py --python   # 测试源码
```

会完成握手、列出工具、逐个调用，并逐项打印 `PASS`/`FAIL`，失败时返回非零退出码。

**3. 接真实 Agent**

把服务写进客户端的 MCP 配置，重启/信任后对 Agent 说
"把 D:\photos\a.jpg 压到 300KB"，即可在客户端的工具调用日志里看到
`compress_image` 的调用。

## 📖 工作原理

1. 目标体积（如 `500 KB`）换算为字节
2. **护栏：** 若目标 ≥ 原文件体积 → `target_too_large`，不写任何文件
3. 二分搜索编码质量，取"能装下的最高质量"
4. 若仅调质量达不到目标且允许降分辨率，搜索"最小幅度"的缩放
5. 仍达不到 → `unreachable`，并报告最小可达体积

你得到的永远是预算内最好看的文件——不会变大，也不会偷偷乱来。

## 🛠 自行构建 exe

```bash
pip install -e ".[dev]"
python scripts/build.py                # → dist/PicPress.exe、dist/picpress-mcp.exe
python scripts/build.py all --onedir   # → dist/PicPress/PicPress.exe（不解包到 %TEMP%）
```

两种模式结束前都会自动做冒烟测试（启动 GUI、与 MCP 握手），并清理测试产生的临时目录。

## 🖥 运行要求

- **现成 exe**：Windows 10 / 11（x64）。无需管理员权限、无需 Python、无需安装任何运行库。
- **从源码运行**：Python 3.10+（推荐 3.12 / 3.13），执行 `pip install -e ".[all]"`。
- **macOS / Linux**：压缩引擎与 MCP 服务是纯 Python，跨平台可用；界面可从源码运行。
  预编译的 exe 目前只提供 Windows 版。

## 🔒 隐私与磁盘足迹

PicPress 在数据方面很"无聊"，这是故意的：

- **完全离线。** 无遥测、无统计、无更新检查。唯一可能联网的动作是你主动点标题栏的
  GitHub 按钮（会打开浏览器）。
- **不写注册表。** 没有安装程序、没有右键菜单扩展、没有文件关联、没有开机自启、
  没有后台服务。**删掉 exe 就等于卸载干净。**
- **绝不动原图。** 永远另写新文件。
- **临时文件：** 单文件版（`--onefile`）启动时会把运行库解包到 `%TEMP%\_MEI*`
  （约 134 MB），正常关闭窗口时会自动删除。如果是**强制结束进程**或断电，
  这个目录可能残留——它是纯临时数据，删掉即可（Windows「磁盘清理 → 临时文件」也会清）。
  便携文件夹版（`--onedir`）**不做任何解包**。

崩溃后清理残留（只删 PyInstaller 自己的临时目录，不会动整个 `%TEMP%`）：

```bat
for /d %d in ("%TEMP%\_MEI*") do @rmdir /s /q "%d"
```

### 卸载

1. 删除 `PicPress.exe`（用过 MCP 的话再删 `picpress-mcp.exe`）
2. 可选：从 MCP 客户端配置里移除 `picpress` 条目
3. 没有第 3 步——无注册表键、无 AppData 目录

## ❓ 常见问题

**打开时提示"Windows 已保护你的电脑"？**
exe 没有代码签名（证书要花钱）。点「更多信息」→「仍要运行」即可；
随着下载量增加，这个提示会逐渐消失。

**为什么目标体积不能大于原图？**
因为那不叫压缩。PicPress 会直接拒绝并说明原因，而不是写一个"假装压缩过"的更大文件。

**目标定得太小、压不下去怎么办？**
PicPress 会告诉你它实际能做到的最小体积，建议改大目标或勾选「允许降低分辨率」。

**会覆盖我的文件吗？**
不会。输出命名是 `<原名>_<目标>.<扩展名>`，重名自动加 ` (2)`、` (3)`，原图始终保留。

**为什么 exe 有 55 MB？**
里面打包了 Python、Qt 图形库和 Pillow，所以对方电脑什么都不用装。
便携文件夹版体积相同但启动更快。

**能批量压一个文件夹吗？**
可以——点「添加文件夹」或直接把文件夹拖进窗口，统一压到同一目标。

## 📤 分享给别人

- **最省事：** 直接发 `PicPress.exe`，对方双击就能用——免安装、免 Python
  （记得提醒上文的 SmartScreen 提示）。
- **最正规：** 发布 GitHub Release，把
  `https://github.com/<你>/picpress/releases/latest` 发给对方。
- **给会用 Agent 的朋友：** 发 `picpress-mcp.exe`，再把上面的 MCP 配置片段给他，
  粘贴进客户端、重启、信任即可。不确定是否连通，先跑 `picpress-mcp.exe --selftest`。

维护者发布新版本的操作步骤见 [docs/RELEASING.md](docs/RELEASING.md)。

## 🧩 路线图

- [ ] 按宽度缩放助手
- [ ] 压缩历史 / 撤销
- [ ] CI 产出 macOS / Linux 构建
- [ ] 界面中英切换

## 🤝 参与贡献

欢迎提 Issue 和 PR。请保持核心引擎（`src/picpress/core.py`）与 UI 解耦——
桌面版与 MCP 服务都依赖它。

```bash
python tests/test_core.py        # 引擎单元测试（19 个）
python tests/test_mcp_server.py  # MCP 协议测试（5 个）
python tests/test_gui_smoke.py   # GUI 冒烟测试（4 个，需桌面环境）
```

## 📄 许可证

[MIT](LICENSE) — 个人与商业使用均免费。

---

*PicPress 只做压缩。目标比原图还大？那不是压缩——PicPress 会如实告诉你。*
