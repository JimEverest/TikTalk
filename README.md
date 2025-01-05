# Live Caption Assistant

## Overview
This project is a sophisticated desktop application designed to capture, process, and analyze live captions with integrated AI assistance capabilities. It's particularly useful for interview scenarios, meetings, and other situations requiring real-time caption analysis.

## Key Features

### 1. Live Caption Capture
- Real-time capture of Chrome's Live Caption window
- Intelligent text deduplication and sentence processing
- Automatic text formatting and display

```594:671:capture.py
class LiveCaptionCapture:
    def __init__(self, ui):
        self.ui = ui
        self.running = False
        self.last_text = ""
        self.seen_fragments = set()
        self.current_sentence = ""  # 添加这行来跟踪当前正在构建的句子

    def find_caption_window(self):
        try:
            caption_window = auto.WindowControl(searchDepth=1, ClassName='Chrome_WidgetWin_1', SubName='Live Caption')
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
                return doc_control.Name
            return None
        except Exception as e:
            self.ui.status_var.set(f"获取文本错误: {str(e)}")
            return None

    def process_text(self, new_text):
        if not new_text:
            return

        # 将文本按句子分割，但保持完整性
        sentences = new_text.split('. ')
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # 如果不是最后一个句子，添加句号
            if i < len(sentences) - 1:
                sentence = sentence + "."

            # 如果是新的句子且不在已见集合中
            if sentence and sentence not in self.seen_fragments:
                self.seen_fragments.add(sentence)
                # 使用 after 方法在主线程中更新UI
                self.ui.root.after(0, self.ui.append_text, sentence)

        # 限制已见片段集合的大小
        if len(self.seen_fragments) > 100:
            self.seen_fragments.clear()
    def start_capture(self):
        self.running = True
        self.ui.root.after(0, self.ui.status_var.set, "开始捕获...")
        
        while self.running:
            try:
                window = self.find_caption_window()
                if window:
                    text = self.get_caption_text(window)
                    if text:
                        self.process_text(text)
                else:
                    time.sleep(3)
                    continue
                
                time.sleep(0.1)
                
            except Exception as e:
                self.ui.root.after(0, self.ui.status_var.set, f"发生错误: {str(e)}")
                time.sleep(1)

    def stop_capture(self):
        self.running = False
        self.ui.root.after(0, self.ui.status_var.set, "已停止捕获")
```


### 2. AI-Powered Analysis
- Integration with multiple AI models including:
  - o1-all
  - o1-mini
  - gpt-4o
  - claude-3-5-sonnet
  - o1-preview
  - o1-pro-all
- Contextual analysis of conversations
- Bilingual response generation (Chinese/English)

### 3. User Interface
- Modern Tkinter-based GUI with:
  - Split-pane layout
  - Real-time transcript display
  - Configurable input panels for JD, CV, and Notes
  - Response panel for AI analysis

```121:181:capture.py
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
        self.text_area = scrolledtext.ScrolledText(
            self.left_frame, 
            wrap=tk.WORD,
            width=40,
            height=20,
            font=("Microsoft YaHei UI", 10)
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # 创建右侧文本框
        self.create_right_panels()
        
        # 创建下部答案面板
        self.lower_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.lower_frame, weight=1)  # 下部分配较少空间
        
        # 创建答案文本框
        self.create_answer_panel()
        
```


### 4. Configuration Management
- Flexible configuration system using INI format
- Customizable shortcuts
- Persistent settings storage

```1:51:config.ini
[GenAI]
model = o1-mini
openai_token = 
openai_token_url = 
openai_health_url = 
openai_mm_url = 
openai_chat_url = 
openai_user_name = 
openai_password = 
openai_application_id = 
openai_application_name = 
head_token_key = Authorization

[Prompts]
summarize_prompt = Summarize the current state of the meeting based on the following transcript, considering the meeting topic, goals, and background. Provide a concise overview of key points discussed and any decisions made. \n** Transcript** : {transcript}\n ** Meeting Topic **: {meeting_topic}\n** Meeting Goals:**  {meeting_goals}\n ** Background** : {background}\n ** Output  Language: **  {language}
viewpoints_prompt = Summarize each participant·s main points from the transcript , Highlight key ideas from key Stakeholders\n Transcript: {transcript}\n Meeting Topic: {meeting_topic}\n Meeting Goals: {meeting_goals}\n Key Stakeholders {key_stakeholders}\n Output Language: {language}
navigate_prompt = Based on the meeting topic, goals, transcript, and {user_name}·s stance, suggest the next statement for {user_name} should make to navigate the meeting effectively. Consider:communication skills, technical understanding, decision-making, leadership, strategic thinking, adaptability, and stakeholder management.\n  Transcript: {transcript}\n  Meeting Topic: {meeting_topic}\n  Meeting Goals: {meeting_goals}  \n Key Stakeholders: {key_stakeholders}  \n User Name: {user_name}\n Output Language: {language}\nNotes: {notes}
minutes_prompt = Convert the following transcript into a formal meeting minutes document, including key points, decisions, and action items etc.   please try to keep the output concise and to the point. try to compile the output in a way that is easy to read and understand， write in header + paragraphs rather than bullet points alone. Ensure clarity and structure align with standard meeting minutes format.\n Transcript: {transcript}\n Meeting Topic: {meeting_topic}\n Meeting Goals: {meeting_goals}\n Output Language: {language}

[Shortcuts]
hotkey_snip = <shift>+a+s
hotkey_paint = <ctrl>+p
hotkey_text = <ctrl>+t
hotkey_screenpen_toggle = <ctrl>+<cmd>+<alt>
hotkey_undo = <ctrl>+z
hotkey_redo = <ctrl>+y
hotkey_screenpen_exit = <esc>
hotkey_screenpen_clear_hide = <ctrl>+<esc>
hotkey_topmost_on = <esc>+`
hotkey_topmost_off = <cmd>+<shift>+\
hotkey_opacity_down = <left>+<right>+<down>
hotkey_opacity_up = <left>+<right>+<up>
hotkey_ask_dialog_key = <ctrl>
hotkey_ask_dialog_count = 4
hotkey_ask_dialog_time_window = 1.0

