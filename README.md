# Video Notes Agent (v0.4.5)

一個基於 AI 的自動化影片筆記與分析系統。

## 🌟 功能特色
- **YouTube 下載**：自動處理任何 YouTube 影片。
- **AI 語音轉文字**：使用 Whisper 自動產生字幕。
- **智慧截圖**：根據場景變化和語意停頓自動擷取關鍵影格。
- **LLM 分析**：為每個影格產生摘要、標題及視覺分析。
- **互動式圖書庫**：網頁介面的管理中心，便於瀏覽影片收藏與筆記。

## 🚀 快速上手

### 1. 系統需求
- Python 3.10+
- `ffmpeg` (需安裝並加入 PATH)
- `yt-dlp` (專案內建或加入 PATH)
- (選配) Ollama, Gemini 或 Claude API 以進行分析。

### 2. 使用方法
- **啟動圖書庫伺服器**：
  ```bash
  python scripts/server.py
  ```
- **處理新影片**：
  ```bash
  python -m scripts "https://www.youtube.com/watch?v=VIDEO_ID"
  ```
- **更新索引系統**：
  ```bash
  python -m scripts --index
  ```

## 📂 目錄結構
- `library/`：儲存已處理影片的資料（YAML、HTML、影格截圖）。
- `scripts/`：分析、渲染與伺服器的實作程式碼。

## 📄 授權條款
MIT License
