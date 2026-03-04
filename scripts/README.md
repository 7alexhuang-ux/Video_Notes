# Video Notes - YouTube 影片筆記自動化系統

將 YouTube 教學影片自動轉換為結構化筆記，支援：
- 自動截取關鍵畫面
- 逐字稿時間碼對齊
- LLM 視覺分析（標題、摘要生成）
- 互動式 HTML 網頁（嵌入式影片、時間軸標記）

## 快速開始

### 1. 環境準備

```bash
# 安裝 Python 依賴
pip install opencv-python pyyaml jinja2

# （選用）安裝 Whisper 轉錄
pip install openai-whisper

# （選用）安裝 LLM 分析
pip install anthropic  # 或 pip install openai
```

### 2. 處理新影片

```bash
cd c:\Project\Alex_Diary\scripts

# 基本處理（截圖 + 逐字稿對齊）
python -m video_notes https://www.youtube.com/watch?v=VIDEO_ID

# 完整處理（含 AI 視覺分析）
python -m video_notes --analyze https://www.youtube.com/watch?v=VIDEO_ID
```

### 3. 查看結果

處理完成後，開啟生成的 HTML：
```
projects/video_notes/[VIDEO_ID]/index.html
```

## CLI 指令參考

### 完整處理

```bash
# 基本處理
python -m video_notes https://youtube.com/...

# 含視覺分析（需要 ANTHROPIC_API_KEY 或 OPENAI_API_KEY）
python -m video_notes --analyze https://youtube.com/...

# 使用 OpenAI 而非 Claude
python -m video_notes --analyze --analyze-provider openai https://youtube.com/...
```

### 單獨執行

```bash
# 只重新渲染（修改 data.yaml 後）
python -m video_notes --render-only projects/video_notes/VIDEO_ID/data.yaml

# 只執行視覺分析
python -m video_notes --analyze-only projects/video_notes/VIDEO_ID/data.yaml

# 只分析手動新增的標記
python -m video_notes --analyze-pending projects/video_notes/VIDEO_ID/data.yaml

# 自動生成章節分類（v0.3.0）
python -m video_notes --auto-chapters projects/video_notes/VIDEO_ID/data.yaml

# 生成影片索引頁
python -m video_notes --index
```

### 截圖參數調整

```bash
# 調整場景變化敏感度（越低越敏感，預設 0.15）
python -m video_notes --threshold 0.2 https://youtube.com/...

# 調整最小截圖間隔（秒，預設 5）
python -m video_notes --min-interval 10 https://youtube.com/...

# 使用定時截圖（每 N 秒一張）
python -m video_notes --timed-interval 30 https://youtube.com/...

# 限制最大截圖數量（預設 50）
python -m video_notes --max-frames 30 https://youtube.com/...
```

## 工作流程

```
1. 執行 CLI 處理影片
   ↓
2. 開啟 index.html 觀看影片
   ↓
3. 點擊時間軸新增手動標記（綠色圓點）
   ↓
4. 點擊「下載 data.yaml」匯出編輯
   ↓
5. 將匯出的 data.yaml 覆蓋原檔案
   ↓
6. 執行 --analyze-pending 讓 AI 分析新標記
   ↓
7. 重新開啟 index.html 查看更新
```

## 檔案結構

```
projects/video_notes/
├── index.html              # 影片索引頁（所有影片列表）
├── [VIDEO_ID_1]/
│   ├── video.mp4           # 下載的影片
│   ├── frames/             # 截圖資料夾
│   │   ├── 00_00_00.png
│   │   ├── 00_01_30.png
│   │   └── ...
│   ├── data.yaml           # 單一資料來源
│   ├── notes.md            # 生成的 Markdown
│   └── index.html          # 生成的互動式網頁
├── [VIDEO_ID_2]/
│   └── ...
```

## data.yaml 結構

```yaml
video:
  title: "影片標題"
  url: "https://www.youtube.com/watch?v=..."
  duration: "19:44"
  downloaded_at: "2026-02-18"

frames:
  - timestamp: "00:35"
    timestamp_seconds: 35.0
    image: "frames/00_00_35.png"
    source: auto              # auto = AI 自動 | manual = 手動新增
    analyzed: true            # AI 是否已分析
    title: "章節標題"
    summary: "整合後的摘要..."
    transcript: "原始逐字稿..."
    visual_analysis: "視覺分析結果..."
    note: "用戶筆記"
```

## 環境變數

```bash
# Claude API（視覺分析用）
export ANTHROPIC_API_KEY=sk-ant-...

# 或 OpenAI API
export OPENAI_API_KEY=sk-...
```

## 常見問題

### Q: 截圖數量太少？
使用定時模式：
```bash
python -m video_notes --timed-interval 30 https://youtube.com/...
```

### Q: 沒有字幕怎麼辦？
系統會自動使用 Whisper 轉錄。確保已安裝：
```bash
pip install openai-whisper
```

### Q: 視覺分析失敗？
確認已設定 API Key：
```bash
export ANTHROPIC_API_KEY=your-key-here
```

### Q: 如何修改筆記？
1. 編輯 `data.yaml` 中的 `note` 欄位
2. 執行 `python -m video_notes --render-only data.yaml`

## 版本歷程

| 版本 | 日期 | 變更 |
|------|------|------|
| 0.1.0 | 2026-02-18 | 初版：截圖 + 逐字稿對齊 |
| 0.2.0 | 2026-02-19 | 視覺分析、互動式 HTML、手動標記 |
| 0.2.1 | 2026-02-19 | 左圖右文版面：截圖左側可點擊播放、分析內容右側、逐字稿折疊 |
| 0.2.2 | 2026-02-19 | 本地影片深度整合：HTML5 播放器、進度條、鍵盤快捷鍵、右鍵新增標記 |
| 0.3.0 | 2026-02-19 | Glassmorphism UI 大改版：深淺色切換、AI 自動章節分類、Lightbox 圖片放大、懸浮播放器字幕 |
| 0.3.1 | 2026-02-19 | 左右分欄佈局：影片固定左側、卡片右側、可拖曳分隔線調整寬度 |
