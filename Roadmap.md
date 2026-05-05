# Video Notes - 專案藍圖 (Roadmap)

> 此文件記錄 Video Notes 的版本演進與未來規劃。

## 🎯 已達成目標 (Done)
- [x] v0.1: 影片下載與 FFmpeg 自動截圖。
- [x] v0.2: Whisper 逐字稿整合與 AI 片段摘要。
- [x] v0.3: 左右分欄互動介面、Glassmorphism 設計、深色模式。
- [x] v0.3.5: 優化字幕閃爍問題、更換章節圖示為數字、新增播放速度控制。
- [x] v0.3.7: 停用 OpenCV 場景檢測，優化「語義優先」截圖策略。
- [x] v0.4.0: 轉向「純語義分析」(Transcript-only)，支援一般課堂與復原圖分析分流。

## 🚀 未來規劃 (Upcoming)

### 2026 Q1: 內容強化
- [ ] **全文搜尋**: 整合 `lunr.js` 實現純前端全文檢索。
- [ ] **多格式匯出**: 支援匯出為結構化的 Markdown (For Obsidian) 或 PDF。
- [ ] **批次處理**: 定義 `manifest.json` 進行多影片排隊處理。

### 2026 Q2: 深度整合
- [ ] **Obsidian 插件化**: 直接在 Obsidian 內部讀取並嵌入影片筆記。
- [ ] **雲端同步**: 串接 Supabase 或 Firebase 存儲編輯過的 `note` 欄位。
- [ ] **視覺 OCR 增強**: 針對 PPT 或 建築施工圖進行 OCR，提取圖面文字。

## 📝 待辦事項 (Backlog)
- [ ] 修正移動端播放器高度問題。
- [ ] 增加「截圖連續播放」模式（類似快照預覽）。
- [ ] 支援多語言字幕切換。

---
*Generated at: 2026-02-19*
