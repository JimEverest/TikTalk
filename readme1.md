# Chrome Live Caption 捕获应用分析

## 应用任务

1. 实时捕获 Chrome 实时字幕窗口中的文本内容
2. 处理捕获的文本，去除重复，保持语义完整性
3. 以合适的格式在 UI 中显示处理后的文本
4. 支持保存、复制等基本功能

## 关键问题

### 1. Chrome 字幕窗口的特性

- 不是简单的增量更新模式
- 每次返回的是一个完整的文本段落（可能包含多个句子）
- 会动态修正之前的内容（如 Chimoth → Jammoth poly hapatia）
- 窗口内容是滚动的，每次捕获到的是可见部分

### 2. 文本状态管理需求

需要一个专门的 TextState 类来管理状态：

```python
class TextState:
    def __init__(self):
        self.sentences = []          # 已确认的完整句子
        self.pending_sentence = ""   # 正在处理的不完整句子
        self.last_raw_text = ""     # 上次的原始文本
        self.window_size = 2        # 关注最后N句的窗口大小
```

### 3. 当前阈值逻辑的问题

```python
# 现有的相似度判断
similarity = SequenceMatcher(None, new_sentence, existing).ratio()
if similarity > 0.9:  # 当前阈值可能过高
    return True

# 现有的长度判断
if len(new_sentence) < len(existing) * 1.5:  # 扩展倍数可能需要调整
    return True
```

### 4. 需要实验验证的问题

- Chrome 字幕窗口的更新频率（目前是 0.1s）
- 相似度阈值的最佳取值
- 句子完整性判断的标准
- 文本修正的检测范围
- 最后 N 句关注窗口的大小

## 建议的实验步骤

### 1. 基础观察

```python
def process_text(self, new_text):
    print("\n[DEBUG] Chrome原始文本:", new_text)
    print("[DEBUG] 文本长度:", len(new_text))
    print("[DEBUG] 句子数量:", len(new_text.split('.')))
```

### 2. 修正检测实验

```python
def detect_changes(self, old_text, new_text):
    # 找到第一个不同的位置
    diff_pos = -1
    for i, (c1, c2) in enumerate(zip(old_text, new_text)):
        if c1 != c2:
            diff_pos = i
            break
    
    if diff_pos != -1:
        print(f"[DEBUG] 变化位置: {diff_pos}")
        print(f"[DEBUG] 变化前文本: {old_text[max(0, diff_pos-20):diff_pos+20]}")
        print(f"[DEBUG] 变化后文本: {new_text[max(0, diff_pos-20):diff_pos+20]}")
```

### 3. 相似度阈值测试

```python
def test_similarity(self, text1, text2):
    similarity = SequenceMatcher(None, text1, text2).ratio()
    print(f"[DEBUG] 相似度: {similarity:.3f}")
    print(f"[DEBUG] 文本1: {text1}")
    print(f"[DEBUG] 文本2: {text2}")
```

## 下一步建议

1. 先不要急着改代码，而是添加更多的调试信息
2. 收集足够的样本数据，特别是出问题的场景
3. 分析 Chrome 字幕窗口的行为模式
4. 逐步调整参数，每次只改一个变量
5. 建立可靠的测试用例