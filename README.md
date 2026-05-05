# Video Notes - YouTube 影片筆記自動化系統

> **版本**: v0.4.x
> **最後更新**: 2026-05-05（從 Alex_Diary 獨立搬遷）
> **目的**: 將 YouTube 教學影片轉化為可搜尋、可編輯的結構化筆記

---

## 🚀 快速開始

### 1. 環境準備

```bash
# Python 3.10+
python --version

# 安裝依賴
pip install -r requirements.txt

# FFmpeg（截圖用）
# Windows: choco install ffmpeg
# macOS:   brew install ffmpeg
# Linux:   sudo apt install ffmpeg

# yt-dlp.exe 也可以直接下載放在專案根目錄
```

### 2. 設定 PYTHONPATH

執行套件前先設好 PYTHONPATH，讓 Python 找得到 `src/video_notes/`：

```bash
# Bash / Git Bash
export PYTHONPATH=src

# PowerShell
$env:PYTHONPATH = "src"

# CMD
set PYTHONPATH=src
```

### 3. 處理第一部影片

```bash
cd c:\Project\Video_Notes
python -m video_notes https://www.youtube.com/watch?v=YOUR_VIDEO_ID
```

### 4. 查看結果

1. 用瀏覽器開啟 `data/index.html` 查看影片索引
2. 點擊任一影片進入互動筆記頁面
3. 左側為截圖時間軸，右側為對應的轉錄與摘要

---

## 🎯 主要功能

| 功能 | 說明 |
|------|------|
| **影片下載** | 自動下載 YouTube 影片（yt-dlp） |
| **語音轉錄** | Whisper 產出逐字稿（支援中/英文） |
| **智慧截圖** | 語義關鍵點 + 定時模式產生截圖 |
| **AI 分析** | Ollama / Gemini / Claude 任選 provider |
| **互動介面** | Liquid Glass 風格網頁，可即時編輯回寫 |
| **編輯回寫** | 啟動 server.py 後可從網頁直接修改並回寫 data.yaml |

---

## 📁 目錄結構

```text
Video_Notes/
├── README.md                       # 本入口文件
├── AGENTS.md                       # 技術與開發規範（給 AI 工具）
├── Roadmap.md                      # 版本演進與待辦
├── requirements.txt                # Python 依賴
├── .env.example                    # 環境變數範本
├── .gitignore
│
├── data/                           # 影片資料根
│   ├── index.html                  # 影片索引頁（入口）
│   ├── library.yaml                # 索引 metadata
│   └── {video_id}/                 # 每部影片獨立資料夾
│       ├── index.html              # 影片筆記頁面
│       ├── data.yaml               # 核心資料 SSOT
│       ├── video.mp4               # 影片檔（不進 git）
│       ├── transcript.json         # Whisper 原始輸出
│       └── frames/                 # 截圖資料夾
│
├── src/
│   └── video_notes/                # Python 套件
│       ├── __init__.py
│       ├── __main__.py
│       ├── main.py                 # CLI 入口
│       ├── server.py               # 編輯回寫 server (port 10002)
│       ├── render.py               # HTML 渲染
│       ├── analyze.py              # LLM 語義分析
│       ├── auto_chapters.py        # 自動章節分類
│       ├── download.py             # YouTube 下載
│       ├── keyframes.py            # 截圖
│       ├── transcribe.py           # Whisper 轉錄
│       ├── align.py                # 截圖與逐字稿對齊
│       ├── index.py                # 全域索引頁產生
│       └── semantic_marks.py       # 語義關鍵點偵測
│
└── scripts/                        # 主力批次工具
    ├── batch_video_process.py      # 批次處理影片清單
    └── check_status.py             # 掃描所有影片分析狀態
```

---

## 🛠️ 常用指令

### 完整處理新影片
```bash
python -m video_notes https://youtube.com/...
python -m video_notes --analyze https://youtube.com/...   # 含 LLM 分析
```

### 編輯既有影片
```bash
# 修改 data.yaml 後重新渲染
python -m video_notes --render-only data/VIDEO_ID/data.yaml

# 補分析待處理片段
python -m video_notes --analyze-pending data/VIDEO_ID/data.yaml

# 自動章節分類
python -m video_notes --auto-chapters data/VIDEO_ID/data.yaml

# 重建全域索引
python -m video_notes --index
```

### 啟動編輯 server
```bash
python src/video_notes/server.py
# 開啟 http://localhost:10002
# 點任一影片 → ✏️ 編輯 → 💾 儲存並回寫
```

### 批次處理
```bash
python scripts/batch_video_process.py    # 跑影片清單
python scripts/check_status.py           # 看分析狀態
```

---

## 🧭 相關文件

- **技術規約**: [AGENTS.md](./AGENTS.md)
- **開發藍圖**: [Roadmap.md](./Roadmap.md)
- **套件詳細說明**: [src/video_notes/README.md](./src/video_notes/README.md)
- **資料格式規格**: [src/video_notes/SPEC.md](./src/video_notes/SPEC.md)

---

## 🎬 範例影片

- [GjwJVefi_HU/](data/GjwJVefi_HU/index.html) - 改卷方式、解題原則
- [YEmW5ITHT9A/](data/YEmW5ITHT9A/index.html) - 114U 環境分析
- [-elEsUbarUU/](data/-elEsUbarUU/index.html) - Piet Oudolf 園藝講座
- [XWfePYlK45E/](data/XWfePYlK45E/index.html) - 復原圖討論

---

## 📜 歷史

本專案於 2026-05-05 從 `c:\Project\Alex_Diary` 獨立搬遷而來。Alex_Diary 內保留 README stub 指向此處。
