# Releasing & sharing PicPress / 发布与分享

面向仓库维护者的操作手册。分三步：**一次性准备 → 打包 → 发布/分享**。

---

## 0. 一次性准备（One-time setup）

### 0.1 把占位地址换成你的仓库

代码和文档里目前用的是占位地址 `your-name/picpress`。一条命令全部替换：

```bash
python scripts/set_repo.py <你的GitHub用户名>/picpress
# 例：python scripts/set_repo.py xiaoqiang/picpress
```

它会改这 4 处：`README.md`、`README.zh-CN.md`、`pyproject.toml`、`src/picpress/gui.py`（应用内 GitHub 按钮）。
改完记得重新打包（地址被编译进 exe）。

### 0.2 关联远程仓库并推送

```bash
git remote add origin https://github.com/<你>/picpress.git
git push -u origin main
```

### 0.3 在 GitHub 仓库页面填写元信息（很重要，影响别人能不能找到）

- **Description**：`Compress photos to an exact target size (B/KB/MB) — desktop app + MCP server for AI agents`
- **Topics**：`image-compression` `photo` `jpeg` `webp` `mcp` `mcp-server` `pyside6` `windows` `desktop-app` `python`
- **Website**：留空或填 Releases 链接
- 勾选 Issues（让别人能反馈问题）

---

## 1. 打包（Build）

```bash
pip install -e ".[dev]"

python scripts/build.py                # 单文件：dist/PicPress.exe + dist/picpress-mcp.exe
python scripts/build.py all --onedir   # 便携文件夹：dist/PicPress/ 与 dist/picpress-mcp/
```

两种形态的区别：

| | 单文件 `--onefile` | 便携文件夹 `--onedir` |
|---|---|---|
| 分享方式 | 直接发一个 exe | 把整个文件夹压成 zip 发 |
| 启动速度 | 每次先解包，慢 2–4 秒 | 立即启动 |
| 临时文件 | 每次启动解包约 134 MB 到 `%TEMP%`，正常退出自动删除 | **不写任何临时文件** |
| 适合 | 随手转发 | 长期使用、在意磁盘痕迹 |

`scripts/build.py` 自带冒烟测试：启动 GUI 检查存活、对 MCP 做一次真实握手，并清理测试产生的临时解包目录。

---

## 2. 发布（GitHub Release）

仓库里的 `.github/workflows/build.yml` 已经配好：**推 tag 即自动构建并发布 Release**。

```bash
# 1) 改版本号（3 个地方 + 更新 CHANGELOG）
#    src/picpress/__init__.py  __version__
#    pyproject.toml            version
#    src/picpress/gui.py       APP_VERSION
# 2) 提交
git commit -am "chore: release v0.2.0"
# 3) 打 tag 并推送（tag 必须以 v 开头，workflow 靠这个触发）
git tag v0.2.0
git push origin main --tags
```

Actions 会依次跑：单元测试 → MCP 协议测试 → GUI 冒烟测试 → 打包 → 创建 Release 并附上两个 exe。

> 首次发布后，把 README 里的 `../../releases/latest` 链接检查一遍即可。

### 手动发布（不走 Actions）

GitHub 页面 → **Releases → Draft a new release** → 选 tag → 上传 `dist/PicPress.exe` 与 `dist/picpress-mcp.exe` → 发布。

建议同时附上 SHA256，方便别人校验：

```powershell
Get-FileHash dist\PicPress.exe -Algorithm SHA256
Get-FileHash dist\picpress-mcp.exe -Algorithm SHA256
```

---

## 3. 分享给别人（Sharing）

### 方式 A：直接发文件（最省事）

- 发 `PicPress.exe` 即可，对方**不需要装 Python、不需要装任何东西**，双击就用。
- 微信/QQ 传大文件没问题；邮箱一般限 25 MB，建议改用网盘或 Release 链接。

⚠️ **对方第一次打开可能被 SmartScreen 拦**（因为 exe 没有代码签名证书）。告诉对方：点「更多信息」→「仍要运行」。要彻底消除这个提示只能买代码签名证书（一年几百到几千元），对个人项目通常没必要。

### 方式 B：发 Release 链接（最推荐）

发 `https://github.com/<你>/picpress/releases/latest` 一条链接，对方自己下载，还能看到更新日志。

### 方式 C：分享 MCP 端给会用 Agent 的朋友

1. 发 `picpress-mcp.exe`
2. 让对方在自己的 MCP 配置里加一段（位置见 README）：

```json
{
  "mcpServers": {
    "picpress": {
      "command": "C:\\你放的路径\\picpress-mcp.exe",
      "args": []
    }
  }
}
```

3. 提醒对方重启客户端并「信任」该服务；不确定是否好用，先双击跑 `picpress-mcp.exe --selftest`。

---

## 4. 发布前检查清单

- [ ] `python scripts/set_repo.py <owner>/<repo>` 已执行（README / pyproject / gui 里无 `your-name`）
- [ ] 版本号三处一致（`__init__.py` / `pyproject.toml` / `gui.py`）
- [ ] `CHANGELOG.md` 已更新
- [ ] 四个测试文件全绿：`test_core.py`、`test_mcp_server.py`、`test_gui_smoke.py`
- [ ] 重新打包并实际双击跑一次（语言切换、格式、命名各点一遍）
- [ ] Release 说明里写清「Windows 10/11 x64」与 SmartScreen 提示
- [ ] 仓库 Description / Topics 已填
