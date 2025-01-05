import uiautomation as auto
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import pyperclip
from tkinter import messagebox
import pythoncom
from difflib import SequenceMatcher
import queue
from .gpt4o import ask
import json
import configparser
from tkhtmlview import HTMLScrolledText
import markdown
from tkinterweb import HtmlFrame  # 新增导入
import os
import pkg_resources


cap_interval=1 #s 0.2-0.5se
copy_prefix="""Please answer the interview question quickly based on the following requirements:
1. Professional and relevant, meeting the interviewer's expectations.
2. Able to understand typos or transcription errors in the question.
3. Use bullet points, clear structure, and highlight key points for easy and quick response.
----------------------

"""

class ConfigWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Configuration")
        self.window.geometry("600x800")
        self.window.minsize(600, 800)
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 从config中读取当前配置
        config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
        config_path = pkg_resources.resource_filename('TikTalk', 'config.ini')
        config.read(config_path, encoding='utf-8')
        current_model = config.get('GenAI', 'model', fallback='o1-all')
        
        # 模型选择
        model_frame = ttk.LabelFrame(main_frame, text="Model Selection", padding="5")
        model_frame.pack(fill=tk.X, pady=5)
        
        self.model_var = tk.StringVar(value=current_model)  # 使用配置文件中的值
        models = ["o1-all", "o1-mini", "gpt-4o", "claude-3-5-sonnet-20241022", 
                 "o1-preview", "o1-pro-all"]
        
        for model in models:
            ttk.Radiobutton(model_frame, text=model, value=model, 
                          variable=self.model_var).pack(anchor=tk.W)
        
        # 从config中读取默认文本
        default_jd = config.get('Defaults', 'default_jd', 
            fallback="111\n222\n333")
        default_cv = config.get('Defaults', 'default_cv', 
            fallback="333\n222\n111")
        default_notes = config.get('Defaults', 'default_notes', 
            fallback="Please provide a detailed analysis...")
        
        # 默认JD
        jd_frame = ttk.LabelFrame(main_frame, text="Default JD", padding="5")
        jd_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.jd_text = scrolledtext.ScrolledText(
            jd_frame,
            wrap=tk.WORD,
            height=4,
            font=("Microsoft YaHei UI", 10)
        )
        self.jd_text.pack(fill=tk.BOTH, expand=True)
        self.jd_text.insert(tk.END, default_jd)
        
        # 默认CV
        cv_frame = ttk.LabelFrame(main_frame, text="Default CV", padding="5")
        cv_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.cv_text = scrolledtext.ScrolledText(
            cv_frame,
            wrap=tk.WORD,
            height=4,
            font=("Microsoft YaHei UI", 10)
        )
        self.cv_text.pack(fill=tk.BOTH, expand=True)
        self.cv_text.insert(tk.END, default_cv)
        
        # 默认Notes
        notes_frame = ttk.LabelFrame(main_frame, text="Default Notes", padding="5")
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.notes_text = scrolledtext.ScrolledText(
            notes_frame,
            wrap=tk.WORD,
            height=4,
            font=("Microsoft YaHei UI", 10)
        )
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        self.notes_text.insert(tk.END, default_notes)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)

    def save_config(self):
        config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
        config_path = pkg_resources.resource_filename('TikTalk', 'config.ini')
        config.read(config_path, encoding='utf-8')
        
        if 'GenAI' not in config:
            config['GenAI'] = {}
        if 'Defaults' not in config:
            config['Defaults'] = {}
        
        # 保存模型选择
        config['GenAI']['model'] = self.model_var.get()
        
        # 保存默认文本
        config['Defaults']['default_jd'] = self.jd_text.get(1.0, tk.END).strip()
        config['Defaults']['default_cv'] = self.cv_text.get(1.0, tk.END).strip()
        config['Defaults']['default_notes'] = self.notes_text.get(1.0, tk.END).strip()
        
        # 写入配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        self.window.destroy()

class LiveCaptionUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Live Caption Transcript")
        self.root.minsize(800, 500)
        
        # 设置分隔条样式
        style = ttk.Style()
        style.configure('TPanedwindow', background='#B3E5FC')  # 设置整体背景色
        style.configure('TPanedwindow.Sash', 
                       sashthickness=8,          # 增加分隔条厚度
                       sashrelief='raised',      # 凸起效果
                       background='#4FC3F7')     # 分隔条颜色(更深的蓝色)
        
        # 添加用于LLM调用的成员变量
        self.llm_queue = queue.Queue()
        self.button_states = {'ask': False}
        self.buttons = {}
        self.animation_count = 0
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # 配置root的grid权重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 配置main_frame的grid权重
        self.main_frame.grid_rowconfigure(0, weight=1)  # 上部分(PanedWindow)
        self.main_frame.grid_rowconfigure(1, weight=0)  # 按钮区域 - 固定高度
        self.main_frame.grid_rowconfigure(2, weight=0)  # 状态栏 - 固定高度
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # 创建垂直方向的PanedWindow为主容器
        self.main_paned = ttk.PanedWindow(
            self.main_frame, 
            orient=tk.VERTICAL
        )
        self.main_paned.grid(row=0, column=0, sticky="nsew")
        
        # 创建上部面板
        self.upper_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.upper_frame, weight=3)  # 上部分配更多空间
        
        # 创建水平方向的PanedWindow
        self.paned_window = ttk.PanedWindow(
            self.upper_frame, 
            orient=tk.HORIZONTAL
        )
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 设置分隔条的宽度
        self.main_paned.configure(width=8)
        self.paned_window.configure(width=8)
        
        # 左侧面板 - 字幕显示
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # 右侧面板
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        # 创建左侧文本显示区域
        self.text_area = tk.Text(
            self.left_frame,
            wrap=tk.WORD,
            width=40,
            height=20,
            font=("Microsoft YaHei UI", 10),
            cursor="hand2",
            spacing1=5,  # 行前空白
            spacing3=5,  # 行后空白
            selectbackground="#E1F5FE",  # 浅蓝色选中背景
            selectforeground="black"     # 选中文字颜色保持黑色
        )
        
        # 添加垂直滚动条（修正位置）
        self.scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical")
        self.text_area.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.text_area.yview)
        
        # 正确的布局方式
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置标签样式
        self.text_area.tag_configure("selected_line", background="#E1F5FE")
        
        # 绑定鼠标事件
        self.text_area.bind("<Button-1>", self.handle_line_click)
        self.text_area.bind("<B1-Motion>", self.handle_line_drag)
        self.text_area.bind("<ButtonRelease-1>", self.handle_line_release)
        
        # 禁用默认的文本选择
        self.text_area.bind("<<Selection>>", lambda e: "break")
        
        # 用于跟踪选中的行
        self.selected_lines = set()
        self.drag_start_line = None
        
        # 创建右侧文本框
        self.create_right_panels()
        
        # 创建下部答案面板
        self.lower_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.lower_frame, weight=1)  # 下部分配较少空间
        
        # 创建答案文本框
        self.create_answer_panel()
        
        # 配置main_frame的grid权重
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # 加载配置
        self.load_config()
        
        # 创建按钮面板
        self.create_buttons()
        
        # 创建字幕捕获器
        self.capturer = LiveCaptionCapture(self)
        
        # 创建状态栏
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_bar.grid(row=2, column=0, sticky="w")
        self.status_var.set("就绪")
        
        self.last_displayed_text = ""
        
        # 启动消息处理循环
        self.process_llm_responses()
        
        # 添加空格键点击计时器
        self.space_clicks = []
        
        # 绑定ESC键和空格键
        self.root.bind('<Escape>', self.handle_escape)
        self.root.bind('<space>', self.handle_space)

    def create_right_panels(self):
        """创建右侧的三个文本框"""
        # JD Panel
        jd_frame = ttk.LabelFrame(self.right_frame, text="JD")
        jd_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.jd_text = scrolledtext.ScrolledText(
            jd_frame,
            wrap=tk.WORD,
            height=6,
            font=("Microsoft YaHei UI", 10)
        )
        self.jd_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # CV Panel
        cv_frame = ttk.LabelFrame(self.right_frame, text="CV")
        cv_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.cv_text = scrolledtext.ScrolledText(
            cv_frame,
            wrap=tk.WORD,
            height=6,
            font=("Microsoft YaHei UI", 10)
        )
        self.cv_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Notes Panel
        notes_frame = ttk.LabelFrame(self.right_frame, text="Notes")
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.notes_text = scrolledtext.ScrolledText(
            notes_frame,
            wrap=tk.WORD,
            height=6,
            font=("Microsoft YaHei UI", 10)
        )
        self.notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_answer_panel(self):
        """创建答案面板"""
        # Answer Panel
        answer_frame = ttk.LabelFrame(self.lower_frame, text="Answer")
        answer_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 使用 HtmlFrame 替换 HTMLScrolledText
        self.answer_text = HtmlFrame(
            answer_frame,
            messages_enabled=False,  # 禁用控制台消息
            vertical_scrollbar=True,  # 启用垂直滚动条
            horizontal_scrollbar=False  # 禁用水平滚动条
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加基本样式
        default_style = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                color: #333;
                padding: 10px;
            }
            ul, ol {
                padding-left: 20px;
                margin: 10px 0;
            }
            li {
                margin: 5px 0;
            }
            p {
                margin: 10px 0;
            }
            code {
                background-color: #f6f8fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: Monaco, Consolas, "Courier New", monospace;
            }
            pre {
                background-color: #f6f8fa;
                padding: 12px;
                border-radius: 6px;
                overflow-x: auto;
            }
            blockquote {
                border-left: 4px solid #dfe2e5;
                padding-left: 16px;
                margin: 16px 0;
                color: #6a737d;
            }
            h1, h2, h3, h4, h5, h6 {
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                line-height: 1.25;
            }
        </style>
        """
        
        # 设置初始内容
        self.answer_text.load_html(
            default_style + 
            '<div class="answer-content"><p>Answer will appear here...</p></div>'
        )

    def set_answer_html(self, markdown_text):
        """设置答案区域的内容"""
        # 转换 markdown 为 HTML
        html_content = markdown.markdown(
            markdown_text,
            extensions=['extra', 'codehilite', 'tables']  # 启用额外的markdown特性
        )
        
        # 组合完整的HTML
        full_html = f"""
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                color: #333;
                padding: 10px;
            }}
            ul, ol {{
                padding-left: 20px;
                margin: 10px 0;
            }}
            li {{
                margin: 5px 0;
            }}
            p {{
                margin: 10px 0;
            }}
            code {{
                background-color: #f6f8fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: Monaco, Consolas, "Courier New", monospace;
            }}
            pre {{
                background-color: #f6f8fa;
                padding: 12px;
                border-radius: 6px;
                overflow-x: auto;
            }}
            blockquote {{
                border-left: 4px solid #dfe2e5;
                padding-left: 16px;
                margin: 16px 0;
                color: #6a737d;
            }}
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
                line-height: 1.25;
            }}
        </style>
        <div class="answer-content">
            {html_content}
        </div>
        """
        
        # 新显示
        self.answer_text.load_html(full_html)

    def create_buttons(self):
        """创建按钮面板"""
        # 创建按钮框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # 创建内部框架来放置按钮
        inner_button_frame = ttk.Frame(button_frame)
        inner_button_frame.pack(side=tk.LEFT)
        
        # 创建自定义样式
        style = ttk.Style()
        style.configure('Custom.TButton', padding=5)
        style.configure('Ask.TButton', 
                       padding=5,
                       foreground='#1976D2')  # 使用蓝色字体
        
        # Start/Stop 按钮
        self.start_button = ttk.Button(
            inner_button_frame,
            text="Start",
            style='Custom.TButton',
            command=self.toggle_capture
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Clear 按钮
        self.clear_button = ttk.Button(
            inner_button_frame,
            text="Clear",
            style='Custom.TButton',
            command=self.clear_text
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Copy 按钮
        self.copy_button = ttk.Button(
            inner_button_frame,
            text="Copy",
            style='Custom.TButton',
            command=self.copy_text
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)
        
        # Save 按钮
        self.save_button = ttk.Button(
            inner_button_frame,
            text="Save",
            style='Custom.TButton',
            command=self.save_text
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Config 按钮
        self.config_button = ttk.Button(
            inner_button_frame,
            text="Config",
            style='Custom.TButton',
            command=self.show_config
        )
        self.config_button.pack(side=tk.LEFT, padx=5)
        
        # Ask 按钮
        self.ask_button = ttk.Button(
            inner_button_frame,
            text="Ask",
            style='Ask.TButton',  # 使用蓝色字体的样式
            command=self.handle_ask
        )
        self.ask_button.pack(side=tk.LEFT, padx=5)
        self.buttons['ask'] = self.ask_button

    def toggle_capture(self):
        if self.start_button["text"] == "开始捕获":
            self.start_capture()
        else:
            self.stop_capture()

    def start_capture(self):
        self.start_button["text"] = "停止捕获"
        self.status_var.set("正在捕获...")
        # 使用新的方法启动捕获线程
        self.capture_thread = CaptureThread(self.capturer)
        self.capture_thread.start()

    def stop_capture(self):
        self.start_button["text"] = "开始捕获"
        self.status_var.set("已停止捕获")
        self.capturer.stop_capture()

    def clear_text(self):
        self.text_area.delete(1.0, tk.END)
        self.jd_text.delete(1.0, tk.END)
        self.cv_text.delete(1.0, tk.END)
        self.notes_text.delete(1.0, tk.END)
        self.answer_text.set_html("<p>Answer will appear here...</p>")  # 空答案区域
        self.last_displayed_text = ""
        self.status_var.set("已清空文本")

    def copy_text(self):
        # 获取所有文本框的内容
        transcript = self.text_area.get(1.0, tk.END).strip()
        jd = self.jd_text.get(1.0, tk.END).strip()
        cv = self.cv_text.get(1.0, tk.END).strip()
        notes = self.notes_text.get(1.0, tk.END).strip()
        answer = self.answer_text.get_text()  # 使用get_text()来获取纯文本内容
        
        # 组合所有内容
        all_text = f"Transcript:\n{transcript}\n\nJD:\n{jd}\n\nCV:\n{cv}\n\nNotes:\n{notes}\n\nAnswer:\n{answer}"
        
        if all_text.strip():
            pyperclip.copy(all_text)
            self.status_var.set("文本已复制到剪贴板")
        else:
            messagebox.showinfo("提示", "没有可复制的文本")

    def save_text(self):
        # 获取所有文本内容
        transcript = self.text_area.get(1.0, tk.END).strip()
        jd = self.jd_text.get(1.0, tk.END).strip()
        cv = self.cv_text.get(1.0, tk.END).strip()
        notes = self.notes_text.get(1.0, tk.END).strip()
        answer = self.answer_text.get_text()  # 使用get_text()来获取纯文本内容
        
        # 组合所有内容
        all_text = f"Transcript:\n{transcript}\n\nJD:\n{jd}\n\nCV:\n{cv}\n\nNotes:\n{notes}\n\nAnswer:\n{answer}"
        
        if not all_text.strip():
            messagebox.showinfo("提示", "没有可保存的文本")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(all_text)
                self.status_var.set(f"文件已保存: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错：{str(e)}")

    def append_text(self, text):
        """添加新文本，包含去重逻辑"""
        if not text:
            return

        # print("\n[DEBUG] ===== 开始处理新文本 =====")
        # print(f"[DEBUG] 新文本: '{text}'")
        # print(f"[DEBUG] 上一次显示的文本: '{self.last_displayed_text}'")

        # 如果是第一条文本
        if not self.last_displayed_text:
            # print("[DEBUG] 这是第一条文本，接显示")
            self.text_area.insert(tk.END, f"{text}\n")
            self.last_displayed_text = text
            self.text_area.see(tk.END)
            return

        # 检查是否是重复文本
        if self._should_replace_last_line(text):
            # print("[DEBUG] 检测到需要替换最后一行")
            # 删除最后一行
            last_line_start = self.text_area.get("end-2c linestart", "end-1c")
            # print(f"[DEBUG] 将要被替换的最后一行: '{last_line_start}'")
            self.text_area.delete("end-2c linestart", "end-1c")
            # 添加新行
            self.text_area.insert(tk.END, f"{text}\n")
            #  print(f"[DEBUG] 已替换为新文本: '{text}'")
        else:
            # print("[DEBUG] 这是新的不重复文本，直接添加")
            # 添加新行
            self.text_area.insert(tk.END, f"{text}\n")

        self.last_displayed_text = text
        self.text_area.see(tk.END)
        # print("[DEBUG] ===== 文本处理完成 =====\n")

    def _should_replace_last_line(self, new_text):
        """判断是否应该替换最后一行"""
        # print("\n[DEBUG] ----- 开始判断是否换 -----")
        # 检查是否含上一行文
        if self.last_displayed_text in new_text:
            # print(f"[DEBUG] 新文本包含上一行文本")
            # print(f"[DEBUG] 上一行: '{self.last_displayed_text}'")
            # print(f"[DEBUG] 新本: '{new_text}'")
            # print("[DEBUG] 判断结果: 需要替换")
            return True

        # 计算编辑距离比例
        similarity_ratio = SequenceMatcher(None, self.last_displayed_text, new_text).ratio()
        edit_distance_ratio = 1 - similarity_ratio
        # print(f"[DEBUG] 相似度: {similarity_ratio:.3f}")
        # print(f"[DEBUG] 编辑距离比例: {edit_distance_ratio:.3f}")

        # 如果编辑距离占比小于20%，认为是重复文本
        should_replace = edit_distance_ratio < 0.2
        # print(f"[DEBUG] 判断结果: {'需要' if should_replace else '不需要'}替换")
        # print("[DEBUG] ----- 判断结束 -----\n")
        return should_replace

    def handle_ask(self):
        """处理Ask按钮点击事件"""
        # 根据选中状态获取transcript内容
        if self.selected_lines:
            # 获取选中的行内容
            selected_texts = []
            for line_num in sorted(self.selected_lines):
                line_start = f"{line_num}.0"
                line_end = f"{line_num}.end"
                text = self.text_area.get(line_start, line_end).strip()
                if text:
                    selected_texts.append(text)
            transcript = " ".join(selected_texts)
        else:
            # 如果没有中的行，获取所有文本
            transcript = self.text_area.get(1.0, tk.END).strip()

        # 获取其他本内容
        jd = self.jd_text.get(1.0, tk.END).strip()
        cv = self.cv_text.get(1.0, tk.END).strip()
        notes = self.notes_text.get(1.0, tk.END).strip()
        
        # 构prompt
        prompt = f"""I am interviewing for the following position. Please help me respond to the interviewer's questions based on the information provided below. Ensure the answers are concise and professional. Additionally, please provide bilingual responses (each point should alternate between Chinese and English, with Chinese on top).