[Defaults]
duration = 30min
username = Jim
language = En
live_freq = 30
notification_showtime = 4
context = Please input meeting context...
agenda = Please input meeting agenda/target...
topics = Please input meeting topics...
stakeholders = Please input key stakeholders...
notes = Please input meeting notes...
default_jd = 1111111
default_cv = 22222
default_notes = NA

```


## Technical Architecture

### Core Components

1. **LiveCaptionUI**
   - Main application window handler
   - Manages UI components and event loops
   - Handles user interactions and display updates

2. **LiveCaptionCapture**
   - Manages caption window detection and text extraction
   - Implements intelligent text processing
   - Handles COM initialization for Windows UI Automation

3. **ConfigWindow**
   - Configuration management interface
   - Model selection and default text management
   - Settings persistence

4. **GPT Integration**
   - Custom API client for AI model interaction
   - Support for multiple model endpoints
   - Robust error handling and response processing

## Setup and Dependencies

### Required Packages

```1:6:requirements.txt
uiautomation
tkinter
pyperclip
pythoncom
difflib

```


### Configuration
The application requires a `config.ini` file with the following sections:
- GenAI: AI model configuration
- Prompts: System prompt templates
- Shortcuts: Keyboard shortcut definitions
- Defaults: Default values and settings

## Usage

1. **Starting the Application**
```python
from capture import LiveCaptionUI

app = LiveCaptionUI()
app.run()
```

2. **Basic Operations**
- Start/Stop Capture: Toggles live caption capture
- Clear: Clears all text fields
- Copy: Copies all content to clipboard
- Save: Saves transcript and analysis to file
- Ask: Triggers AI analysis of current content

3. **Configuration**
- Access through the Config button
- Select AI model
- Configure default texts for JD, CV, and Notes
- Save settings for persistence

## Technical Details

### Text Processing Algorithm
The application uses a sophisticated text processing system that:
- Removes duplicates using sequence matching
- Maintains sentence integrity
- Handles partial updates

```622:643:capture.py
    def process_text(self, new_text):
        if not new_text:
            return

        # 将文本按句子分割，但保持完整性
        sentences = new_text.split('. ')
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # 如果不是最后一个句子，添加句号
            if i < len(sentences) - 1:
                sentence = sentence + "."

            # 如果是新的句子且不在已见集合中
            if sentence and sentence not in self.seen_fragments:
                self.seen_fragments.add(sentence)
                # 使用 after 方法在主线程中更新UI
                self.ui.root.after(0, self.ui.append_text, sentence)

```


### AI Integration
The system implements a robust AI communication layer that:
- Handles authentication
- Manages API endpoints
- Processes responses

```31:46:gpt4o.py
def ask(msgs):
    # 检查OPENAI_TOKEN是否已经存在

    print("~"*100)
    print(msgs)
    print("~"*100)
    
    _token = ""
    
    if OPENAI_TOKEN and OPENAI_TOKEN.strip():  # 优先从环境变量中取token
        _token = "Bearer " + OPENAI_TOKEN
    else:
        # 如果没有找到环境变量中的token，尝试通过get_token获取
        _token = get_token()
    resp = ask_with_msgs(_token, msgs)
    return resp
```


## Development Notes

### Threading Model
- Main UI thread for interface operations
- Separate capture thread for COM operations
- Queue-based communication between threads

```576:593:capture.py
class CaptureThread(threading.Thread):
    def __init__(self, capturer):
        super().__init__()
        self.capturer = capturer
        self.daemon = True

    def run(self):
        try:
            # ���线程中初始化COM
            pythoncom.CoInitialize()
            # 初始化UI Automation
            auto.InitializeUIAutomationInCurrentThread()
            # 动捕获
            self.capturer.start_capture()
        finally:
            # 清理COM
            pythoncom.CoUninitialize()
```


### Error Handling
- Robust exception handling for UI operations
- Graceful degradation for API failures
- User feedback through status bar updates

## Future Enhancements
1. Support for additional AI models
2. Enhanced text processing algorithms
3. Multiple language support
4. Advanced configuration options
5. Plugin system for extensibility

## Contributing
Contributions are welcome! Please ensure:
1. Code follows existing style
2. New features include appropriate tests
3. Documentation is updated
4. Pull requests include description of changes

## License
This project is licensed under the MIT License - see the LICENSE file for details.
