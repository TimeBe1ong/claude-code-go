# Claude Code Go

🚀 跨平台 Claude Code CLI 启动器 · 支持多 API Key 切换与本地用量统计

## 功能

- 🖥️ **跨平台**：自动检测 Windows / macOS / Linux，使用对应终端和环境变量
- 🔌 **8 个 API 预设**：DeepSeek / Anthropic / GLM / Kimi / Qwen / 百度千帆 / OpenAI
- 🔑 **多 Key 管理**：每个预设可存多个 API Key，下拉选择，打码隐藏，加密存储
- 📝 **模型记忆**：每个预设独立记住模型名，改一次永久生效
- 📊 **用量统计**：本地解析 Claude Code 的 JSONL 会话文件，展示 Token 消耗
- 📦 **脚本导出**：一键生成 `DeepSeekGo.bat` / `GLMGo.sh` 独立启动脚本
- 🔒 **安全存储**：API Key base64 编码存储，不暴露明文

## 界面预览

```
┌─ Claude Code Go ──────────────── [📖 安装准备说明] ─┐
│                                                       │
│  ┌─ 操作系统 ─────────────────────────────────────┐   │
│  │ 🪟 Windows (PowerShell)                        │   │
│  └────────────────────────────────────────────────┘   │
│  ┌─ 工作目录 ─────────────────────────────────────┐   │
│  │ [C:\DeepSleep                    ] [📁 选择]   │   │
│  └────────────────────────────────────────────────┘   │
│  ┌─ API 配置 ─────────────────────────────────────┐   │
│  │ API 预设: [DeepSeek ▼]                         │   │
│  └────────────────────────────────────────────────┘   │
│  ┌─ API Key ──────────────────────────────────────┐   │
│  │ [sk-bacd****48d8                    ▼]         │   │
│  └────────────────────────────────────────────────┘   │
│  ┌─ 默认模型 ─────────────────────────────────────┐   │
│  │ [deepseek-v4-pro[1m]                         ] │   │
│  └────────────────────────────────────────────────┘   │
│                                                       │
│  [📊 用量统计]              [💾 保存] [🔄 重置]       │
│                                                       │
│  [          🚀 启动 Claude Code          ]            │
│              [📦 输出 DeepSeek Go]                     │
└───────────────────────────────────────────────────────┘
```

## 快速开始

### 前提条件

1. **Node.js 18+** — [下载](https://nodejs.org)
2. **Git for Windows**（仅 Windows）— [下载](https://git-scm.com)
3. **Claude Code**：
   ```bash
   npm install -g @anthropic-ai/claude-code
   claude --version  # 验证安装
   ```

### 使用

1. 下载 [Releases](https://github.com/TimeBe1ong/claude-code-go/releases) 中的 `Claude-Code-Go.exe`
2. 双击运行
3. 选择 API 预设，填入 Key，配置模型
4. 点击 🚀 启动

### 从源码运行

```bash
git clone https://github.com/TimeBe1ong/claude-code-go.git
cd claude-code-go
python claude_launcher.py
```

### 打包 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Claude-Code-Go" claude_launcher.py
```
EXE 在 `dist/` 目录。

### 输出启动脚本

配置好 API Key、模型后，点击 **📦 输出 {预设名} Go**，会生成一个独立的启动脚本：

- Windows → `DeepSeekGo.bat`（双击打开 PowerShell，自动设环境变量，启动 Claude）
- macOS / Linux → `DeepSeekGo.sh`（终端执行，自动 export + 启动）

**这个脚本已经保存了你的配置，可以发给别人或放在任何地方单独使用，不需要再打开启动器。**

## 技术栈

- Python 3.8+
- tkinter（标准库 GUI）
- base64（Key 编码）
- threading（用量统计后台扫描）
- PyInstaller（打包）
## 免责协议
- 声明用途：明确本项目仅供技术学习和研究使用。
- 提示风险：告知用户使用本项目可能违反Anthropic的用户协议，使用前需仔细阅读相关服务条款。
- 责任划分：声明使用本项目的一切风险由用户自行承担，作者不对因使用本项目导致的账户封禁、服务中断或其他任何损失承担责任。
- 默认接受条款：说明用户一旦使用或修改本程序，即视为完全接受本免责协议的所有条款。
## 许可证

MIT License
