# Video Notes 系統規格書

## 版本歷程

| 版本 | 日期 | 變更 |
|------|------|------|
| 0.1.0 | 2026-02-18 | 初版：基本截圖+逐字稿對齊 |
| 0.2.0 | 進行中 | 視覺分析整合、標題生成、收摺區塊、互動式編輯 |

---

## v0.2.0 規格：智慧內容整合

### 核心需求

1. **每個時間戳記需有標題**
   - 從逐字稿或視覺分析中提取關鍵主題
   - 標題應簡潔（10-20 字）

2. **視覺分析整合**
   - 分析截圖中的視覺內容（文字、圖表、手繪）
   - 將視覺資訊與逐字稿整合成易讀的內文摘要

3. **收摺區塊**
   - 原始截圖 + 逐字稿收納在可收摺的區塊中
   - 預設收摺，需要時展開查看

---

### 資料結構 (data.yaml v2)

```yaml
video:
  title: "影片標題"
  url: "https://..."
  duration: "11:56"
  downloaded_at: "2026-02-18"

frames:
  - timestamp: "00:35"
    timestamp_seconds: 35.0
    image: "frames/00_00_35.png"

    # === v0.2.0 新增 ===
    title: "建築師考試的真相：不需要華麗表現"  # 自動生成或手動編輯
    summary: |                                    # 整合後的內文摘要
      講師分享親身經驗：帶著咖啡和蛋糕去考試，
      只用一支筆畫了 3.5 小時的草圖就通過了。
      重點不是表現法，而是解題方向的正確性。

    visual_analysis: |                            # 視覺分析結果（可收摺）
      - 畫面顯示講師正在講解
      - 無明顯板書或圖表
      - 背景為教室環境

    # === 原始內容（可收摺）===
    transcript: |
      有沒有人覺得...（原始逐字稿）

    note: ""  # 用戶筆記
```

---

### 輸出格式

#### Markdown (notes.md)

```markdown
## 00:35 - 建築師考試的真相：不需要華麗表現

講師分享親身經驗：帶著咖啡和蛋糕去考試，
只用一支筆畫了 3.5 小時的草圖就通過了。

<details>
<summary>📷 原始截圖與逐字稿</summary>

![00:35](frames/00_00_35.png)

**逐字稿：**
> 有沒有人覺得...

**視覺分析：**
- 畫面顯示講師正在講解
- 無明顯板書或圖表

</details>

---
```

#### HTML (index.html)

- 摘要區塊直接顯示
- 「查看原始內容」按鈕展開截圖+逐字稿
- 點擊時間碼跳轉 YouTube

---

### 技術實作方案

#### 方案 A：使用 LLM 進行視覺分析（推薦）

```
截圖 + 逐字稿 → LLM (多模態) → 標題 + 摘要 + 視覺分析
```

**優點：**
- 高品質的內容理解和整合
- 可自動生成有意義的標題
- 支援複雜圖表和手繪分析

**實作方式：**
- 使用 Claude API 或 OpenAI GPT-4V
- 批次處理所有截圖
- 將結果寫入 data.yaml

#### 方案 B：本地 OCR + 規則生成

```
截圖 → OCR (Tesseract) → 提取文字
逐字稿 → 關鍵字提取 → 生成標題
```

**優點：**
- 離線運作，無 API 費用
- 處理速度快

**缺點：**
- OCR 準確度有限
- 標題品質較低

---

### 開發計畫

| 階段 | 任務 | 狀態 |
|------|------|------|
| 1 | 更新 data.yaml 結構 | ✅ 完成 |
| 2 | 新增 analyze.py 模組（LLM 視覺分析） | ✅ 完成 |
| 3 | 更新 render.py（收摺區塊 + 互動式 HTML） | ✅ 完成 |
| 4 | 更新 main.py（整合分析流程） | ✅ 完成 |
| 5 | 測試與調校 | 待測試 |

---

### CLI 介面更新

```bash
# 完整處理（含視覺分析）
python -m video_notes https://youtube.com/... --analyze

# 跳過分析（僅截圖+逐字稿）
python -m video_notes https://youtube.com/...

# 對現有 data.yaml 執行分析
python -m video_notes --analyze-only projects/video_notes/VIDEO_ID/data.yaml

# 重新渲染
python -m video_notes --render-only projects/video_notes/VIDEO_ID/data.yaml
```

---

---

## v0.2.0 額外需求：互動式編輯介面

### 用戶工作流程

```
1. AI 自動處理影片 → 生成初版 data.yaml + HTML
2. 用戶在網頁介面觀看影片 + 檢視現有關鍵幀
3. 用戶手動新增關鍵幀（點擊時間軸標記）
4. 網頁介面將新標記回寫到 data.yaml
5. 下次與 AI 對話時，AI 分析新標記的幀並更新摘要
```

### HTML 介面需求

#### 1. 嵌入式影片播放器
- YouTube iframe 嵌入，支援時間碼跳轉
- 播放器下方顯示時間軸

#### 2. 互動式時間軸
```
[======●====●=======●====●=======●======]
        ↑      ↑          ↑         ↑
      00:35  01:10      02:45     04:20
      (AI)   (AI)      (手動)     (AI)
```
- 已有關鍵幀用圓點標記
- AI 生成的標記為藍色，手動新增的為綠色
- 點擊時間軸空白處可新增標記

#### 3. 新增關鍵幀功能
- 點擊時間軸 → 彈出確認框
- 輸入標題（選填）
- 點擊「新增」→ 截圖 + 寫入 data.yaml
- 標記為 `source: manual`，待 AI 分析

#### 4. 資料同步機制
- 使用 localStorage 暫存編輯
- 「匯出」按鈕生成更新後的 data.yaml
- 或提供「複製 YAML」功能讓用戶手動貼上

### data.yaml v2 結構（含手動標記）

```yaml
frames:
  - timestamp: "00:35"
    timestamp_seconds: 35.0
    image: "frames/00_00_35.png"
    source: auto              # auto | manual
    analyzed: true            # AI 是否已分析
    title: "建築師考試的核心觀念"
    summary: "..."
    transcript: "..."
    visual_analysis: "..."
    note: ""

  - timestamp: "02:45"
    timestamp_seconds: 165.0
    image: "frames/00_02_45.png"   # 待截圖
    source: manual            # 手動新增
    analyzed: false           # 尚未分析
    title: "配置圖重點"       # 用戶輸入的暫定標題
    summary: ""               # 待 AI 填入
    transcript: ""            # 待對齊
    visual_analysis: ""       # 待分析
    note: "這邊的講解很重要"  # 用戶筆記
```

### CLI 新增指令

```bash
# 分析尚未處理的手動標記
python -m video_notes --analyze-pending projects/video_notes/VIDEO_ID/data.yaml

# 為手動標記截圖（從本地影片提取）
python -m video_notes --capture-manual projects/video_notes/VIDEO_ID/data.yaml
```

---

### 待確認事項

- [x] LLM API 選擇 → 支援 Claude 和 OpenAI（--analyze-provider 參數）
- [ ] 單次分析的 token 成本估算
- [ ] 批次處理的最佳化策略
- [x] 網頁端截圖實作方式 → 手動標記後需執行 Python CLI 截圖
- [x] data.yaml 編輯的同步機制 → localStorage 暫存 + 匯出 YAML
