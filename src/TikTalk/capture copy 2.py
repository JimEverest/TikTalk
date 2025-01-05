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
from gpt4o import ask
import json
import configparser
from tkhtmlview import HTMLScrolledText
import markdown


cap_interval=1 #s 0.2-0.5se


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
        config.read('config.ini', encoding='utf-8')
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
        config.read('config.ini', encoding='utf-8')
        
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
        with open('config.ini', 'w', encoding='utf-8') as f:
            config.write(f)
        
        self.window.destroy()

class LiveCaptionUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Live Caption Transcript")
        # 设置最小窗口大小
        self.root.minsize(800, 500)
        
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
        
        # 创建垂直方向的PanedWindow作为主容器
        self.main_paned = ttk.PanedWindow(self.main_frame, orient=tk.VERTICAL)
        self.main_paned.grid(row=0, column=0, sticky="nsew")
        
        # 创建上部面板
        self.upper_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.upper_frame, weight=2)  # 上部分配更多空间
        
        # 创建水平方向的PanedWindow
        self.paned_window = ttk.PanedWindow(self.upper_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
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
            spacing3=5,  # 行后��白
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
        
        self.answer_text = HTMLScrolledText(
            answer_frame,
            height=6,
            font=("Microsoft YaHei UI", 10),
            html="<p>Answer will appear here...</p>"
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_buttons(self):
        # 按钮样式
        style = ttk.Style()
        style.configure('Custom.TButton', padding=5)
        
        # 创建按钮框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        
        # 开始/停止按钮
        self.start_button = ttk.Button(
            button_frame,
            text="开始捕获",
            style='Custom.TButton',
            command=self.toggle_capture
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 清空按钮
        self.clear_button = ttk.Button(
            button_frame,
            text="清空",
            style='Custom.TButton',
            command=self.clear_text
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # 复制按钮
        self.copy_button = ttk.Button(
            button_frame,
            text="复制",
            style='Custom.TButton',
            command=self.copy_text
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)
        
        # 保存按钮
        self.save_button = ttk.Button(
            button_frame,
            text="保存",
            style='Custom.TButton',
            command=self.save_text
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Ask按钮
        self.ask_button = ttk.Button(
            button_frame,
            text="Ask",
            style='Custom.TButton',
            command=self.handle_ask
        )
        self.ask_button.pack(side=tk.LEFT, padx=5)
        self.buttons['ask'] = self.ask_button
        
        # Config按钮
        self.config_button = ttk.Button(
            button_frame,
            text="Config",
            style='Custom.TButton',
            command=self.show_config
        )
        self.config_button.pack(side=tk.LEFT, padx=5)

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
        self.answer_text.set_html("<p>Answer will appear here...</p>")  # 清空答案区域
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
            # print("[DEBUG] 这是第一条文本，直接显示")
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
        # print("\n[DEBUG] ----- 开始判断是否替换 -----")
        # 检查是否包含上一行文字
        if self.last_displayed_text in new_text:
            # print(f"[DEBUG] 新文本包含上一行文本")
            # print(f"[DEBUG] 上一行: '{self.last_displayed_text}'")
            # print(f"[DEBUG] 新文本: '{new_text}'")
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
        # 获取所有文本内容
        transcript = self.text_area.get(1.0, tk.END).strip()
        jd = self.jd_text.get(1.0, tk.END).strip()
        cv = self.cv_text.get(1.0, tk.END).strip()
        notes = self.notes_text.get(1.0, tk.END).strip()
        
        # 构建prompt
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
        
        # 构建消息格式
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
                        # 将markdown转换为HTML
                        html_content = markdown.markdown(response)
                        # 显示新答案
                        self.answer_text.set_html(html_content)
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
            config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
            config.read('config.ini', encoding='utf-8')
            
            # 设置默认值
            self.default_jd = config.get('Defaults', 'default_jd', 
                fallback="111\n222\n333")
            self.default_cv = config.get('Defaults', 'default_cv', 
                fallback="333\n222\n111")
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
            
        except Exception as e:
            print(f"加载配置出错: {str(e)}")

    def show_config(self):
        """显示配置窗口"""
        config_window = ConfigWindow(self.root)
        self.root.wait_window(config_window.window)  # 等待配置窗口关闭
        
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

    def handle_line_click(self, event):
        """处理行点击事件"""
        index = self.text_area.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        
        # 记录拖动起始行
        self.drag_start_line = line_num
        
        # 如果按住Ctrl键，不清除之前的选择
        if not event.state & 0x4:  # 0x4 是Ctrl键的状态码
            self.clear_all_selections()
            
        self.toggle_line_selection(line_num)
        return "break"  # 阻止默认的文本选择

    def handle_line_drag(self, event):
        """处理拖动选择"""
        if self.drag_start_line is None:
            return "break"
            
        current_line = int(self.text_area.index(f"@{event.x},{event.y}").split('.')[0])
        
        # 清除之前的选择（除了起始行）
        self.clear_all_selections()
        
        # 选择拖动范围内的所���行
        start = min(self.drag_start_line, current_line)
        end = max(self.drag_start_line, current_line)
        
        for line in range(start, end + 1):
            self.toggle_line_selection(line, force_select=True)
            
        return "break"

    def handle_line_release(self, event):
        """处理鼠标释放"""
        self.drag_start_line = None
        return "break"

    def toggle_line_selection(self, line_num, force_select=False):
        """切换行选择状态"""
        line_start = f"{line_num}.0"
        line_end = f"{line_num}.end"
        
        # 获取行内容
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
        
        # 保存当前滚动位置
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
            
            # 添加空格（除非是最后一个词）
            if i < len(words) - 1:
                current_sentence += " "
            
            # 执行分句
            if should_split:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # 处理最后一个句子（无论是否完整都添加）
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # 如果没有任何句子，但有文本，则将整个文本作为一个句子
        if not sentences and text.strip():
            sentences.append(text.strip())
        
        return sentences

    def get_last_incomplete_sentence(self):
        """获取最后一个可能未完成的句子"""
        if not self.seen_fragments:
            return None
        last_sentence = list(self.seen_fragments)[-1]
        # 如果句子没有标准的结束符号，为是未完成的
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
            if similarity > 0.9:  # 提高相似度阈值，减少误判
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
        """新的文本处理方法"""
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
                # 保留���史文本直到公共文本结束
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
        print("\n[DEBUG] 分句结果:")
        for i, sentence in enumerate(sentences, 1):
            print(f"[{i}] {sentence}")

    def find_longest_common_substring(self, str1, str2):
        """查找两个字符串中的最长公共子串"""
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

        print("\n[DEBUG] ===== 开始新一轮文本处理 =====")
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

        # print(f"[DEBUG] 分句结果: {len(sentences)}个句子")
        # for i, s in enumerate(sentences):
            # print(f"[DEBUG] 子{i+1}: '{s}'")

        # 3. 文本显示处理
        for sentence in sentences:
            if not self._is_duplicate(sentence):
                # print(f"[DEBUG] 准备显示新句子: '{sentence}'")
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
            # 计算相似度
            similarity = SequenceMatcher(None, new_sentence, existing).ratio()
            if similarity > 0.8:  # 提高阈值，减少误判
                # print(f"[DEBUG] 相似度重复 ({similarity:.2f}): '{new_sentence}' vs '{existing}'")
                return True
                
            # 检查包含关系
            if len(new_sentence) > len(existing):
                if existing in new_sentence:
                    # print(f"[DEBUG] 包含关系重复: '{new_sentence}' 包含 '{existing}'")
                    return True
            elif new_sentence in existing:
                # print(f"[DEBUG] 包含关系重复: '{existing}' 包含 '{new_sentence}'")
                return True

        return False


if __name__ == "__main__":
    # 在主线程中初始化COM
    pythoncom.CoInitialize()
    try:
        app = LiveCaptionUI()
        app.run()
    finally:
        pythoncom.CoUninitialize()