Unless otherwise specified in the notes, please default to answering only the last question raised by the interviewer (ignore previous questions).
Since the questions are transcribed from audio, there may be some errors or homophone confusions. Please don't mind and handle them intelligently.


# Job Description:
{jd}

# My Resume:
{cv}

# questions raised by the interviewer:
{transcript}

Additional Notes:
{notes}

"""
        
        # 建消息格式
        messages = [
            {"role": "user", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        
        # 异步调用LLM
        self.call_llm_async("answer", messages, "Ask")

    def call_llm_async(self, msg_type, msgs, button_name):
        """异步调用LLM"""
        def run_llm():
            try:
                # 开始动画
                self.button_states[button_name.lower()] = True
                self.root.after(0, self.update_button_animation)
                
                # 调用GPT4o API
                response = ask(msgs)
                self.llm_queue.put((msg_type, response))
                
            except Exception as e:
                self.llm_queue.put(("error", f"LLM调用失败: {str(e)}"))
            finally:
                # 停止动画
                self.button_states[button_name.lower()] = False
                # 恢复按钮文字
                self.root.after(0, lambda: self.buttons[button_name.lower()].configure(
                    text=button_name))
        
        thread = threading.Thread(target=run_llm)
        thread.daemon = True
        thread.start()

    def update_button_animation(self):
        """更新按钮动画"""
        for button_name, is_active in self.button_states.items():
            if is_active:
                dots = "." * (self.animation_count % 4)
                self.buttons[button_name].configure(text=f"Thinking{dots}")
        
        self.animation_count += 1
        
        # 如果还有活动按钮，继续动画
        if any(self.button_states.values()):
            self.root.after(500, self.update_button_animation)

    def process_llm_responses(self):
        """处理LLM返回的响应"""
        try:
            while True:
                try:
                    msg_type, response = self.llm_queue.get_nowait()
                    if msg_type == "error":
                        messagebox.showerror("错误", response)
                    elif msg_type == "answer":
                        # 使用新的方法显示答案
                        self.set_answer_html(response)
                except queue.Empty:
                    break
        finally:
            # 继续监听队列
            self.root.after(100, self.process_llm_responses)

    def run(self):
        self.root.mainloop()

    def load_config(self):
        """加载配置"""
        try:
            config_path = pkg_resources.resource_filename('TikTalk', 'config.ini')
            config = configparser.ConfigParser(interpolation=None)
            config.read(config_path, encoding='utf-8')
            
            # 确保必要的配置节存在
            if 'Defaults' not in config:
                config['Defaults'] = {}
            
            # 设置默认值
            self.default_jd = config.get('Defaults', 'default_jd', 
                fallback="Please input job description here...")
            self.default_cv = config.get('Defaults', 'default_cv', 
                fallback="Please input your CV here...")
            self.default_notes = config.get('Defaults', 'default_notes', 
                fallback="Please provide a detailed analysis...")
            
            # 更新文本框
            if not self.jd_text.get(1.0, tk.END).strip():
                self.jd_text.delete(1.0, tk.END)
                self.jd_text.insert(tk.END, self.default_jd)
            if not self.cv_text.get(1.0, tk.END).strip():
                self.cv_text.delete(1.0, tk.END)
                self.cv_text.insert(tk.END, self.default_cv)
            if not self.notes_text.get(1.0, tk.END).strip():
                self.notes_text.delete(1.0, tk.END)
                self.notes_text.insert(tk.END, self.default_notes)
            return config
        except Exception as e:
            print(f"Failed to load config: {e}")
            return None

    def show_config(self):
        """显示配置窗口"""
        config_window = tk.Toplevel(self.root)
        config_window.title("Configuration")
        config_window.minsize(400, 600)
        
        # 创建主框架添加滚动条
        main_frame = ttk.Frame(config_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 读取配置
        config = configparser.ConfigParser(interpolation=None)
        config_path = pkg_resources.resource_filename('TikTalk', 'config.ini')
        config.read(config_path, encoding='utf-8')
        
        # 确保必要的配置节存在
        if 'Endpoints' not in config:
            config['Endpoints'] = {
                'endpoints': 'aigcbest,adamchatbot,gptapi',
                'current': 'adamchatbot'
            }
        
        if 'GenAI' not in config:
            config['GenAI'] = {'model': 'o1-all'}
            
        # 确保Models节存在
        if 'Models' not in config:
            config['Models'] = {
                'adamchatbot_models': 'gpt-4o,claude-3-5-sonnet-20241022,o1-mini-all,o1-all',
                'aigcbest_models': 'gpt-4o-mini,gpt-4o,o1-mini,claude-3-5-sonnet-20241022,gemini-2.0-flash-exp,gemini-2.0-flash-thinking-exp,gemini-exp-1206,o1-preview,o1,o1-mini-all,o1-all,o1-preview-all,o1-pro-all',
                'gptapi_models': 'o1,o1-preview,gemini-2.0-flash-exp,gemini-2.0-flash-thinking-exp,o1-mini'
            }
            # 保存配置到文件以确保Models节被持久化
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
        
        # 先创建Endpoint Selection Section
        endpoint_frame = ttk.LabelFrame(main_frame, text="Endpoint Selection")
        endpoint_frame.pack(fill=tk.X, padx=5, pady=5)
        
        endpoints = config.get('Endpoints', 'endpoints', fallback='aigcbest,adamchatbot,gptapi').split(',')
        current_endpoint = config.get('Endpoints', 'current', fallback='adamchatbot')
        endpoint_var = tk.StringVar(value=current_endpoint)
        endpoint_combo = ttk.Combobox(
            endpoint_frame, 
            textvariable=endpoint_var,
            values=endpoints,
            state='readonly'
        )
        endpoint_combo.pack(fill=tk.X, padx=5, pady=5)
        
        # 然后创建Model Selection Section
        model_frame = ttk.LabelFrame(main_frame, text="Model Selection")
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建模型选择变量
        model_var = tk.StringVar(value=config.get('GenAI', 'model', fallback='o1-all'))
        
        def update_model_list(*args):
            # 清除现有的单选按钮
            for widget in model_frame.winfo_children():
                widget.destroy()
                
            # 获取当前选中的endpoint
            current_endpoint = endpoint_var.get()
            
            print(f"Updating models for endpoint: {current_endpoint}")  # 调试信息
            print(f"Config sections: {config.sections()}")  # 显示所有配置节
            
            try:
                # 获取对应的模型列表
                model_key = f'{current_endpoint}_models'
                print(f"Looking for model key: {model_key}")  # 调试信息
                models_str = config.get('Models', model_key, fallback='o1-all')
                print(f"Available models: {models_str}")  # 调试信息
                print(f"Raw Models section: {dict(config['Models'])}")  # 显示Models节的原始内容
                models = models_str.split(',')
                
                # 如果当前选中的模型不在新的模型列表中，设置为第一个可用模型
                if model_var.get() not in models:
                    model_var.set(models[0])
                
                # 创建新的单选按钮
                for model in models:
                    ttk.Radiobutton(
                        model_frame,
                        text=model,
                        variable=model_var,
                        value=model
                    ).pack(anchor=tk.W, padx=5, pady=2)
            except Exception as e:
                print(f"Error updating model list: {str(e)}")  # 调试信息
        
        # 绑定endpoint选择变更事件
        endpoint_var.trace('w', update_model_list)
        
        # 初始化模型列表
        update_model_list()
        
        # Default Text Section
        default_frame = ttk.LabelFrame(main_frame, text="Default Text")
        default_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # JD Text
        jd_label = ttk.Label(default_frame, text="Default JD:")
        jd_label.pack(anchor=tk.W, padx=5, pady=2)
        jd_text = scrolledtext.ScrolledText(default_frame, height=4)
        jd_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        jd_text.insert("1.0", config.get('Defaults', 'default_jd', 
            fallback='Please input job description here...'))
        
        # CV Text
        cv_label = ttk.Label(default_frame, text="Default CV:")
        cv_label.pack(anchor=tk.W, padx=5, pady=2)
        cv_text = scrolledtext.ScrolledText(default_frame, height=4)
        cv_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        cv_text.insert("1.0", config.get('Defaults', 'default_cv',
            fallback='Please input your CV here...'))
        
        # Notes Text
        notes_label = ttk.Label(default_frame, text="Default Notes:")
        notes_label.pack(anchor=tk.W, padx=5, pady=2)
        notes_text = scrolledtext.ScrolledText(default_frame, height=4)
        notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        notes_text.insert("1.0", config.get('Defaults', 'default_notes',
            fallback='Please provide a detailed analysis...'))
        
        def save_config():
            # 保存endpoint选择
            config.set('Endpoints', 'current', endpoint_var.get())
            
            # 保存模型选择
            config.set('GenAI', 'model', model_var.get())
            
            # 保存默认文本
            config.set('Defaults', 'default_jd', jd_text.get("1.0", tk.END).strip())
            config.set('Defaults', 'default_cv', cv_text.get("1.0", tk.END).strip())
            config.set('Defaults', 'default_notes', notes_text.get("1.0", tk.END).strip())
            
            # 保存配置到文件
            config_path = pkg_resources.resource_filename('TikTalk', 'config.ini')
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # 重新加载配置
            self.load_config()
            
            # 更新默认文本
            if not self.jd_text.get(1.0, tk.END).strip():
                self.jd_text.delete(1.0, tk.END)
                self.jd_text.insert(tk.END, self.default_jd)
            if not self.cv_text.get(1.0, tk.END).strip():
                self.cv_text.delete(1.0, tk.END)
                self.cv_text.insert(tk.END, self.default_cv)
            if not self.notes_text.get(1.0, tk.END).strip():
                self.notes_text.delete(1.0, tk.END)
                self.notes_text.insert(tk.END, self.default_notes)
            
            config_window.destroy()
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # 保存和取消按钮
        ttk.Button(button_frame, text="Save", command=save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=config_window.destroy).pack(side=tk.RIGHT, padx=5)

    def handle_line_click(self, event):
        """处理行点击事件"""
        index = self.text_area.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        
        # 记录拖动起始行
        self.drag_start_line = line_num
        
        # 如果按住Ctrl键，不清除之前的择
        if not event.state & 0x4:  # 0x4 是Ctrl键的状态码
            self.clear_all_selections()
            
        self.toggle_line_selection(line_num)
        
        # 复制选中的内容到剪贴板
        self.copy_selected_to_clipboard()
        
        return "break"  # 阻止默认的文本选择

    def handle_line_drag(self, event):
        """处理拖动选择"""
        if self.drag_start_line is None:
            return "break"
        
        current_line = int(self.text_area.index(f"@{event.x},{event.y}").split('.')[0])
        
        # 清除之前的选择（除了起始行）
        self.clear_all_selections()
        
        # 选择拖动范围内的所有行
        start = min(self.drag_start_line, current_line)
        end = max(self.drag_start_line, current_line)
        
        for line in range(start, end + 1):
            self.toggle_line_selection(line, force_select=True)
        
        # 复制选中的内容到剪贴板
        self.copy_selected_to_clipboard()
        
        return "break"

    def copy_selected_to_clipboard(self):
        """复制选中的内容到剪贴板"""
        if not self.selected_lines:
            return
        
        # 获取选中的行内容
        selected_texts = []
        for line_num in sorted(self.selected_lines):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            text = self.text_area.get(line_start, line_end).strip()
            if text:
                selected_texts.append(text)
        
        if selected_texts:
            # 添加前缀文本
            prefix = copy_prefix
            # 将内容复制到剪贴板
            text = prefix + "\n".join(selected_texts)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            
            # 创建提示窗口
            popup = tk.Toplevel()
            popup.overrideredirect(True)  # 移除窗口装饰
            popup.attributes('-topmost', True)  # 保持在最上层
            
            # 计算弹窗位置（居中显示）
            x = self.root.winfo_x() + self.root.winfo_width()//2 - 100
            y = self.root.winfo_y() + self.root.winfo_height()//2 - 25
            popup.geometry(f"200x50+{x}+{y}")
            
            # 添加提示文本
            label = ttk.Label(
                popup, 
                text="已复制选中内容到剪贴板",
                wraplength=180,
                justify="center"
            )
            label.pack(expand=True)
            
            # 1.2秒后自动关闭
            popup.after(1200, popup.destroy)

    def handle_line_release(self, event):
        """处理鼠标释放"""
        self.drag_start_line = None
        return "break"

    def toggle_line_selection(self, line_num, force_select=False):
        """切换行选择状态"""
        line_start = f"{line_num}.0"
        line_end = f"{line_num}.end"
        
        # 获取内容
        line_content = self.text_area.get(line_start, line_end).strip()
        if not line_content:
            return
            
        # 切换选中状态
        if not force_select and line_num in self.selected_lines:
            self.text_area.tag_remove("selected_line", line_start, line_end + "+1c")
            self.selected_lines.remove(line_num)
        else:
            self.text_area.tag_add("selected_line", line_start, line_end + "+1c")
            self.selected_lines.add(line_num)

    def clear_all_selections(self):
        """清除所有选中状态"""
        self.text_area.tag_remove("selected_line", "1.0", tk.END)
        self.selected_lines.clear()

    def update_text_area(self, sentences):
        """增量更新文本区域的内容"""
        # 如果句子数量没有变化，不更新
        if len(sentences) == self.current_line_count:
            return
        
        # 保存当前滚位置
        current_view = self.text_area.yview()
        
        # 获取当前所有行的内容
        current_lines = {}
        for i in range(1, self.current_line_count + 1):
            line_start = f"{i}.0"
            line_end = f"{i}.end"
            content = self.text_area.get(line_start, line_end).strip()
            if content:
                current_lines[i] = content

        # 清空文本区域
        self.text_area.delete("1.0", tk.END)
        new_selected_lines = set()
        
        # 添加句子
        for i, sentence in enumerate(sentences, 1):
            # 添加新行
            self.text_area.insert(tk.END, f"{sentence}\n")
            
            # 如果这行之前被选中，恢复选中状态
            if i in self.selected_lines:
                self.text_area.tag_add("selected_line", f"{i}.0", f"{i}.end+1c")
                new_selected_lines.add(i)
        
        # 更新行数选中状态
        self.current_line_count = len(sentences)
        self.selected_lines = new_selected_lines
        
        # 总是滚动到最新内容
        self.text_area.see(tk.END)

    def handle_escape(self, event):
        """处理ESC键按下事件"""
        self.clear_all_selections()
        return "break"

    def handle_space(self, event):
        """处理空格键点击事件"""
        current_time = time.time()
        
        # 清理超过1秒的点击记录
        self.space_clicks = [t for t in self.space_clicks if current_time - t < 1.0]
        
        # 添加新的点击时间
        self.space_clicks.append(current_time)
        
        # 如果在1秒内有3次点击，触发Ask
        if len(self.space_clicks) >= 3:
            self.space_clicks.clear()  # 清空点击记录
            self.handle_ask()
            return "break"
        
        return "break"  # 阻止空格键的默认行为

# 新增线程类来处理COM初始化
class CaptureThread(threading.Thread):
    def __init__(self, capturer):
        super().__init__()
        self.capturer = capturer
        self.daemon = True

    def run(self):
        try:
            # 线程中初始化COM
            pythoncom.CoInitialize()
            # 初始化UI Automation
            auto.InitializeUIAutomationInCurrentThread()
            # 动捕获
            self.capturer.start_capture()
        finally:
            # 清理COM
            pythoncom.CoUninitialize()

class LiveCaptionCapture:
    def __init__(self, ui):
        self.ui = ui
        self.running = False
        self.last_text = ""
        self.seen_fragments = set()
        self.current_sentence = ""
        self.last_processed_text = ""  # Track the last processed full text
        self.all_transcription = ""  # 新增：用于存储完整的转录文本
        self.last_common_end = 0     # 新增：记录上次找到的公共文本的结束位置
        
        # 加载配置
        config = configparser.ConfigParser(interpolation=None)
        config.read('config.ini', encoding='utf-8')
        # 获取字幕窗口标识符列表如果没有配置则使用认值
        try:
            self.caption_identifiers = json.loads(config.get('CaptionWindow', 'identifiers', 
                fallback='["Live Caption", "实时字幕"]'))
        except Exception as e:
            self.ui.status_var.set(f"加载字幕标识符配置出错，使用默认值: {str(e)}")
            self.caption_identifiers = ["Live Caption", "实时字幕"]

    def find_caption_window(self):
        try:
            # 遍历所有可能的标识符
            for identifier in self.caption_identifiers:
                caption_window = auto.WindowControl(searchDepth=1, ClassName='Chrome_WidgetWin_1', SubName=identifier)
                if caption_window.Exists(maxSearchSeconds=1):
                    return caption_window
            return None
        except Exception as e:
            self.ui.status_var.set(f"查找窗口错误: {str(e)}")
            return None

    def get_caption_text(self, window):
        try:
            doc_control = window.DocumentControl()
            if doc_control.Exists():
                text = doc_control.Name
                text = text.replace('\n', ' ').replace('\r', '')#.lower()
                return text
            return None
        except Exception as e:
            self.ui.status_var.set(f"获取文本错误: {str(e)}")
            return None

    def split_sentences(self, text):
        """统一的分句方法
        
        Args:
            text: 要分句的文本
            
        Returns:
            list: 分句后的句子列表
        """
        if not text:
            return []
        
        sentences = []
        current_sentence = ""
        
        # 分词处理
        words = text.split()
        
        for i, word in enumerate(words):
            current_sentence += word
            
            # 判断是否需要分句
            should_split = False
            
            # 检查标准句子结束符
            if word.endswith(('.', '!', '?')):
                # 1. 避免将 Mr./Dr. 等缩写误判为句子结束
                if not any(word.lower().startswith(prefix) for prefix in ['mr.', 'dr.', 'ms.', 'mrs.']):
                    # 2. 避免将数字中的小数点误判为句子结束符
                    if not (word.replace('.', '').replace(',', '').isdigit() or  # 处理纯数字
                           word[:-1].replace('.', '').replace(',', '').isdigit()):  # 处理以点结尾的数字
                        should_split = True
            
            # 添加空格（除是最后一个词）
            if i < len(words) - 1:
                current_sentence += " "
            
            # 执行分句
            if should_split:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # 处理最后一个句子（无论是否完整都添加）
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # 如果没有任何句子，但有文本，则将整个文本作为一句子
        if not sentences and text.strip():
            sentences.append(text.strip())
        
        return sentences

    def get_last_incomplete_sentence(self):
        """获取最后一个可能未完成的句子"""
        if not self.seen_fragments:
            return None
        last_sentence = list(self.seen_fragments)[-1]
        # 如果句子没有标准的结符号，为是未完成的
        if not last_sentence.endswith('.') and not last_sentence.endswith('?') and not last_sentence.endswith('!'):
            return last_sentence
        return None

    def is_similar_to_existing(self, new_sentence):
        """检查新句子是否与已存在的句子相似"""
        for existing in self.seen_fragments:
            # 如果新句子完全包含在现有句子中
            if new_sentence in existing:
                return True
            # 如果现有句子完全包含在新句子中，且新句子不是现有句子的显著扩展
            if existing in new_sentence and len(new_sentence) < len(existing) * 1.5:
                return True
            # 计算相似度，但使用更低的阈值
            similarity = SequenceMatcher(None, new_sentence, existing).ratio()
            if similarity > 0.9:  # 提高相似度阈值，少误判
                return True
        return False

    def start_capture(self):
        self.running = True
        self.ui.root.after(0, self.ui.status_var.set, "开始捕获...")
        
        while self.running:
            try:
                window = self.find_caption_window()
                if window:
                    text = self.get_caption_text(window)
                    if text:
                        # 只使用新的处理方法
                        self.process_text_v2(text)
                else:
                    time.sleep(3)
                    continue
                
                time.sleep(cap_interval)
                
            except Exception as e:
                self.ui.root.after(0, self.ui.status_var.set, f"发生错误: {str(e)}")
                time.sleep(1)

    def stop_capture(self):
        self.running = False
        self.ui.root.after(0, self.ui.status_var.set, "已停止捕获")

    def process_text_v2(self, new_text):
        """新文本处理方法"""
        if not new_text or not new_text.strip():
            return

        # 获取 all_transcription 的最后 800 个字符
        last_chunk = self.all_transcription[-800:] if len(self.all_transcription) > 800 else self.all_transcription

        # 找到最长公共子串
        common_text = self.find_longest_common_substring(last_chunk, new_text)
        
        if common_text:
            # 在历史文本中定位公共文本的位置
            hist_pos = self.all_transcription.rfind(common_text)
            if hist_pos != -1:
                # 保留史文本直到公共文本结束
                self.all_transcription = self.all_transcription[:hist_pos + len(common_text)]
                
                # 在新文本中定位公共文本的位置
                new_pos = new_text.find(common_text)
                if new_pos != -1:
                    # 获取新文本中公共文本后的部分
                    new_content = new_text[new_pos + len(common_text):].strip()
                    if new_content:
                        self.all_transcription += " " + new_content
        else:
            if self.all_transcription:
                self.all_transcription += " "
            self.all_transcription += new_text

        # 对完整的转录文本进行分句
        sentences = self.split_sentences(self.all_transcription)
        
        # 直接在主线程中更新UI
        self.ui.text_area.delete("1.0", tk.END)
        for i, sentence in enumerate(sentences, 1):
            self.ui.text_area.insert(tk.END, f"{sentence}\n")
            # 恢复选中状态
            if i in self.ui.selected_lines:
                self.ui.text_area.tag_add("selected_line", f"{i}.0", f"{i}.end+1c")
        self.ui.text_area.see(tk.END)

        # 调试输出
        # print("\n[DEBUG] 句结果:")
        # for i, sentence in enumerate(sentences, 1):
        #     print(f"[{i}] {sentence}")

    def find_longest_common_substring(self, str1, str2):
        """查找两个字符串中的最长公共串"""
        if not str1 or not str2:
            return ""
            
        # 创建动态规划矩阵
        m, n = len(str1), len(str2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # 记录最长子串的长度和结束位置
        max_length = 0
        end_pos = 0
        
        # 填充dp矩阵
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    if dp[i][j] > max_length:
                        max_length = dp[i][j]
                        end_pos = i
        
        # 返回最长公共子串
        if max_length == 0:
            return ""
        return str1[end_pos - max_length:end_pos]

    def process_text(self, new_text):
        if not new_text:
            return

        print("\n[DEBUG] ===== 开始一轮文本处理 =====")
        print(f"[DEBUG1] Chrome原始文本: '{new_text}'")
        # print(f"[DEBUG] 上次处理文本: '{self.last_processed_text}'")

        # 1. 文本差异分析
        if self.last_processed_text:
            # 找到第一个不同的位置
            diff_pos = -1
            for i, (c1, c2) in enumerate(zip(self.last_processed_text, new_text)):
                if c1 != c2:
                    diff_pos = i
                    break
            
            if diff_pos != -1:
                pass
                # print(f"[DEBUG] 检测到文本差异位置: {diff_pos}")
                # print(f"[DEBUG] 差异前文本: '{self.last_processed_text[max(0, diff_pos-20):diff_pos]}'")
                # print(f"[DEBUG] 差异后文本: '{new_text[max(0, diff_pos-20):diff_pos+20]}'")
                
                # 检查是否是修正还是新增
                # if len(new_text) < len(self.last_processed_text):
                #     print("[DEBUG] 检测到文本修正")
                #     pass
                # else:
                #     print("[DEBUG] 检测到文本新增")
                #     pass

        # 2. 分句处理
        sentences = []
        current_sentence = ""
        words = new_text.split()
        
        for word in words:
            current_sentence += word + " "
            if word.endswith(('.', '!', '?')) or len(current_sentence.strip()) > 100:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        # print(f"[DEBUG] 分句结果: {len(sentences)}句子")
        # for i, s in enumerate(sentences):
            # print(f"[DEBUG] 子{i+1}: '{s}'")

        # 3. 文本显示处
        for sentence in sentences:
            if not self._is_duplicate(sentence):
                # print(f"[DEBUG] 准备显示新子: '{sentence}'")
                self.ui.root.after(0, self.ui.append_text, sentence)
            else:
                # print(f"[DEBUG] 跳过重复句子: '{sentence}'")
                pass

        self.last_processed_text = new_text
        # print("[DEBUG] ===== 文本处理完成 =====\n")

    def _is_duplicate(self, new_sentence):
        """改进的重复检测"""
        # 检查完全匹配
        if new_sentence in self.seen_fragments:
            # print(f"[DEBUG] 完全匹配重复: '{new_sentence}'")
            return True

        # 检查部分匹配
        for existing in self.seen_fragments:
            # 算相似度
            similarity = SequenceMatcher(None, new_sentence, existing).ratio()
            if similarity > 0.8:  # 提高阈值，减少误判
                # print(f"[DEBUG] 相似度重复 ({similarity:.2f}): '{new_sentence}' vs '{existing}'")
                return True
                
            # 检查包含关系
            if len(new_sentence) > len(existing):
                if existing in new_sentence:
                    # print(f"[DEBUG] 包含关系重复: '{existing}' 包含 '{new_sentence}'")
                    return True
            elif new_sentence in existing:
                # print(f"[DEBUG] 包含关系重复: '{existing}' 包含 '{new_sentence}'")
                return True

        return False

def load_config():
    try:
        config = configparser.ConfigParser(interpolation=None)
        config_path = pkg_resources.resource_filename('TikTalk', 'config.ini')
        config.read(config_path, encoding='utf-8')
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def main():
    # 在主线程中初始化COM
    pythoncom.CoInitialize()
    try:
        app = LiveCaptionUI()
        app.run()
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    main()
