# Video Notes - Agent 核心開發規範 (AGENTS.md)

> 此文件定義 Video Notes 系統的技術細則、資料格式與 AI 處理流程。

## 🛠️ 技術棧 (Tech Stack)

| 元件 | 技術 |
|------|------|
| 影片下載 | yt-dlp |
| 截圖提取 | FFmpeg |
| 語音轉文字 | Whisper (openai-whisper) |
| AI 分析 | Gemini / Claude API |
| 前端頁面 | 純 HTML + CSS + Vanilla JS（無框架） |
| 資料格式 | YAML（人類可讀） + JSON（機器處理） |

## 📁 資料規格 (Data Format)

### `data.yaml` 結構
核心 SSOT 檔案，定義影片 metadata 與截圖片段分析。

```yaml
video:
  title: "影片標題"
  url: "https://www.youtube.com/watch?v=..."
  duration: "11:56"
  downloaded_at: "2026-02-18"

frames:
  - timestamp: "00:00"           # 時間點
    timestamp_seconds: 0         # 秒數
    image: "frames/00_00_00.png" # 截圖路徑
    title: "片段標題"             # AI 生成
    summary: |                   # AI 生成 (條列式)
      - 重點知識 1
        - 補充說明
      - 重點知識 2
    transcript: "原始語音轉錄..." # Whisper 輸出
    note: ""                     # 使用者筆記
    source: "semantic"           # semantic | interval | manual
    analyzed: true               # 是否已 AI 分析

chapters:                        # 章節分組
  - title: "破除表現法迷思"
    start_index: 0
    end_index: 2
```

### `transcript.json` 結構
Whisper 轉錄的原始 JSON 資料。

```json
{
  "text": "完整轉錄文字...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.4,
      "text": "好 現在這邊先聊一下",
      "avg_logprob": -0.59,
      "no_speech_prob": 0.34
    }
  ]
}
```

## 🔄 處理流程 (Workflow v0.4.0+)

1. **環境初始化**: 啟動時確認影片類型 (**一般性課堂** vs **復原圖分析**)。
2. **下載與轉錄 @ `download.py`, `transcribe.py`**: 下載影片並產出 `transcript.json`。
3. **語義截圖策略 @ `keyframes.py`, `main.py`**:
   - **停用 OpenCV 場景檢測**：改採「語義關鍵點」+「定時模式」進行截圖。
4. **AI 智慧提煉 @ `analyze.py`**:
   - **移除視覺分析 (Vision-less)**：全系統採用純逐字稿驅動的語義分析，不再使用 Vision API 以節省成本並提升速度。
   - **預設使用 Ollama (gpt-oss:20b)**：支援本地端「不需要 API Key」的語義分析。
   - **專案分流**：
     - **一般性課堂**：提取核心知識點、生成標題與摘要。
     - **復原圖分析**：識別「學生姓名」、「得分」、「過關狀態」。
5. **介面渲染 @ `render.py`**: 產出互動式 `index.html`，具備自動滾動與章節導航。
6. **編輯與回寫 (v0.4.1) @ `server.py`**:
   - 啟動伺服器：`python scripts/video_notes/server.py` (Port: 10002)。
   - 網頁端點擊 **「✏️ 編輯」** 並修改。
   - 點擊 **「💾 儲存並回寫檔案」** 將變更持久化至 `data.yaml` 並自動重新渲染網頁。
7. **索引與章節自動化 @ `index.py`, `auto_chapters.py`**: 每次處理完成後，自動更新章節資訊並刷新主索引頁。

## 🎨 UI/UX 規範
- **Liquid Glass**: 磨砂玻璃效果、磨砂邊線。
- **Editable Summaries**: 卡片摘要支援即時編輯與後端持久化回寫。
- **No Background Flicker**: 字幕應避免使用黑底背景，改用 `text-shadow` 處理。
- **Auto-Follow (v0.4.0)**: 播放時右側卡片與左側章節導航應自動隨影片進度捲動並高亮。
- **Navigation**: 確保具備返回主索引 (`../index.html`) 的導航能力。

---
*Last Updated: 2026-02-20*
