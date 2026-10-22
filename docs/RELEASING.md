# Releasing & sharing PicPress / 发布与分享

面向仓库维护者的操作手册。分三步：**一次性准备 → 打包 → 发布/分享**。

---

## 0. 一次性准备（One-time setup）

### 0.1 把占位地址换成你的仓库

仓库地址已写入本项目（`xiaoqiangzaici/picpress`）。若你 fork 或改名，一条命令全部替换：

```bash
python scripts/set_repo.py <你的GitHub用户名>/picpress
# 例：python scripts/set_repo.py xiaoqiangzaici/picpress
```

它会改这 4 处：`README.md`、`README.zh-CN.md`、`pyproject.toml`、`src/picpress/gui.py`（应用内 GitHub 按钮）。
改完记得重新打包（地址被编译进 exe）。

### 0.2 关联远程仓库并推送

```bash
git remote add origin https://github.com/<你>/picpress.git
git push -u origin main
```

> 首次推送整包代码也可以直接用 `python scripts/publish_github.py`（见 2.3），
> 它会通过 GitHub API 建仓库并提交，不需要 `github.com` 的直连。

### 0.3 在 GitHub 仓库页面填写元信息（很重要，影响别人能不能找到）

- **Description**：`Compress photos to an exact target size (B/KB/MB) — desktop app + MCP server for AI agents`
- **Topics**：`image-compression` `photo` `jpeg` `webp` `mcp` `mcp-server` `pyside6` `windows` `desktop-app` `python`
- 勾选 Issues（让别人能反馈问题）

---

## 1. 打包（Build）

```bash
pip install -e ".[dev]"

python scripts/build.py     # 便携文件夹：dist/PicPress/ 与 dist/picpress-mcp/
python scripts/package.py   # 压成两个 zip + 生成 SHA256SUMS.txt
```

产物：

| 文件 | 说明 |
|---|---|
| `dist/PicPress-portable.zip` | 桌面应用，约 55 MB（解压后 138 MB） |
| `dist/picpress-mcp-portable.zip` | MCP 服务，约 37 MB（解压后 85 MB） |
| `dist/SHA256SUMS.txt` | 供下载者校验 |

**为什么只发文件夹版？** 单文件版每次启动都要把约 134 MB 解包到 `%TEMP%`，
被强杀时会残留；文件夹版启动即用、除自身目录外不写任何东西。单文件只是可选开发模式：
`python scripts/build.py --onefile`。

`scripts/build.py` 自带冒烟测试：启动 GUI 检查存活、对 MCP 做一次真实握手，并清理测试产生的临时解包目录。

---

## 2. 发布（GitHub Release）

### 2.1 自动发布（推荐）

仓库里的 `.github/workflows/build.yml` 已经配好：**推 tag 即自动构建、打 zip、生成校验文件并发布 Release**。

```bash
# 1) 改版本号（3 处 + 更新 CHANGELOG）
#    src/picpress/__init__.py  __version__
#    pyproject.toml            version
#    src/picpress/gui.py       APP_VERSION
git commit -am "chore: release v0.3.0"
git tag v0.3.0
git push origin main --tags
```

Actions 会依次跑：单元测试 → MCP 协议测试 → GUI 冒烟测试 → 打包 → 创建 Release 并附上两个 zip。

### 2.2 手动发布（不走 Actions）

GitHub 页面 → **Releases → Draft a new release** → 选 tag → 上传
`dist/PicPress-portable.zip`、`dist/picpress-mcp-portable.zip`、`dist/SHA256SUMS.txt` → 发布。

### 2.3 网络连不上 github.com 时（用 API 发布）

有些网络下 `github.com` 不通、但 `api.github.com` 正常。此时可用仓库自带的脚本，
通过 GitHub REST API 建仓库并推送代码（无需 git 直连）：

```bash
# 1) 准备一个 Personal Access Token（classic，勾选 repo + workflow）
#    https://github.com/settings/tokens
# 2) 发布（token 只从环境变量读取，不会写进任何文件）
set GITHUB_TOKEN=ghp_xxx
python scripts/publish_github.py xiaoqiang/picpress
```

脚本会：创建仓库（若不存在）→ 写入 Description/Topics → 逐个文件提交到 `main`。
**Release 附件仍需在网页上手动上传**（zip 太大，走网页最稳）。

> 用完建议到 GitHub 设置里撤销该 token，或改用有效期很短的 fine-grained token。

---

## 3. 分享给别人（Sharing）

### 方式 A：直接发文件（最省事）

- 发 `PicPress-portable.zip`，对方解压后双击 `PicPress.exe` 即可。
  **不需要装 Python、不需要装任何东西**，删掉文件夹就等于卸载。
- 微信/QQ 传大文件没问题；邮箱一般限 25 MB，建议改用网盘或 Release 链接。

⚠️ **对方第一次打开可能被 SmartScreen 拦**（exe 没有代码签名）。让对方点「更多信息」→「仍要运行」。
要彻底消除只能买代码签名证书（一年几百到几千元），个人项目通常没必要。

### 方式 B：发 Release 链接（最推荐）

发 `https://github.com/<你>/picpress/releases/latest` 一条链接，对方自己下载，还能看到更新日志。

### 方式 C：分享 MCP 端给会用 Agent 的朋友

1. 发 `picpress-mcp-portable.zip`
2. 让对方解压后，在自己的 MCP 配置里加一段（位置见 README）：

```json
{
  "mcpServers": {
    "picpress": {
      "command": "C:\\你解压的路径\\picpress-mcp\\picpress-mcp.exe",
      "args": []
    }
  }
}
```

3. 提醒对方重启客户端并「信任」该服务；不确定是否好用，先在命令行跑
   `picpress-mcp.exe --selftest`（6 项自检）。

---

## 4. 发布前检查清单

- [ ] `python scripts/set_repo.py <owner>/<repo>` 已执行（README / pyproject / gui 里无 `your-name`）
- [ ] 版本号三处一致（`__init__.py` / `pyproject.toml` / `gui.py`）
- [ ] `CHANGELOG.md` 已更新
- [ ] 三个测试文件全绿：`test_core.py`、`test_mcp_server.py`、`test_gui_smoke.py`
- [ ] 重新打包并实际解压跑一次（语言切换、格式、命名各点一遍）
- [ ] Release 说明里写清「Windows 10/11 x64」与 SmartScreen 提示
- [ ] 仓库 Description / Topics 已填
