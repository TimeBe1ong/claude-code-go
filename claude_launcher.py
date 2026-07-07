"""
Claude Code Go - DeepSeek 启动器
跨平台 GUI 工具 (Windows / macOS / Linux)
"""
import base64
import glob
import json
import os
import platform
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

def _get_config_dir():
    """配置文件存到系统数据目录，不污染桌面"""
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif platform.system() == "Darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    path = os.path.join(base, "Claude-Code-Go")
    os.makedirs(path, exist_ok=True)
    return path

CONFIG_DIR = _get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ── API Key 简单编码 ─────────────────────────────────
def _encode_key(key):
    return base64.b64encode(key.encode()).decode()

def _decode_key(encoded):
    try:
        return base64.b64decode(encoded.encode()).decode()
    except Exception:
        return encoded  # 兼容旧明文

# ── 默认配置 ──────────────────────────────────────────
API_PRESETS = {
    "DeepSeek":       ("https://api.deepseek.com/anthropic",                  "deepseek-v4-pro[1m]"),
    "Anthropic":      ("https://api.anthropic.com",                           "claude-sonnet-5"),
    "智谱 GLM":       ("https://open.bigmodel.cn/api/paas/v4/anthropic",      "glm-4"),
    "月之暗面 Kimi":  ("https://api.moonshot.cn/anthropic",                   "moonshot-v1"),
    "阿里百炼 Qwen":  ("https://dashscope.aliyuncs.com/compatible-mode/anthropic", "qwen-max"),
    "百度千帆":       ("https://qianfan.baidubce.com/v2/anthropic",           "ernie-4.0"),
    "OpenAI":         ("https://api.openai.com/v1",                           "gpt-4o"),
    "自定义":         ("", ""),
}

DEFAULT_CONFIG = {
    "work_dir": "C:\\DeepSleep" if os.name == "nt" else os.path.expanduser("~"),
    "api_preset": "DeepSeek",
    "api_base_url": "https://api.deepseek.com/anthropic",
    "api_tokens": {},
    "api_models": {},
    "os_type": "",
}

# ── 平台相关 ──────────────────────────────────────────
def detect_os():
    system = platform.system()
    if system == "Windows":
        return "Windows"
    elif system == "Darwin":
        return "macOS"
    else:
        return "Linux"

OS_TYPE = detect_os()

def get_os_label(os_type):
    return {"Windows": "🪟 Windows (PowerShell)", "macOS": "🍎 macOS (Terminal)", "Linux": "🐧 Linux (Terminal)"}.get(os_type, os_type)

# ── 配置读写 ──────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            saved = {}
    else:
        saved = {}

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(saved)
    # 解密 api_tokens
    if "api_tokens" in cfg:
        decoded = {}
        for k, v in cfg["api_tokens"].items():
            if isinstance(v, str):
                v = [v]
            decoded[k] = [_decode_key(t) for t in v]
        cfg["api_tokens"] = decoded
    # 兼容旧版单个 api_auth_token
    if "api_auth_token" in cfg and cfg["api_auth_token"]:
        old_token = cfg.pop("api_auth_token")
        if not cfg.get("api_tokens"):
            cfg["api_tokens"] = {}
        if "DeepSeek" not in cfg["api_tokens"]:
            cfg["api_tokens"]["DeepSeek"] = [_decode_key(old_token)]
    if not cfg.get("os_type"):
        cfg["os_type"] = OS_TYPE
        save_config(cfg)
    return cfg

def save_config(cfg):
    # 加密 api_tokens
    safe = cfg.copy()
    if "api_tokens" in safe:
        safe["api_tokens"] = {k: [_encode_key(t) for t in v] for k, v in safe["api_tokens"].items()}
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2, ensure_ascii=False)

# ── 辅助：子窗口居中 ──────────────────────────────────
def center_window(win, width, height):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")


# ── 用量统计 ──────────────────────────────────────────
def get_claude_data_dir():
    return os.path.join(os.path.expanduser("~"), ".claude")

