# PicPress

**把照片压缩到你指定的体积。**
Compress photos to the exact size you choose — 精确到 B / KB / MB。

[English](README.md) · [简体中文](README.zh-CN.md)

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
python scripts/build.py
# → dist/PicPress.exe、dist/picpress-mcp.exe
```

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