def parse_usage_from_jsonl(filepath):
    """解析单个 JSONL 文件，提取所有 usage 数据"""
    records = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = obj.get("message", {})
                usage = msg.get("usage")
                if usage:
                    records.append({
                        "timestamp": obj.get("timestamp", ""),
                        "model": msg.get("model", ""),
                        "session_id": obj.get("sessionId", ""),
                        "input_tokens": usage.get("input_tokens", 0),
                        "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                        "cache_create_tokens": usage.get("cache_creation_input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                    })
    except Exception:
        pass
    return records

def get_all_usage():
    """扫描所有 JSONL 文件，汇总用量"""
    data_dir = get_claude_data_dir()
    projects_dir = os.path.join(data_dir, "projects")
    all_records = []

    if os.path.exists(projects_dir):
        for root, dirs, files in os.walk(projects_dir):
            for f in files:
                if f.endswith(".jsonl"):
                    filepath = os.path.join(root, f)
                    records = parse_usage_from_jsonl(filepath)
                    all_records.extend(records)

    all_records.sort(key=lambda r: r["timestamp"], reverse=True)
    return all_records

# ── 主窗口 ────────────────────────────────────────────
class ClaudeLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Claude Code Go")
        center_window(self.root, 560, 520)
        self.root.resizable(True, True)
        self.root.minsize(460, 420)

        self.config = load_config()
        self._build_ui()
        self._sync_ui_from_config()

    # ── UI ─────────────────────────────────────────────
    def _build_ui(self):
        self.url_var = tk.StringVar()   # Base URL，内部存储
        self.model_var = tk.StringVar() # 模型，内部存储

        main = ttk.Frame(self.root, padding="16 12 16 8")
        main.pack(fill=tk.BOTH, expand=True)

        # 标题行
        title_row = ttk.Frame(main)
        title_row.pack(fill=tk.X, pady=(0, 2))

        ttk.Label(title_row, text="Claude Code Go", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        ttk.Button(title_row, text="📖 安装准备说明", command=self._show_install_guide).pack(side=tk.RIGHT)

        ttk.Label(main, text="跨平台一键启动", foreground="#888").pack(pady=(0, 14))

        # ── 操作系统 ──
        os_frame = ttk.LabelFrame(main, text="操作系统", padding="8 6 8 6")
        os_frame.pack(fill=tk.X, pady=(0, 8))

        self.env_os_label = ttk.Label(os_frame, text="", font=("Segoe UI", 9))
        self.env_os_label.pack(anchor=tk.W)

        # ── 工作目录 ──
        dir_frame = ttk.LabelFrame(main, text="工作目录", padding="8 6 8 6")
        dir_frame.pack(fill=tk.X, pady=(0, 8))

        dir_row = ttk.Frame(dir_frame)
        dir_row.pack(fill=tk.X)

        self.dir_var = tk.StringVar()
        ttk.Entry(dir_row, textvariable=self.dir_var, font=("Consolas", 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(dir_row, text="📁 选择", command=self._browse_dir, width=6).pack(side=tk.RIGHT)

        # ── API 选择 ──
        api_frame = ttk.LabelFrame(main, text="API 配置", padding="8 6 8 6")
        api_frame.pack(fill=tk.X, pady=(0, 8))

        # 预设下拉
        preset_row = ttk.Frame(api_frame)
        preset_row.pack(fill=tk.X)

        ttk.Label(preset_row, text="API 预设:").pack(side=tk.LEFT, padx=(0, 8))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_row, textvariable=self.preset_var,
                                         values=list(API_PRESETS.keys()), state="readonly", width=20)
        self.preset_combo.pack(side=tk.LEFT)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        # ── API Key ──
        tok_frame = ttk.LabelFrame(main, text="API Key（下拉选择或输入新 Key）", padding="8 6 8 6")
        tok_frame.pack(fill=tk.X, pady=(0, 8))

        self.tok_var = tk.StringVar()
        self.tok_combo = ttk.Combobox(tok_frame, textvariable=self.tok_var, font=("Consolas", 9))
        self.tok_combo.pack(fill=tk.X)
        self._full_keys = []      # 完整 Key 列表
        self._current_full_key = "" # 当前选中的完整 Key

        # 聚焦时显示完整 Key，失焦后自动打码
        self.tok_combo.bind("<FocusIn>", self._unmask_key)
        self.tok_combo.bind("<FocusOut>", self._mask_display)
        self.tok_combo.bind("<<ComboboxSelected>>", self._on_key_selected)

        # ── 模型 ──
        model_frame = ttk.LabelFrame(main, text="默认模型", padding="8 6 8 6")
        model_frame.pack(fill=tk.X, pady=(0, 8))

        self.model_var = tk.StringVar()
        ttk.Entry(model_frame, textvariable=self.model_var, font=("Consolas", 9)).pack(fill=tk.X)

        # ── 底部按钮 ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(btn_frame, text="📊 用量统计", command=self._show_usage_stats).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="💾 保存配置", command=self._save).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_frame, text="🔄 重置默认", command=self._reset).pack(side=tk.RIGHT, padx=(6, 0))

        # 启动按钮
        launch_btn = ttk.Button(main, text="🚀 启动 Claude Code", command=self._launch)
        launch_btn.pack(fill=tk.X, pady=(10, 0))
        style = ttk.Style()
        style.configure("Large.TButton", font=("Segoe UI", 11, "bold"))
        launch_btn.configure(style="Large.TButton")

        # 输出启动脚本（按钮文字随预设动态变化）
        self.export_btn = ttk.Button(main, text="", command=self._export_dsg)
        self.export_btn.pack(anchor=tk.E, pady=(6, 0))

        # 状态栏
        self.status = ttk.Label(main, text="就绪", foreground="#888", anchor=tk.W)
        self.status.pack(fill=tk.X, pady=(6, 0))

    # ── 逻辑 ───────────────────────────────────────────
    def _sync_ui_from_config(self):
        self._update_env_labels()
        self.dir_var.set(self.config.get("work_dir", ""))
        preset = self.config.get("api_preset", "DeepSeek")
        self.preset_var.set(preset if preset in API_PRESETS else "自定义")
        self._update_export_btn()
        self.url_var.set(self.config.get("api_base_url", ""))
        # 读取该预设对应的 token 列表（打码显示）
        tokens = self.config.get("api_tokens", {})
        self._full_keys = tokens.get(preset, [])
        self._refresh_tok_dropdown()
        # 读取该预设对应的模型：用户保存的 > 预设默认
        models = self.config.get("api_models", {})
        if preset in models:
            self.model_var.set(models[preset])
        elif preset in API_PRESETS:
            _, default_model = API_PRESETS[preset]
            self.model_var.set(default_model)

    def _on_preset_selected(self, evt):
        name = self.preset_var.get()
        if name in API_PRESETS:
            url, default_model = API_PRESETS[name]
            if url:
                self.url_var.set(url)
            # 模型：用户保存的 > 预设默认
            models = self.config.get("api_models", {})
            self.model_var.set(models.get(name, default_model))
        # 切换预设：更新 Key 下拉列表（打码显示）
        tokens = self.config.get("api_tokens", {})
        self._full_keys = tokens.get(name, [])
        self._refresh_tok_dropdown()
        self._update_export_btn()

    def _update_export_btn(self):
        name = self.preset_var.get()
        self.export_btn.configure(text=f"📦 输出 {name} Go")

    def _update_env_labels(self):
        os_type = self.config.get("os_type", OS_TYPE)
        self.env_os_label.configure(text=get_os_label(os_type))

    def _show_install_guide(self):
        messagebox.showinfo("安装准备说明",
            "安装 Claude Code 前请确保:\n\n"
            "1. Node.js 18+\n"
            "   下载: https://nodejs.org\n\n"
            "2. Git for Windows (仅 Windows)\n"
            "   下载: https://git-scm.com\n\n"
            "3. 安装 Claude Code:\n"
            "   npm install -g @anthropic-ai/claude-code\n\n"
            "4. 验证安装:\n"
            "   claude --version")

    def _detect_env(self):
        detected = detect_os()
        self.config["os_type"] = detected
        save_config(self.config)
        self._update_env_labels()
        self.status.configure(text=f"✅ 检测完成: {get_os_label(detected)}")

    def _browse_dir(self):
        path = filedialog.askdirectory(title="选择工作目录")
        if path:
            self.dir_var.set(path)

    @staticmethod
    def _mask_key(key):
        """sk-abc123...xyz9 → sk-abc****xyz9"""
        if len(key) <= 12:
            return key[:4] + "****" if len(key) > 8 else key
        return key[:6] + "****" + key[-4:]

    def _is_masked(self, text):
        return "****" in text

    def _unmask_key(self, evt=None):
        """聚焦时显示完整 Key"""
        if self._is_masked(self.tok_var.get()):
            self.tok_var.set(self._current_full_key)

    def _mask_display(self, evt=None):
        """失焦后打码，新 Key 自动保存"""
        current = self.tok_var.get().strip()
        if current and not self._is_masked(current):
            self._current_full_key = current
            # 新 Key 加入列表
            if current not in self._full_keys:
                preset = self.preset_var.get()
                if "api_tokens" not in self.config:
                    self.config["api_tokens"] = {}
                keys = self.config["api_tokens"].get(preset, [])
                if current in keys:
                    keys.remove(current)
                keys.insert(0, current)
                self.config["api_tokens"][preset] = keys
                self._full_keys = keys
            self._refresh_tok_dropdown()
        else:
            # 已是打码状态或无内容，刷新下拉
            current_full = self._current_full_key
            self._refresh_tok_dropdown()
            if current_full in self._full_keys:
                self._current_full_key = current_full
                idx = self._full_keys.index(current_full)
                masked = [self._mask_key(k) for k in self._full_keys]
                self.tok_var.set(masked[idx])

    def _on_key_selected(self, evt=None):
        """下拉选中：显示完整 Key"""
        selected = self.tok_var.get()
        if self._is_masked(selected):
            for k in self._full_keys:
                if self._mask_key(k) == selected:
                    self._current_full_key = k
                    self.tok_var.set(k)
                    break

    def _refresh_tok_dropdown(self):
        """刷新 Key 下拉列表（打码显示）"""
        masked = [self._mask_key(k) for k in self._full_keys]
        self.tok_combo["values"] = masked
        if self._full_keys:
            self._current_full_key = self._full_keys[0]
            self.tok_var.set(masked[0])
        else:
            self._current_full_key = ""
            self.tok_var.set("")

    def _save(self):
        self.config["work_dir"] = self.dir_var.get()
        self.config["api_preset"] = self.preset_var.get()
        self.config["api_base_url"] = self.url_var.get()
        # 保存模型到对应预设名下
        preset = self.preset_var.get()
        model = self.model_var.get().strip()
        if "api_models" not in self.config:
            self.config["api_models"] = {}
        if model:
            self.config["api_models"][preset] = model
        elif preset in self.config["api_models"]:
            del self.config["api_models"][preset]
        save_config(self.config)
        self.status.configure(text="✅ 配置已保存")

    def _reset(self):
        self.config = DEFAULT_CONFIG.copy()
        self.config["os_type"] = detect_os()
        save_config(self.config)
        self._sync_ui_from_config()
        self.status.configure(text="已恢复默认配置")

    # ── 启动 ───────────────────────────────────────────
    def _launch(self):
        self._save()

        api_url = self.url_var.get().strip()
        api_token = self._current_full_key

        if not api_token:
            messagebox.showwarning("提示", "请先填写 API Key")
            return

        work_dir = self.dir_var.get().strip() or os.path.expanduser("~")
        model = self.model_var.get().strip()
        os_type = self.config.get("os_type", OS_TYPE)

        if os_type == "Windows":
            self._launch_windows(work_dir, api_url, api_token, model)
        elif os_type == "macOS":
            self._launch_mac(work_dir, api_url, api_token, model)
        else:
            self._launch_linux(work_dir, api_url, api_token, model)

    def _launch_windows(self, work_dir, api_url, api_token, model):
        env_vars = (
            f"$env:ANTHROPIC_BASE_URL='{api_url}'; "
            f"$env:ANTHROPIC_AUTH_TOKEN='{api_token}'; "
            f"$env:ANTHROPIC_MODEL='{model}'; "
            f"$env:ANTHROPIC_DEFAULT_OPUS_MODEL='{model}'; "
            f"$env:ANTHROPIC_DEFAULT_SONNET_MODEL='{model}'; "
            f"$env:ANTHROPIC_DEFAULT_HAIKU_MODEL='deepseek-v4-flash'; "
            f"$env:CLAUDE_CODE_SUBAGENT_MODEL='deepseek-v4-flash'; "
            f"$env:CLAUDE_CODE_SHOW_COST='true'"
        )
        cmd = f"Set-Location '{work_dir}'; {env_vars}; claude.cmd"

        try:
            subprocess.Popen(["powershell.exe", "-NoExit", "-Command", cmd], cwd=work_dir)
            self.status.configure(text="✅ Claude Code 已启动！")
        except Exception as e:
            messagebox.showerror("启动失败", str(e))
            self.status.configure(text="❌ 启动失败")

    def _launch_mac(self, work_dir, api_url, api_token, model):
        exports = (
            f"export ANTHROPIC_BASE_URL='{api_url}'; "
            f"export ANTHROPIC_AUTH_TOKEN='{api_token}'; "
            f"export ANTHROPIC_MODEL='{model}'; "
            f"export ANTHROPIC_DEFAULT_OPUS_MODEL='{model}'; "
            f"export ANTHROPIC_DEFAULT_SONNET_MODEL='{model}'; "
            f"export ANTHROPIC_DEFAULT_HAIKU_MODEL='deepseek-v4-flash'; "
            f"export CLAUDE_CODE_SUBAGENT_MODEL='deepseek-v4-flash'; "
            f"export CLAUDE_CODE_SHOW_COST='true'"
        )
        cmd = f'cd "{work_dir}"; {exports}; claude'

        try:
            subprocess.Popen(["osascript", "-e",
                f'tell application "Terminal" to do script "{cmd}"'])
            self.status.configure(text="✅ Claude Code 已启动！")
        except Exception as e:
            messagebox.showerror("启动失败", str(e))
            self.status.configure(text="❌ 启动失败")

    def _launch_linux(self, work_dir, api_url, api_token, model):
        exports = (
            f"export ANTHROPIC_BASE_URL='{api_url}'; "
            f"export ANTHROPIC_AUTH_TOKEN='{api_token}'; "
            f"export ANTHROPIC_MODEL='{model}'; "
            f"export ANTHROPIC_DEFAULT_OPUS_MODEL='{model}'; "
            f"export ANTHROPIC_DEFAULT_SONNET_MODEL='{model}'; "
            f"export ANTHROPIC_DEFAULT_HAIKU_MODEL='deepseek-v4-flash'; "
            f"export CLAUDE_CODE_SUBAGENT_MODEL='deepseek-v4-flash'; "
            f"export CLAUDE_CODE_SHOW_COST='true'"
        )
        cmd = f'cd "{work_dir}"; {exports}; claude'

        terminals = [
            ["gnome-terminal", "--", "bash", "-c", f"{cmd}; exec bash"],
            ["konsole", "-e", "bash", "-c", f"{cmd}; exec bash"],
            ["xfce4-terminal", "-e", f"bash -c '{cmd}; exec bash'"],
            ["x-terminal-emulator", "-e", f"bash -c '{cmd}; exec bash'"],
            ["xterm", "-e", f"bash -c '{cmd}; exec bash'"],
        ]

        for term_cmd in terminals:
            try:
                subprocess.Popen(term_cmd, cwd=work_dir)
                self.status.configure(text="✅ Claude Code 已启动！")
                return
            except FileNotFoundError:
                continue

        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        messagebox.showinfo("提示",
            "未找到可用的终端模拟器。\n\n启动命令已复制到剪贴板，请手动粘贴到终端执行。")
        self.status.configure(text="⚠️ 命令已复制到剪贴板")

    def _show_usage_stats(self):
        """显示用量统计窗口（后台扫描，不卡 UI）"""
        # 先弹出窗口，显示加载中
        win = tk.Toplevel(self.root)
        win.title("用量统计")
        win.geometry("580x500")
        win.resizable(True, True)
        win.transient(self.root)
        center_window(win, 580, 500)

        main = ttk.Frame(win, padding="12 10 12 8")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="📊 Token 用量统计", font=("Segoe UI", 14, "bold")).pack(pady=(0, 2))
        loading_label = ttk.Label(main, text="正在扫描用量数据...", foreground="#888")
        loading_label.pack(pady=20)
        progress = ttk.Progressbar(main, mode="indeterminate")
        progress.pack(fill=tk.X, padx=60)
        progress.start()

        def _scan_and_show():
            records = get_all_usage()
            # 回到主线程更新 UI
            win.after(0, lambda: self._build_stats_window(win, main, records))

        threading.Thread(target=_scan_and_show, daemon=True).start()

    def _build_stats_window(self, win, main, records):
        """在主线程构建统计窗口内容"""
        # 清掉加载提示
        for w in main.winfo_children():
            w.destroy()

        if not records:
            ttk.Label(main, text="暂无用量数据", foreground="#888").pack(pady=30)
            ttk.Label(main, text="开始使用 Claude Code 后这里会显示统计。").pack()
            ttk.Button(main, text="关闭", command=win.destroy).pack(pady=(12, 0))
            return

        # 汇总
        total_in = sum(r["input_tokens"] for r in records)
        total_cache = sum(r["cache_read_tokens"] + r["cache_create_tokens"] for r in records)
        total_out = sum(r["output_tokens"] for r in records)
        total_all = total_in + total_cache + total_out
        total_msgs = len(records)
        unique_models = set(r["model"] for r in records if r["model"])

        def fmt(n):
            if n >= 1_000_000:
                return f"{n/1_000_000:.1f}M"
            elif n >= 1_000:
                return f"{n/1_000:.1f}K"
            return str(n)

        ttk.Label(main, text="📊 Token 用量统计", font=("Segoe UI", 14, "bold")).pack(pady=(0, 2))
        ttk.Label(main, text=f"来源: {get_claude_data_dir()}\\projects\\", foreground="#888").pack(pady=(0, 10))

        # 汇总卡片
        card_frame = ttk.Frame(main)
        card_frame.pack(fill=tk.X, pady=(0, 10))

        cards = [
            ("消息数", f"{total_msgs} 条"),
            ("总 Token", fmt(total_all)),
            ("Input", fmt(total_in)),
            ("Cache", fmt(total_cache)),
            ("Output", fmt(total_out)),
            ("模型数", f"{len(unique_models)} 个"),
        ]

        for i, (label, value) in enumerate(cards):
            card = ttk.LabelFrame(card_frame, text=label, padding="6 4 6 4")
            card.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="nsew")
            ttk.Label(card, text=value, font=("Segoe UI", 12, "bold")).pack()
        for i in range(3):
            card_frame.columnconfigure(i, weight=1)

        # 模型分布
        if unique_models:
            ttk.Label(main, text="模型用量", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(4, 2))
            model_table = ttk.Frame(main)
            model_table.pack(fill=tk.X, pady=(0, 4))
            ttk.Label(model_table, text="模型", font=("Segoe UI", 9, "bold"), width=28, anchor=tk.W).grid(row=0, column=0, sticky="w")
            ttk.Label(model_table, text="消息数", font=("Segoe UI", 9, "bold"), width=10).grid(row=0, column=1)
            ttk.Label(model_table, text="Input", font=("Segoe UI", 9, "bold"), width=10).grid(row=0, column=2)
            ttk.Label(model_table, text="Output", font=("Segoe UI", 9, "bold"), width=10).grid(row=0, column=3)

            model_stats = {}
            for r in records:
                m = r["model"] or "unknown"
                if m not in model_stats:
                    model_stats[m] = {"count": 0, "in": 0, "out": 0}
                model_stats[m]["count"] += 1
                model_stats[m]["in"] += r["input_tokens"] + r["cache_read_tokens"] + r["cache_create_tokens"]
                model_stats[m]["out"] += r["output_tokens"]

            for row_i, (m, s) in enumerate(sorted(model_stats.items(), key=lambda x: x[1]["in"], reverse=True)):
                ttk.Label(model_table, text=m, font=("Consolas", 8)).grid(row=row_i + 1, column=0, sticky="w", pady=1)
                ttk.Label(model_table, text=str(s["count"])).grid(row=row_i + 1, column=1, pady=1)
                ttk.Label(model_table, text=fmt(s["in"])).grid(row=row_i + 1, column=2, pady=1)
                ttk.Label(model_table, text=fmt(s["out"])).grid(row=row_i + 1, column=3, pady=1)

        # 最近记录
        ttk.Label(main, text="最近 20 条", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(8, 2))

        list_frame = ttk.Frame(main)
        list_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(list_frame, columns=("time", "model", "in", "out"),
                            show="headings", height=12)
        tree.heading("time", text="时间")
        tree.heading("model", text="模型")
        tree.heading("in", text="Input")
        tree.heading("out", text="Output")
        tree.column("time", width=100)
        tree.column("model", width=190)
        tree.column("in", width=90)
        tree.column("out", width=90)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for r in records[:20]:
            ts = r["timestamp"][:19].replace("T", " ") if r["timestamp"] else ""
            it = r["input_tokens"] + r["cache_read_tokens"] + r["cache_create_tokens"]
            tree.insert("", tk.END, values=(ts, r["model"], fmt(it), fmt(r["output_tokens"])))

        ttk.Button(main, text="关闭", command=win.destroy).pack(pady=(6, 0))

    def _export_dsg(self):
        """按当前配置输出启动脚本：{模型名}Go"""
        self._save()

        api_url = self.url_var.get().strip()
        api_token = self._current_full_key
        work_dir = self.dir_var.get().strip() or os.path.expanduser("~")
        model = self.model_var.get().strip()
        os_type = self.config.get("os_type", OS_TYPE)
        preset = self.preset_var.get()

        if not api_token:
            messagebox.showwarning("提示", "请先填写 API Key")
            return

        # 文件名：预设名 + Go
        safe_name = preset.replace(" ", "").replace("/", "-")
        script_name = f"{safe_name}Go"

        if os_type == "Windows":
            ext = ".bat"
            env_lines = (
                f"$env:ANTHROPIC_BASE_URL='{api_url}'; "
                f"$env:ANTHROPIC_AUTH_TOKEN='{api_token}'; "
                f"$env:ANTHROPIC_MODEL='{model}'; "
                f"$env:ANTHROPIC_DEFAULT_OPUS_MODEL='{model}'; "
                f"$env:ANTHROPIC_DEFAULT_SONNET_MODEL='{model}'; "
                f"$env:ANTHROPIC_DEFAULT_HAIKU_MODEL='deepseek-v4-flash'; "
                f"$env:CLAUDE_CODE_SUBAGENT_MODEL='deepseek-v4-flash'; "
                f"$env:CLAUDE_CODE_SHOW_COST='true'"
            )
            content = (
                "@echo off\r\n"
                f"start powershell.exe -NoExit -Command \"Set-Location '{work_dir}'; {env_lines}; claude.cmd\"\r\n"
            )
        else:
            ext = ".sh"
            exports = (
                f"export ANTHROPIC_BASE_URL='{api_url}'\n"
                f"export ANTHROPIC_AUTH_TOKEN='{api_token}'\n"
                f"export ANTHROPIC_MODEL='{model}'\n"
                f"export ANTHROPIC_DEFAULT_OPUS_MODEL='{model}'\n"
                f"export ANTHROPIC_DEFAULT_SONNET_MODEL='{model}'\n"
                f"export ANTHROPIC_DEFAULT_HAIKU_MODEL='deepseek-v4-flash'\n"
                f"export CLAUDE_CODE_SUBAGENT_MODEL='deepseek-v4-flash'\n"
                f"export CLAUDE_CODE_SHOW_COST='true'\n"
            )
            content = (
                "#!/bin/bash\n"
                f"cd \"{work_dir}\"\n"
                f"{exports}"
                "claude\n"
            )

        # 选择保存路径
        filepath = filedialog.asksaveasfilename(
            title="保存启动脚本",
            initialfile=script_name + ext,
            defaultextension=ext,
            filetypes=[("脚本文件", f"*{ext}"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        self.status.configure(text=f"✅ 已输出: {os.path.basename(filepath)}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ClaudeLauncher()
    app.run()
