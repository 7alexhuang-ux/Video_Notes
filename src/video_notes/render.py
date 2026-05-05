"""
渲染模組 - 從 data.yaml 生成 Markdown 和 HTML

v0.3.0 更新：
- Glassmorphism 視覺風格
- 深淺色主題切換
- 章節目錄（可摺疊）
- 純圖片卡片 + 懸浮播放按鈕
- 懸浮小播放器（含字幕）
- Lightbox 圖片放大
"""

from pathlib import Path
import json
from jinja2 import Environment, BaseLoader
import yaml
import re
import json

# 導入 SRT 解析
try:
    from .transcribe import parse_srt
except ImportError:
    from transcribe import parse_srt


# Markdown 模板 (v0.3.0)
MARKDOWN_TEMPLATE = """# {{ video.title }}

- **來源**: [YouTube]({{ video.url }})
- **時長**: {{ video.duration }}
- **整理日期**: {{ video.downloaded_at }}

---

{% if chapters %}
## 目錄

{% for chapter in chapters %}
### {{ chapter.title }}
{% for frame in frames[chapter.start_index:chapter.end_index+1] %}
- {{ frame.timestamp }} {{ frame.title | default('') }}
{% endfor %}

{% endfor %}
---
{% endif %}

{% for frame in frames %}
## {{ frame.timestamp }} - {{ frame.title | default(frame.timestamp) }}

{{ frame.summary | default(frame.transcript) }}

{% if frame.note %}
> **筆記**: {{ frame.note }}
{% endif %}

<details>
<summary>📷 原始截圖與逐字稿</summary>

![{{ frame.timestamp }}]({{ frame.image }})

**逐字稿：**
> {{ frame.transcript | replace('\\n', '\\n> ') }}

{% if frame.visual_analysis %}
**視覺分析：**
{{ frame.visual_analysis }}
{% endif %}

</details>

---

{% endfor %}

*由 Video Notes v0.3.0 自動生成*
"""


# HTML 模板 (v0.3.2) - 左右分欄佈局 + 點擊播放 + 滿版截圖
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ video.title }}</title>
    <style>
        /* ========================================
           v0.3.2 左右分欄 + 點擊播放 + 滿版截圖
           ======================================== */

        :root {
            /* 淺色主題 (預設) */
            --bg-gradient: linear-gradient(135deg, #e8f0fe 0%, #f5e6f3 50%, #fef3e8 100%);
            --glass-bg: rgba(255, 255, 255, 0.6);
            --glass-border: rgba(255, 255, 255, 0.8);
            --glass-blur: 20px;
            --text-color: #1a1a2e;
            --text-secondary: #555;
            --accent-color: #e94560;
            --accent-light: rgba(233, 69, 96, 0.1);
            --success-color: #2ecc71;
            --shadow-soft: 0 8px 32px rgba(0, 0, 0, 0.1);
            --shadow-glow: 0 0 40px rgba(233, 69, 96, 0.1);
            --card-bg: rgba(255, 255, 255, 0.7);
            --header-bg: rgba(255, 255, 255, 0.8);
            --resizer-color: rgba(0, 0, 0, 0.1);
            --left-panel-width: 45%;
        }

        [data-theme="dark"] {
            /* 深色主題 */
            --bg-gradient: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            --glass-bg: rgba(255, 255, 255, 0.08);
            --glass-border: rgba(255, 255, 255, 0.12);
            --text-color: #eee;
            --text-secondary: #aaa;
            --accent-light: rgba(233, 69, 96, 0.15);
            --shadow-soft: 0 8px 32px rgba(0, 0, 0, 0.3);
            --shadow-glow: 0 0 40px rgba(233, 69, 96, 0.15);
            --card-bg: rgba(255, 255, 255, 0.05);
            --header-bg: rgba(22, 33, 62, 0.9);
            --resizer-color: rgba(255, 255, 255, 0.1);
        }

        .chapter-divider {
            grid-column: 1 / -1;
            padding: 40px 0 20px 0;
            margin-top: 40px;
            border-bottom: 2px solid var(--accent-color);
            position: sticky;
            top: -20px;
            background: var(--bg-gradient);
            z-index: 50;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .chapter-divider h2 {
            font-size: 1.5rem;
            font-weight: 800;
            margin: 0;
            color: var(--accent-color);
            text-shadow: 0 0 20px rgba(233, 69, 96, 0.4);
        }
        .chapter-divider .chapter-range {
            font-size: 0.8rem;
            background: rgba(255,255,255,0.1);
            padding: 4px 12px;
            border-radius: 99px;
            color: var(--text-secondary);
        }

        .frame-chapter-breadcrumb {
            font-size: 0.75rem;
            color: var(--accent-color);
            margin-bottom: 4px;
            font-weight: 600;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .star-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.2rem;
            filter: grayscale(1);
            opacity: 0.3;
            transition: all 0.2s;
            margin-right: 8px;
            vertical-align: middle;
        }
        .star-btn.active {
            filter: grayscale(0);
            opacity: 1;
            transform: scale(1.1);
        }
        .star-btn:hover {
            opacity: 0.8;
            transform: scale(1.2);
        }

        /* Editor Styles */
        .summary-editor {
            width: 100%;
            min-height: 150px;
            padding: 12px;
            background: var(--card-bg);
            border: 1px solid var(--accent-color);
            border-radius: 8px;
            color: var(--text-color);
            font-size: 0.95rem;
            font-family: inherit;
            line-height: 1.7;
            resize: vertical;
            display: none;
            margin-bottom: 10px;
            outline: none;
            box-shadow: 0 0 10px var(--accent-light);
        }

        .edit-controls {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            display: none;
        }

        .save-btn {
            background: var(--success-color);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .save-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(46, 204, 113, 0.3);
        }

        .edit-toggle-btn {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.75rem;
            transition: all 0.2s ease;
        }

        .edit-toggle-btn:hover {
            border-color: var(--accent-color);
            color: var(--accent-color);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html, body {
            height: 100%;
            overflow: hidden;
        }

        body {
            font-family: 'Segoe UI', 'Microsoft JhengHei', -apple-system, sans-serif;
            background: var(--bg-gradient);
            background-attachment: fixed;
            color: var(--text-color);
            line-height: 1.6;
        }

        /* ========================================
           主容器 - 左右分欄
           ======================================== */

        .main-container {
            display: flex;
            height: 100vh;
            width: 100%;
        }

        /* 左側面板 - 影片 + 時間軸 */
        .left-panel {
            width: var(--left-panel-width);
            min-width: 300px;
            max-width: 70%;
            height: 100%;
            display: flex;
            flex-direction: column;
            background: var(--header-bg);
            backdrop-filter: blur(var(--glass-blur));
            -webkit-backdrop-filter: blur(var(--glass-blur));
            border-right: 1px solid var(--glass-border);
        }

        /* 可拖曳分隔線 */
        .resizer {
            width: 8px;
            cursor: col-resize;
            background: var(--resizer-color);
            flex-shrink: 0;
            transition: background 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .resizer:hover, .resizer.dragging {
            background: var(--accent-color);
        }

        .resizer::after {
            content: '';
            width: 2px;
            height: 40px;
            background: var(--text-secondary);
            border-radius: 2px;
            opacity: 0.5;
        }

        .resizer:hover::after, .resizer.dragging::after {
            background: white;
            opacity: 1;
        }

        /* 右側面板 - 卡片流 */
        .right-panel {
            flex: 1;
            height: 100%;
            overflow-y: auto;
            padding: 20px;
        }

        /* ========================================
           左側面板內容
           ======================================== */

        .video-header {
            padding: 15px 20px;
            background: var(--glass-bg);
            border-bottom: 1px solid var(--glass-border);
        }

        .video-header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .video-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex: 1;
            margin-right: 12px;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }

        .theme-toggle {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 5px 10px;
            cursor: pointer;
            font-size: 0.8rem;
            color: var(--text-color);
            display: flex;
            align-items: center;
            gap: 4px;
            transition: all 0.3s ease;
        }

        .theme-toggle:hover {
            background: var(--accent-light);
            border-color: var(--accent-color);
        }

        .youtube-link {
            color: var(--text-secondary);
            font-size: 0.8rem;
            text-decoration: none;
        }

        .youtube-link:hover {
            color: var(--accent-color);
        }

        .back-link {
            text-decoration: none;
            font-size: 1.2rem;
            background: var(--glass-bg);
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            border: 1px solid var(--glass-border);
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .back-link:hover {
            transform: scale(1.1);
            background: var(--accent-color);
            border-color: var(--accent-color);
            color: white;
            box-shadow: 0 4px 15px rgba(233, 69, 96, 0.3);
        }

        /* 影片區域 */
        .video-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #000;
            position: relative;
            min-height: 0;
        }

        .video-area video {
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: #000;
        }

        /* 字幕 */
        .subtitle-display {
            position: absolute;
            bottom: 40px;
            left: 0;
            right: 0;
            text-align: center;
            padding: 10px 20px;
            color: white;
            font-size: 1.1rem;
            font-weight: 500;
            line-height: 1.4;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            /* 使用文字陰影替代黑底，避免閃爍感 */
            text-shadow: 
                -1.5px -1.5px 0 #000,  
                 1.5px -1.5px 0 #000,
                -1.5px  1.5px 0 #000,
                 1.5px  1.5px 0 #000,
                 0px 2px 4px rgba(0,0,0,0.8);
            z-index: 100;
        }

        .subtitle-display.visible {
            opacity: 1;
        }

        /* 時間軸區域 */
        .timeline-area {
            padding: 15px 20px;
            background: var(--glass-bg);
            border-top: 1px solid var(--glass-border);
        }

        .timeline-controls {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }

        .play-btn {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--accent-color);
            border: none;
            color: white;
            font-size: 1.1rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            box-shadow: 0 4px 15px rgba(233, 69, 96, 0.3);
        }

        .play-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(233, 69, 96, 0.4);
        }

        .mark-btn {
            background: var(--success-color);
            border: none;
            color: white;
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 15px rgba(46, 204, 113, 0.3);
        }

        .mark-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(46, 204, 113, 0.4);
        }

        .time-display {
            font-family: monospace;
            font-size: 0.9rem;
            color: var(--text-color);
            min-width: 100px;
        }

        .volume-control {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-left: auto;
        }

        .volume-control input {
            width: 80px;
            accent-color: var(--accent-color);
        }

        /* 時間軸軌道 */
        .timeline-track {
            height: 12px;
            background: var(--glass-bg);
            border-radius: 6px;
            position: relative;
            cursor: pointer;
            border: 1px solid var(--glass-border);
        }

        .timeline-progress {
            height: 100%;
            background: var(--accent-color);
            border-radius: 6px;
            width: 0%;
            transition: width 0.1s linear;
        }

        .timeline-marker {
            position: absolute;
            top: 50%;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--accent-color);
            border: 2px solid white;
            transform: translate(-50%, -50%);
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.55rem;
            font-weight: bold;
            color: white;
        }

        .timeline-marker:hover {
            transform: translate(-50%, -50%) scale(1.3);
            z-index: 20;
        }

        .timeline-marker.manual {
            background: var(--success-color);
        }

        .timeline-marker.starred {
            background: #fbbf24; /* Star gold */
            border-color: #fff;
            box-shadow: 0 0 10px rgba(251, 191, 36, 0.8);
            z-index: 15;
        }

        .timeline-marker.active {
            transform: translate(-50%, -50%) scale(1.5);
            box-shadow: 0 0 0 3px var(--accent-light), 0 2px 8px rgba(0,0,0,0.2);
        }

        /* 章節目錄 */
        .chapter-nav {
            max-height: 280px;
            overflow-y: auto;
            padding: 12px 20px;
            background: var(--card-bg);
            border-top: 1px solid var(--glass-border);
        }

        .chapter-nav h3 {
            font-size: 0.9rem;
            color: var(--accent-color);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .chapter-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .chapter-item {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            overflow: hidden;
        }

        .chapter-header {
            padding: 8px 12px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            transition: all 0.2s ease;
        }

        .chapter-header:hover {
            background: var(--accent-light);
        }

        .chapter-title {
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .chapter-count {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .chapter-arrow {
            font-size: 0.8rem;
            transition: transform 0.2s ease;
        }

        .chapter-item.open .chapter-arrow {
            transform: rotate(180deg);
        }

        .chapter-frames {
            display: none;
            padding: 0 12px 8px;
        }

        .chapter-item.open .chapter-frames {
            display: block;
        }

        .chapter-frame-link {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            margin: 2px 0;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            color: var(--text-color);
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .chapter-frame-link:hover,
        .chapter-frame-link.active {
            background: var(--accent-light);
        }

        .chapter-frame-link.active {
            border-left: 3px solid var(--accent-color);
        }

        .chapter-frame-id {
            font-family: monospace;
            font-size: 0.7rem;
            font-weight: bold;
            color: white;
            background: var(--accent-color);
            padding: 2px 6px;
            border-radius: 4px;
            min-width: 28px;
            text-align: center;
        }

        .chapter-frame-time {
            font-family: monospace;
            font-size: 0.75rem;
            color: var(--text-secondary);
            padding: 2px 4px;
        }

        .link-title {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .mini-score {
            font-size: 0.65rem;
            font-weight: bold;
            padding: 1px 4px;
            border-radius: 3px;
            min-width: 24px;
            text-align: center;
        }

        .mini-score.pass { background: var(--success-color); color: white; }
        .mini-score.fail { background: var(--accent-color); color: white; }

        .chapter-frame-link.frame-passed { border-right: 3px solid var(--success-color); }
        .chapter-frame-link.frame-failed { border-right: 3px solid var(--accent-color); }

        /* ========================================
           右側面板 - 卡片流
           ======================================== */

        .frame-card {
            background: var(--card-bg);
            backdrop-filter: blur(var(--glass-blur));
            -webkit-backdrop-filter: blur(var(--glass-blur));
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: var(--shadow-soft);
            transition: all 0.3s ease;
        }

        .frame-card:hover {
            box-shadow: var(--shadow-soft), var(--shadow-glow);
        }

        .frame-card.active {
            border-color: var(--accent-color);
            box-shadow: 0 0 0 2px var(--accent-color), var(--shadow-soft);
        }

        .frame-header {
            padding: 14px 18px;
            background: var(--glass-bg);
            border-bottom: 1px solid var(--glass-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }

        .frame-title {
            font-size: 1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .frame-number {
            background: var(--accent-color);
            color: white;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 0.75rem;
            font-weight: bold;
        }

        .frame-badges {
            display: flex;
            gap: 6px;
            align-items: center;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }

        .badge.auto { 
            background: linear-gradient(135deg, rgba(155, 89, 182, 0.3), rgba(155, 89, 182, 0.1)); 
            border-color: rgba(155, 89, 182, 0.4);
            color: #d2a8ff;
        }

        .badge.manual { 
            background: linear-gradient(135deg, rgba(233, 69, 96, 0.3), rgba(233, 69, 96, 0.1)); 
            border-color: rgba(233, 69, 96, 0.4);
            color: #ff9fb1;
        }

        .badge.analyzed { 
            background: linear-gradient(135deg, rgba(46, 204, 113, 0.3), rgba(46, 204, 113, 0.1)); 
            border-color: rgba(46, 204, 113, 0.4);
            color: #85ffc7;
        }

        .student-tag {
            margin-top: 10px;
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid var(--accent-color);
            border-radius: 4px;
            font-size: 0.9rem;
            color: var(--text-color);
        }

        .student-tag strong {
            color: var(--accent-light);
            margin-left: 5px;
        }

        /* 卡片主體 */
        .frame-body {
            display: grid;
            grid-template-columns: 55% 1fr;
            gap: 0;
        }

        @media (max-width: 1200px) {
            .frame-body {
                grid-template-columns: 1fr;
            }
        }

        /* 左側圖片區 */
        .frame-image-area {
            padding: 0;
            display: flex;
            flex-direction: column;
            background: var(--glass-bg);
        }

        .image-wrapper {
            position: relative;
            width: 100%;
            height: 100%;
            flex: 1;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .image-wrapper:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }

        .image-wrapper img {
            width: 100%;
            height: auto;
            object-fit: contain;
            display: block;
        }

        .play-overlay {
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            opacity: 0;
            transform: translateY(8px);
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(233, 69, 96, 0.4);
        }

        .image-wrapper:hover .play-overlay {
            opacity: 1;
            transform: translateY(0);
        }

        .zoom-hint {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.6);
            color: white;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.7rem;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .image-wrapper:hover .zoom-hint {
            opacity: 1;
        }

        .frame-timestamp {
            position: absolute;
            bottom: 10px;
            left: 10px;
            font-family: monospace;
            font-size: 0.85rem;
            color: white;
            background: rgba(0,0,0,0.7);
            padding: 4px 10px;
            border-radius: 4px;
            z-index: 5;
        }

        /* 右側分析區 */
        .frame-analysis {
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .analysis-section h4 {
            color: var(--accent-color);
            font-size: 0.9rem;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .analysis-summary {
            font-size: 0.95rem;
            line-height: 1.7;
            color: var(--text-color);
        }

        .analysis-visual {
            background: var(--accent-light);
            border-left: 3px solid var(--accent-color);
            padding: 12px 16px;
            border-radius: 0 10px 10px 0;
        }

        .analysis-visual p, .analysis-visual div {
            font-size: 0.85rem;
            line-height: 1.6;
            color: var(--text-secondary);
        }

        .user-note {
            background: rgba(46, 204, 113, 0.1);
            border-left: 3px solid var(--success-color);
            padding: 12px 16px;
            border-radius: 0 10px 10px 0;
        }

        .user-note h5 {
            color: var(--success-color);
            margin-bottom: 6px;
            font-size: 0.85rem;
        }

        /* 逐字稿折疊區 */
        .transcript-toggle {
            border-top: 1px solid var(--glass-border);
        }

        .transcript-toggle summary {
            padding: 12px 18px;
            cursor: pointer;
            font-size: 0.85rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .transcript-toggle summary:hover {
            background: var(--glass-bg);
            color: var(--text-color);
        }

        .transcript-content {
            padding: 15px;
            background: var(--glass-bg);
        }

        .transcript-text {
            background: var(--card-bg);
            padding: 15px;
            border-radius: 10px;
            white-space: pre-wrap;
            font-size: 0.85rem;
            line-height: 1.7;
            color: var(--text-secondary);
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid var(--glass-border);
        }

        /* 雙語模式樣式 */
        .zh-lang, .en-lang { display: block; margin-bottom: 8px; }
        .zh-lang { color: var(--text-color); font-weight: 500; }
        .en-lang { color: var(--text-secondary); opacity: 0.8; font-family: 'Inter', sans-serif; }
        
        body.sub-mode-zh .en-lang { display: none; }
        body.sub-mode-en .zh-lang { display: none; }
        body.sub-mode-bilingual .en-lang { border-top: 1px solid var(--glass-border); padding-top: 8px; margin-top: 8px; }

        /* ========================================
           Lightbox 圖片放大
           ======================================== */

        .lightbox {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }

        .lightbox.active {
            display: flex;
        }

        .lightbox img {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
            border-radius: 8px;
        }

        .lightbox-close {
            position: absolute;
            top: 20px;
            right: 30px;
            color: white;
            font-size: 2.5rem;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.3s;
        }

        .lightbox-close:hover {
            opacity: 1;
        }

        .lightbox-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            color: white;
            font-size: 3rem;
            cursor: pointer;
            padding: 20px;
            opacity: 0.7;
            transition: opacity 0.3s;
        }

        .lightbox-nav:hover {
            opacity: 1;
        }

        .lightbox-prev { left: 20px; }
        .lightbox-next { right: 20px; }

        .lightbox-info {
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            color: white;
            text-align: center;
            background: rgba(0,0,0,0.6);
            padding: 10px 20px;
            border-radius: 25px;
        }

        /* ========================================
           Footer
           ======================================== */

        .right-panel footer {
            text-align: center;
            padding: 30px 20px;
            color: var(--text-secondary);
            font-size: 0.8rem;
        }

        .right-panel footer a {
            color: var(--accent-color);
            text-decoration: none;
        }

        /* ========================================
           響應式 - 小螢幕改為上下佈局
           ======================================== */

        @media (max-width: 900px) {
            .main-container {
                flex-direction: column;
            }

            .left-panel {
                width: 100% !important;
                min-width: unset;
                max-width: unset;
                height: 50vh;
            }

            .resizer {
                display: none;
            }

            .right-panel {
                height: 50vh;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- 左側面板：影片 + 時間軸 -->
        <div class="left-panel" id="leftPanel">
            <!-- 標題列 -->
            <div class="video-header">
                <div class="video-header-top">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <a href="../index.html" class="back-link" title="回主索引">🏠</a>
                        <h1 class="video-title">{{ video.title }}</h1>
                    </div>
                    <div class="header-controls">
                        <a href="{{ video.url }}" target="_blank" class="youtube-link">📺 YouTube</a>
                        <button class="theme-toggle" onclick="toggleTheme()">
                            <span id="themeIcon">🌙</span>
                            <span id="themeText">深色</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- 影片區域 -->
            <div class="video-area">
                <video id="mainVideo" controls preload="metadata" poster="{{ frames[0].image if frames else '' }}">
                    <source src="video.mp4" type="video/mp4">
                </video>
                <div class="subtitle-display" id="subtitleDisplay"></div>
            </div>

            <!-- 時間軸控制 -->
            <div class="timeline-area">
                <div class="timeline-controls">
                    <button class="play-btn" id="playBtn" onclick="togglePlay()">▶</button>
                    <span class="time-display">
                        <span id="currentTime">00:00</span> / {{ video.duration }}
                    </span>
                    
                    <!-- 播放速度調整 -->
                    <div class="speed-control" style="display: flex; align-items: center; gap: 5px; margin-left: 10px;">
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">⚡</span>
                        <select id="speedSelector" onchange="setPlaybackRate(this.value)" style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 4px; color: var(--text-color); font-size: 0.8rem; padding: 2px 5px; cursor: pointer;">
                            <option value="0.5">0.5x</option>
                            <option value="0.75">0.75x</option>
                            <option value="1" selected>1.0x</option>
                            <option value="1.25">1.25x</option>
                            <option value="1.5">1.5x</option>
                            <option value="2">2.0x</option>
                        </select>
                    </div>

                    {% if video.is_bilingual %}
                    <!-- 字幕切換 -->
                    <div class="subtitle-control" style="display: flex; align-items: center; gap: 5px; margin-left: 10px;">
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">💬</span>
                        <select id="subModeSelector" onchange="setSubtitleMode(this.value)" style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 4px; color: var(--text-color); font-size: 0.8rem; padding: 2px 5px; cursor: pointer;">
                            <option value="bilingual" selected>中英對照</option>
                            <option value="zh">純中文</option>
                            <option value="en">純英文</option>
                        </select>
                    </div>
                    {% endif %}

                    <button class="mark-btn" id="markBtn" onclick="addManualMark()" title="按 M 鍵添加手動戳記" style="margin-left: 10px;">
                        📍 戳記
                    </button>
                    <div class="volume-control">
                        <span>🔊</span>
                        <input type="range" id="volumeSlider" min="0" max="1" step="0.1" value="1" onchange="setVolume(this.value)">
                    </div>
                </div>
                <div class="timeline-track" id="timelineTrack" onclick="handleTimelineClick(event)">
                    <div class="timeline-progress" id="timelineProgress"></div>
                    {% for frame in frames %}
                    <div class="timeline-marker {{ frame.source | default('auto') }} {{ 'starred' if frame.starred else '' }}"
                         id="marker-{{ loop.index }}"
                         style="left: {{ (frame.timestamp_seconds / duration_seconds * 100) | round(2) }}%"
                         onclick="event.stopPropagation(); jumpToFrame({{ loop.index }}, {{ frame.timestamp_seconds }}, findChapterForFrame({{ loop.index }}))"
                         title="{{ frame.chapter_id | default(loop.index) }}: {{ frame.timestamp }} - {{ frame.title | default('') }}">
                        {{ frame.chapter_id | default(loop.index) }}
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- 章節目錄 -->
            {% if chapters %}
            <div class="chapter-nav">
                <h3>📑 章節目錄</h3>
                <div class="chapter-list">
                    {% for chapter in chapters %}
                    <div id="chapter-item-{{ loop.index }}" class="chapter-item {{ 'open' if loop.index == 1 else '' }}">
                        <div class="chapter-header" onclick="toggleChapter({{ loop.index }})">
                            <span class="chapter-title">
                                <span class="chapter-number">{{ loop.index }}.</span>
                                {{ chapter.title | replace(loop.index ~ '.', '') | trim }}
                            </span>
                            <span class="chapter-count">{{ chapter.end_index - chapter.start_index + 1 }}</span>
                            <span class="chapter-arrow">▼</span>
                        </div>
                        <div class="chapter-frames" data-chapter-index="{{ loop.index }}">
                            {% for i in range(chapter.start_index, [chapter.end_index + 1, frames|length]|min) %}
                            {% set frame = frames[i] %}
                            <a class="chapter-frame-link {{ 'frame-passed' if frame.score and frame.score >= 60 else ('frame-failed' if frame.score and frame.score < 60 else '') }}" href="#frame-{{ i + 1 }}" data-frame-index="{{ i + 1 }}" onclick="jumpToFrame({{ i + 1 }}, {{ frame.timestamp_seconds }}, this.closest('.chapter-frames').dataset.chapterIndex); return false;">
                                <span class="chapter-frame-id">{{ frame.chapter_id }}</span>
                                <span class="chapter-frame-time">{{ frame.timestamp }}</span>
                                <span class="link-title">{{ frame.title | default('待分析', true) | truncate(30) }}</span>
                                {% if frame.score %}
                                <span class="mini-score {{ 'pass' if frame.score >= 60 else 'fail' }}">{{ frame.score }}</span>
                                {% endif %}
                            </a>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>

        <!-- 可拖曳分隔線 -->
        <div class="resizer" id="resizer"></div>

        <!-- 右側面板：卡片流 -->
        <div class="right-panel" id="rightPanel">
            {% set ns = namespace(current_chapter_idx=-1) %}
            {% for frame in frames %}
            
            {# 檢測是否進入新章節 #}
            {% set frame_idx = loop.index - 1 %}
            {% set found_chapter = none %}
            {% for ch in chapters %}
                {% if frame_idx >= ch.start_index and frame_idx <= ch.end_index %}
                    {% set found_chapter = ch %}
                    {% set ch_idx = loop.index %}
                {% endif %}
            {% endfor %}

            {% if found_chapter and ns.current_chapter_idx != ch_idx %}
                <div class="chapter-divider" id="chapter-anchor-{{ ch_idx }}">
                    <h2>CAP {{ ch_idx }}. {{ found_chapter.title }}</h2>
                    <span class="chapter-range">點位 {{ found_chapter.start_index + 1 }} - {{ found_chapter.end_index + 1 }}</span>
                </div>
                {% set ns.current_chapter_idx = ch_idx %}
            {% endif %}

            <section class="frame-card" id="frame-{{ loop.index }}" data-timestamp="{{ frame.timestamp_seconds }}">
                <div class="frame-header">
                    <div style="display: flex; flex-direction: column;">
                        {% if found_chapter %}
                        <div class="frame-chapter-breadcrumb">CHAPTER {{ ch_idx }} / {{ found_chapter.title }}</div>
                        {% endif %}
                        <h3 class="frame-title">
                            <span class="frame-number">{{ frame.chapter_id | default(loop.index) }}</span>
                            {% if frame.title %}
                            {{ frame.title }}
                            {% else %}
                            <span style="opacity: 0.5;">待分析</span>
                            {% endif %}
                        </h3>
                    </div>
                    <div class="frame-badges">
                        <button class="star-btn {{ 'active' if frame.starred else '' }}" id="star-{{ loop.index - 1 }}" onclick="toggleStar({{ loop.index - 1 }})" title="標記為重點">⭐</button>
                        <span class="badge {{ frame.source | default('auto') }}">{{ '手動' if frame.source == 'manual' else '自動' }}</span>
                        {% if frame.analyzed %}
                        <span class="badge analyzed">✓ 已分析</span>
                        {% endif %}
                        {% if frame.score is defined %}
                        <span class="badge {{ 'score-pass' if frame.score >= 60 else 'score-fail' }}">
                            🎯 得分: {{ frame.score }} {{ ' (及格)' if frame.score >= 60 else ' (未過關)' }}
                        </span>
                        {% endif %}
                    </div>
                </div>

                <div class="frame-body">
                    <!-- 左側圖片 - 滿版 -->
                    <div class="frame-image-area">
                        <div class="image-wrapper" onclick="openLightbox({{ loop.index - 1 }})">
                            {% if frame.image %}
                            <img src="{{ frame.image }}" alt="{{ frame.timestamp }}" loading="lazy">
                            <span class="zoom-hint">🔍 點擊放大</span>
                            <span class="frame-timestamp">{{ frame.timestamp }}</span>
                            {% else %}
                            <div style="background: var(--glass-bg); padding: 60px 15px; text-align: center; color: var(--text-secondary); height: 100%; display: flex; align-items: center; justify-content: center;">
                                📷 待截圖
                            </div>
                            {% endif %}
                            <button class="play-overlay" onclick="event.stopPropagation(); jumpToTimeAndPlay({{ frame.timestamp_seconds }})">
                                ▶ 播放
                            </button>
                        </div>
                    </div>

                    <!-- 右側分析 -->
                    <div class="frame-analysis">
                        {% if frame.summary %}
                        <div class="analysis-section">
                            <h4 style="display: flex; justify-content: space-between; align-items: center;">
                                <span>📝 內容摘要</span>
                                <button class="edit-toggle-btn" onclick="toggleEdit({{ loop.index - 1 }})">✏️ 編輯</button>
                            </h4>
                            <div class="analysis-summary" id="summary-display-{{ loop.index - 1 }}">{{ frame.summary | replace('\n', '<br>') | safe }}</div>
                            <textarea class="summary-editor" id="summary-editor-{{ loop.index - 1 }}">{{ frame.summary }}</textarea>
                            <div class="edit-controls" id="edit-controls-{{ loop.index - 1 }}">
                                <button class="save-btn" id="save-btn-{{ loop.index - 1 }}" onclick="saveSummary({{ loop.index - 1 }})">💾 儲存並回寫檔案</button>
                                <button class="save-btn" style="background: var(--text-secondary);" onclick="toggleEdit({{ loop.index - 1 }})">取消</button>
                            </div>
                            
                            {% if frame.student %}
                            <div class="student-tag">
                                👤 學生作品: <strong>{{ frame.student }}</strong>
                            </div>
                            {% endif %}
                        </div>
                        {% endif %}

                        {% if frame.note %}
                        <div class="user-note">
                            <h5>📌 我的筆記</h5>
                            <p>{{ frame.note }}</p>
                        </div>
                        {% endif %}

                        {% if not frame.summary %}
                        <div style="color: var(--text-secondary); font-style: italic; font-size: 0.9rem;">
                            尚未進行語義分析。請確認 Ollama 已啟動後執行 <code>--analyze-only</code>。
                        </div>
                        {% endif %}
                    </div>
                </div>

                <!-- 逐字稿 -->
                {% if frame.transcript %}
                <details class="transcript-toggle">
                    <summary>📜 展開逐字稿</summary>
                    <div class="transcript-content">
                        <div class="transcript-text">
                            <div class="zh-lang">{{ frame.transcript }}</div>
                            {% if frame.transcript_en %}
                            <div class="en-lang">{{ frame.transcript_en }}</div>
                            {% endif %}
                        </div>
                    </div>
                </details>
                {% endif %}
            </section>
            {% endfor %}

            <footer>
                Video Notes v0.3.2 |
                <a href="#" onclick="document.getElementById('rightPanel').scrollTo({top:0, behavior:'smooth'}); return false;">回到頂部</a>
            </footer>
        </div>
    </div>

    <!-- Lightbox -->
    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <span class="lightbox-close" onclick="closeLightbox()">&times;</span>
        <span class="lightbox-nav lightbox-prev" onclick="event.stopPropagation(); prevImage()">❮</span>
        <img id="lightboxImg" src="" alt="">
        <span class="lightbox-nav lightbox-next" onclick="event.stopPropagation(); nextImage()">❯</span>
        <div class="lightbox-info" id="lightboxInfo"></div>
    </div>
    
    <!-- Data Islands for Safer JSON Injection -->
    <script id="data-video" type="application/json">{{ data_json | safe }}</script>
    <script id="data-subtitle-zh" type="application/json">{{ subtitle_json | safe }}</script>
    <script id="data-subtitle-en" type="application/json">{{ subtitle_en_json | safe }}</script>

    <script>
        // ========================================
        // Video Notes v0.3.4 - Safer Data Loading
        // ========================================
        
        console.log("Script starting...");
        window.onerror = function(message, source, lineno, colno, error) {
            console.error("Global JS Error:", message, "at", source, ":", lineno, ":", colno);
        };

        // Initialize variables
        let videoData = {};
        let durationSeconds = 0;
        let frames = [];
        let chapters = [];
        let subtitleSegments = [];
        let subtitleEnSegments = [];

        try {
            console.log('Step 1: Parsing Video Data');
            const rawData = document.getElementById('data-video').textContent;
            if (rawData) {
                 videoData = JSON.parse(rawData);
            }
            durationSeconds = {{ duration_seconds | default(0) }};
            frames = videoData.frames || [];
            chapters = videoData.chapters || [];
            console.log('Step 1 Done: Frames', frames.length);
        } catch (e) {
            console.error('Error parsing video data:', e);
            // Fallback
            durationSeconds = 0;
            frames = [];
        }

        try {
            console.log('Step 2: Parsing Subtitles');
            subtitleSegments = JSON.parse(document.getElementById('data-subtitle-zh').textContent);
            subtitleEnSegments = JSON.parse(document.getElementById('data-subtitle-en').textContent);
            console.log('Step 2 Done: Subs loaded');
        } catch (e) { console.error('Error parsing subtitles:', e); }

        const mainVideo = document.getElementById('mainVideo');
        const subtitleDisplay = document.getElementById('subtitleDisplay');

        // Lightbox
        let currentImageIndex = 0;
        const images = frames.map(f => f.image).filter(Boolean);

        // 根據 frame index 找到對應章節
        window.findChapterForFrame = function(frameIndex) {
            for (let i = 0; i < chapters.length; i++) {
                const ch = chapters[i];
                if (frameIndex >= ch.start_index + 1 && frameIndex <= ch.end_index + 1) {
                    return i + 1;  // 章節編號從 1 開始
                }
            }
            return null;
        };

        // ========================================
        // 可拖曳分隔線
        // ========================================

        // ========================================
        // 可拖曳分隔線
        // ========================================
        
        try {
            const resizer = document.getElementById('resizer');
            const leftPanel = document.getElementById('leftPanel');
            let isResizing = false;

            if (resizer && leftPanel) {
                resizer.addEventListener('mousedown', (e) => {
                    isResizing = true;
                    resizer.classList.add('dragging');
                    document.body.style.cursor = 'col-resize';
                    document.body.style.userSelect = 'none';
                });

                document.addEventListener('mousemove', (e) => {
                    if (!isResizing) return;

                    const containerWidth = document.body.clientWidth;
                    const newWidth = (e.clientX / containerWidth) * 100;

                    // 限制範圍 25% - 75%
                    if (newWidth >= 25 && newWidth <= 75) {
                        leftPanel.style.width = newWidth + '%';
                    }
                });

                document.addEventListener('mouseup', () => {
                    if (isResizing) {
                        isResizing = false;
                        resizer.classList.remove('dragging');
                        document.body.style.cursor = '';
                        document.body.style.userSelect = '';

                        // 儲存寬度偏好
                        localStorage.setItem('leftPanelWidth', leftPanel.style.width);
                    }
                });
                
                // 載入寬度偏好
                const savedWidth = localStorage.getItem('leftPanelWidth');
                if (savedWidth) {
                    leftPanel.style.width = savedWidth;
                }
            }
        } catch (e) { console.error("Resizer init error:", e); }

        // ========================================
        // 主題切換
        // ========================================

        window.toggleTheme = function() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);

            document.getElementById('themeIcon').textContent = newTheme === 'dark' ? '☀️' : '🌙';
            document.getElementById('themeText').textContent = newTheme === 'dark' ? '淺色' : '深色';

            localStorage.setItem('theme', newTheme);
        };

        // 載入主題偏好
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        if (savedTheme === 'dark') {
            document.getElementById('themeIcon').textContent = '☀️';
            document.getElementById('themeText').textContent = '淺色';
        }

        // ========================================
        // 影片控制
        // ========================================

        window.togglePlay = function() {
            if (mainVideo.paused) {
                mainVideo.play();
            } else {
                mainVideo.pause();
            }
        };

        window.setVolume = function(value) {
            mainVideo.volume = value;
        };

        window.setPlaybackRate = function(rate) {
            mainVideo.playbackRate = parseFloat(rate);
        };

        window.handleTimelineClick = function(event) {
            const track = event.currentTarget;
            const rect = track.getBoundingClientRect();
            const percent = (event.clientX - rect.left) / rect.width;
            mainVideo.currentTime = percent * durationSeconds;
        };

        window.jumpToTimeAndPlay = function(seconds) {
            if (mainVideo) {
                mainVideo.currentTime = seconds;
                mainVideo.play().catch(e => console.error("Play failed:", e));
            }
        };

        // 影片事件
        mainVideo.addEventListener('play', () => {
            document.getElementById('playBtn').textContent = '⏸';
        });

        mainVideo.addEventListener('pause', () => {
            document.getElementById('playBtn').textContent = '▶';
        });

        mainVideo.addEventListener('timeupdate', () => {
            const percent = (mainVideo.currentTime / durationSeconds) * 100;
            document.getElementById('timelineProgress').style.width = percent + '%';

            const mins = Math.floor(mainVideo.currentTime / 60);
            const secs = Math.floor(mainVideo.currentTime % 60);
            document.getElementById('currentTime').textContent =
                mins.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');

            // 更新字幕
            updateSubtitle(mainVideo.currentTime);

            // 高亮當前標記
            highlightCurrentMarker(mainVideo.currentTime);
        });

        // 字幕功能 - 支援多語言與切換模式
        window.updateSubtitle = function(currentTime) {
            let subtitleZh = '';
            let subtitleEn = '';

            // 1. 讀取 ZH 字幕
            if (subtitleSegments && subtitleSegments.length > 0) {
                for (const seg of subtitleSegments) {
                    if (currentTime >= seg.start && currentTime < seg.end) {
                        subtitleZh = seg.text;
                        break;
                    }
                }
            }

            // 2. 讀取 EN 字幕
            if (subtitleEnSegments && subtitleEnSegments.length > 0) {
                for (const seg of subtitleEnSegments) {
                    if (currentTime >= seg.start && currentTime < seg.end) {
                        subtitleEn = seg.text;
                        break;
                    }
                }
            }

            // 3. 後備邏輯：如果沒 SRT，從 frame 逐字稿取 (ZH)
            if (!subtitleZh && !subtitleEn) {
                for (let i = 0; i < frames.length; i++) {
                    const frame = frames[i];
                    const startTime = frame.timestamp_seconds;
                    const endTime = (i + 1 < frames.length) ? frames[i + 1].timestamp_seconds : durationSeconds;

                    if (currentTime >= startTime && currentTime < endTime && frame.transcript) {
                        const sentences = frame.transcript.split(/\\n+/).filter(s => s.trim());
                        if (sentences.length > 0) {
                            const segmentDuration = endTime - startTime;
                            const timeInSegment = currentTime - startTime;
                            const sentenceIndex = Math.min(
                                Math.floor((timeInSegment / segmentDuration) * sentences.length),
                                sentences.length - 1
                            );
                            subtitleZh = sentences[sentenceIndex].trim();
                        }
                        break;
                    }
                }
            }

            // 4. 根據模式組合顯示內容
            let displayHtml = '';
            const mode = typeof currentSubMode !== 'undefined' ? currentSubMode : 'bilingual';

            if (mode === 'bilingual') {
                if (subtitleZh) displayHtml += `<div class="sub-zh">${subtitleZh}</div>`;
                if (subtitleEn) displayHtml += `<div class="sub-en" style="font-size: 0.8em; opacity: 0.8; margin-top: 4px; font-style: italic;">${subtitleEn}</div>`;
            } else if (mode === 'zh') {
                displayHtml = subtitleZh;
            } else if (mode === 'en') {
                displayHtml = subtitleEn;
            }

            if (displayHtml) {
                subtitleDisplay.innerHTML = displayHtml;
                subtitleDisplay.classList.add('visible');
            } else {
                subtitleDisplay.classList.remove('visible');
            }
        }

        // 高亮當前標記
        function highlightCurrentMarker(currentTime) {
            document.querySelectorAll('.timeline-marker').forEach(m => m.classList.remove('active'));

            let activeFrameIndex = -1;
            for (let i = 0; i < frames.length; i++) {
                const frame = frames[i];
                const startTime = frame.timestamp_seconds;
                const endTime = (i + 1 < frames.length) ? frames[i + 1].timestamp_seconds : durationSeconds;

                if (currentTime >= startTime && currentTime < endTime) {
                    const marker = document.getElementById('marker-' + (i + 1));
                    if (marker) marker.classList.add('active');
                    activeFrameIndex = i + 1;
                    break;
                }
            }

            // v0.4.0: 自動跟隨 (Auto-scroll)
            if (activeFrameIndex !== -1) {
                // 1. 滾動卡片 (僅當該卡片不在視窗內或切換時)
                const card = document.getElementById('frame-' + activeFrameIndex);
                if (card && window.lastAutoScrollFrame !== activeFrameIndex) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    window.lastAutoScrollFrame = activeFrameIndex;
                    
                    // 高亮卡片感
                    document.querySelectorAll('.frame-card').forEach(c => c.classList.remove('active'));
                    card.classList.add('active');
                }

                // 2. 滾動章節導覽
                const chapterIdx = window.findChapterForFrame(activeFrameIndex);
                if (chapterIdx !== null && window.lastAutoScrollChapter !== chapterIdx) {
                    const chapterItem = document.getElementById('chapter-item-' + chapterIdx);
                    if (chapterItem) {
                        // 展開章節
                        chapterItem.classList.add('open');
                        window.lastAutoScrollChapter = chapterIdx;
                        
                        // 高亮章節內連結
                        document.querySelectorAll('.chapter-frame-link').forEach(link => {
                            link.classList.toggle('active', parseInt(link.dataset.frameIndex) === activeFrameIndex);
                        });

                        // 讓章節項捲動到可見區域
                        chapterItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                } else if (chapterIdx !== null) {
                    // 即使章節相同，也要高亮對應的連結
                    document.querySelectorAll('.chapter-frame-link').forEach(link => {
                        link.classList.toggle('active', parseInt(link.dataset.frameIndex) === activeFrameIndex);
                    });
                }
            }
        }

        // ========================================
        // 章節目錄
        // ========================================

        // Expose functions to global scope - DEFINED EARLY
        window.toggleChapter = function(index) {
            console.log('Toggling chapter:', index);
            const item = document.getElementById('chapter-item-' + index);
            if (item) {
                item.classList.toggle('open');
            } else {
                console.error('Chapter item not found:', index);
            }
        };

        window.jumpToFrame = function(index, seconds, chapterIndex) {
            // 跳轉影片
            const v = document.getElementById('mainVideo');
            if (v) {
                if (typeof seconds === 'number' && !isNaN(seconds)) {
                    v.currentTime = seconds;
                }
            }

            // 滾動到卡片
            const card = document.getElementById('frame-' + index);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'start' });

                // 高亮卡片
                document.querySelectorAll('.frame-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
                setTimeout(() => card.classList.remove('active'), 2000);
            }
            
            // 展開並高亮對應章節
            if (chapterIndex) {
                const chapIdx = parseInt(chapterIndex);
                if (!isNaN(chapIdx)) {
                    // 關閉其他章節，展開當前章節
                    document.querySelectorAll('.chapter-item').forEach(item => {
                        if (item.id === 'chapter-item-' + chapIdx) {
                            item.classList.add('open');
                        }
                    });

                    // 高亮章節中對應的連結
                    document.querySelectorAll('.chapter-frame-link').forEach(link => {
                        link.classList.remove('active');
                        if (parseInt(link.dataset.frameIndex) === index) {
                            link.classList.add('active');
                        }
                    });
                }
            }
        };

        // ========================================
        // Initializers
        // ========================================

        try {
             // 確保 chapters 存在
             if (typeof chapters === 'undefined') chapters = [];
        } catch(e) { console.error("Init vars error", e); }


        // ========================================
        // 卡片跳轉
        // ========================================

        // Previously defined jumpToFrame here, now moved up.


        // ========================================
        // Lightbox
        // ========================================

        function openLightbox(index) {
            currentImageIndex = index;
            const frame = frames[index];
            if (!frame || !frame.image) return;

            document.getElementById('lightboxImg').src = frame.image;
            document.getElementById('lightboxInfo').textContent =
                `${frame.timestamp} - ${frame.title || '截圖 ' + (index + 1)} (${index + 1}/${frames.length})`;
            document.getElementById('lightbox').classList.add('active');
        }

        function closeLightbox() {
            document.getElementById('lightbox').classList.remove('active');
        }

        function prevImage() {
            currentImageIndex = (currentImageIndex - 1 + frames.length) % frames.length;
            while (!frames[currentImageIndex].image && currentImageIndex > 0) {
                currentImageIndex--;
            }
            openLightbox(currentImageIndex);
        }

        function nextImage() {
            currentImageIndex = (currentImageIndex + 1) % frames.length;
            while (!frames[currentImageIndex].image && currentImageIndex < frames.length - 1) {
                currentImageIndex++;
            }
            openLightbox(currentImageIndex);
        }

        // ========================================
        // 手動戳記功能
        // ========================================

        // 從 localStorage 載入手動戳記
        const videoId = '{{ video_id }}';
        let manualMarks = JSON.parse(localStorage.getItem('manualMarks_' + videoId) || '[]');

        // 初始化：渲染已保存的手動戳記
        function renderManualMarks() {
            // 移除舊的手動戳記
            document.querySelectorAll('.timeline-marker.user-manual').forEach(m => m.remove());

            // 添加新的手動戳記
            const track = document.getElementById('timelineTrack');
            manualMarks.forEach((mark, idx) => {
                const marker = document.createElement('div');
                marker.className = 'timeline-marker manual user-manual';
                marker.style.left = (mark.time / durationSeconds * 100) + '%';
                marker.title = 'M' + (idx + 1) + ': ' + formatTime(mark.time) + ' (手動)';
                marker.textContent = 'M' + (idx + 1);
                marker.onclick = (e) => {
                    e.stopPropagation();
                    mainVideo.currentTime = mark.time;
                };
                // 右鍵刪除
                marker.oncontextmenu = (e) => {
                    e.preventDefault();
                    if (confirm('刪除此手動戳記？')) {
                        manualMarks.splice(idx, 1);
                        saveManualMarks();
                        renderManualMarks();
                    }
                };
                track.appendChild(marker);
            });
        }

        function saveManualMarks() {
            localStorage.setItem('manualMarks_' + videoId, JSON.stringify(manualMarks));
        }

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return mins.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');
        }

        function addManualMark() {
            const currentTime = mainVideo.currentTime;
            // 檢查是否已有相近的戳記（5秒內）
            const tooClose = manualMarks.some(m => Math.abs(m.time - currentTime) < 5);
            if (tooClose) {
                alert('此位置已有戳記（5秒內）');
                return;
            }
            manualMarks.push({ time: currentTime, created: Date.now() });
            manualMarks.sort((a, b) => a.time - b.time);
            saveManualMarks();
            renderManualMarks();

            // 視覺反饋
            const btn = document.getElementById('markBtn');
            btn.style.transform = 'scale(1.2)';
            setTimeout(() => btn.style.transform = '', 200);
        }

        // 初始化手動戳記
        renderManualMarks();

        // ========================================
        // 鍵盤快捷鍵
        // ========================================

        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch(e.key) {
                case 'Escape':
                    closeLightbox();
                    break;
                case 'ArrowLeft':
                    if (document.getElementById('lightbox').classList.contains('active')) {
                        prevImage();
                    } else {
                        mainVideo.currentTime = Math.max(0, mainVideo.currentTime - 5);
                    }
                    break;
                case 'ArrowRight':
                    if (document.getElementById('lightbox').classList.contains('active')) {
                        nextImage();
                    } else {
                        mainVideo.currentTime = Math.min(durationSeconds, mainVideo.currentTime + 5);
                    }
                    break;
                case ' ':
                    e.preventDefault();
                    togglePlay();
                    break;
                case 'm':
                case 'M':
                    addManualMark();
                    break;
            }
        });

        // 字幕切換模式
        let currentSubMode = 'bilingual';

        window.setSubtitleMode = function(mode) {
            currentSubMode = mode;
            document.body.classList.remove('sub-mode-zh', 'sub-mode-en', 'sub-mode-bilingual');
            document.body.classList.add('sub-mode-' + mode);
            localStorage.setItem('alex_diary_video_sub_mode', mode);

            // Update the selector value if it exists
            const selector = document.getElementById('subModeSelector');
            if (selector) selector.value = mode;
        }

        // 初始化模式
        function initSubMode() {
            const savedMode = localStorage.getItem('alex_diary_video_sub_mode') || 'bilingual';
            window.setSubtitleMode(savedMode); // Call the main setter function
        }

        window.addEventListener('DOMContentLoaded', () => {
            initSubMode();
        });

        // ========================================
        // 編輯摘要功能 (v0.4.1)
        // ========================================

        window.toggleEdit = function(index) {
            const display = document.getElementById('summary-display-' + index);
            const editor = document.getElementById('summary-editor-' + index);
            const controls = document.getElementById('edit-controls-' + index);
            
            const isEditing = editor.style.display === 'block';
            
            if (isEditing) {
                display.style.display = 'block';
                editor.style.display = 'none';
                controls.style.display = 'none';
            } else {
                display.style.display = 'none';
                editor.style.display = 'block';
                controls.style.display = 'flex';
                editor.style.height = 'auto';
                editor.style.height = (editor.scrollHeight + 10) + 'px';
                editor.focus();
            }
        };

        window.saveSummary = function(index) {
            const videoId = document.getElementById('data-video') ? JSON.parse(document.getElementById('data-video').textContent).video.url.split('v=')[1].split('&')[0] : 'unknown';
            const newSummary = document.getElementById('summary-editor-' + index).value;
            const saveBtn = document.getElementById('save-btn-' + index);
            
            const originalText = saveBtn.textContent;
            saveBtn.textContent = '⌛ 儲存中...';
            saveBtn.disabled = true;

            // 預設打向本機 server
            fetch('http://localhost:10002/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_id: videoId,
                    frame_index: index,
                    summary: newSummary
                })
            })
            .then(res => {
                if (!res.ok) throw new Error('伺服器錯誤: ' + res.status);
                return res.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    saveBtn.textContent = '✅ 已存檔';
                    saveBtn.style.background = '#27ae60';
                    setTimeout(() => {
                        location.reload(); // 重新整理以載入重新渲染後的 HTML
                    }, 500);
                } else {
                    alert('儲存失敗: ' + (data.error || '未知錯誤'));
                    saveBtn.textContent = originalText;
                    saveBtn.disabled = false;
                }
            })
            .catch(err => {
                console.error(err);
                alert('伺服器連線失敗！\\n請回終端機檢查 python scripts/video_notes/server.py 是否正在運行。');
                saveBtn.textContent = originalText;
                saveBtn.disabled = false;
            });
        };

        window.toggleStar = function(index) {
            const btn = document.getElementById('star-' + index);
            const isActive = btn.classList.toggle('active');
            
            // 同步更新時間軸上的標記顏色 (注意模板中是 1-indexed)
            const marker = document.getElementById('marker-' + (index + 1));
            if (marker) {
                marker.classList.toggle('starred', isActive);
            }

            const videoId = document.getElementById('data-video') ? JSON.parse(document.getElementById('data-video').textContent).video.url.split('v=')[1].split('&')[0] : 'unknown';
            
            fetch('http://localhost:10002/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_id: videoId,
                    frame_index: index,
                    starred: isActive
                })
            });
        };

        console.log('Video Notes v0.4.1 - Script execution complete');
    </script>
</body>
</html>
"""


def extract_video_id(url: str) -> str:
    """從 YouTube URL 提取影片 ID"""
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def parse_duration_to_seconds(duration: str) -> int:
    """將時間字串轉換為秒數"""
    parts = duration.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def render_markdown(data: dict, output_path: Path):
    """從資料生成 Markdown 文件"""
    env = Environment(loader=BaseLoader())
    template = env.from_string(MARKDOWN_TEMPLATE)
    content = template.render(**data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Markdown 已生成: {output_path}")


def render_html(data: dict, output_path: Path):
    """從資料生成 HTML 文件"""
    output_path = Path(output_path)
    project_dir = output_path.parent

    # 提取影片 ID 和時長
    video_url = data.get("video", {}).get("url", "")
    video_id = extract_video_id(video_url)
    duration_str = data.get("video", {}).get("duration", "00:00")
    duration_seconds = parse_duration_to_seconds(duration_str)

    # 讀取 SRT 字幕檔 (ZH 優先)
    srt_zh_path = project_dir / "subtitle_zh.srt"
    if not srt_zh_path.exists():
        srt_zh_path = project_dir / "subtitle.srt"
    
    subtitle_segments = []
    if srt_zh_path.exists():
        try:
            segments = parse_srt(srt_zh_path)
            subtitle_segments = [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in segments
            ]
            print(f"已載入 ZH 字幕: {len(subtitle_segments)} 段")
        except Exception as e:
            print(f"ZH 字幕載入失敗: {e}")

    # 讀取 SRT 字幕檔 (EN)
    srt_en_path = project_dir / "subtitle_en.srt"
    subtitle_en_segments = []
    if srt_en_path.exists():
        try:
            segments_en = parse_srt(srt_en_path)
            subtitle_en_segments = [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in segments_en
            ]
            print(f"已載入 EN 字幕: {len(subtitle_en_segments)} 段")
        except Exception as e:
            print(f"EN 字幕載入失敗: {e}")

    # 確保 chapters 存在
    if "chapters" not in data:
        data["chapters"] = []

    # 計算每個 frame 的章節編號 (如 1-1, 1-2, 2-1)
    chapters = data.get("chapters", [])
    frames = data.get("frames", [])

    if chapters:
        # 有章節時，按章節編號
        for chapter_idx, chapter in enumerate(chapters):
            start_idx = chapter.get("start_index", 0)
            end_idx = chapter.get("end_index", len(frames) - 1)
            frame_in_chapter = 0
            for i in range(start_idx, min(end_idx + 1, len(frames))):
                frame_in_chapter += 1
                frames[i]["chapter_id"] = f"{chapter_idx + 1}-{frame_in_chapter}"
    else:
        # 無章節時，直接用序號
        for i, frame in enumerate(frames):
            frame["chapter_id"] = str(i + 1)

    # 準備模板變數
    template_data = {
        **data,
        "video_id": video_id,
        "duration_seconds": duration_seconds,
        "data_json": json.dumps(data, ensure_ascii=False).replace("<script>", "<\\script>"),
        "subtitle_json": json.dumps(subtitle_segments, ensure_ascii=False).replace("<script>", "<\\script>"),
        "subtitle_en_json": json.dumps(subtitle_en_segments, ensure_ascii=False).replace("<script>", "<\\script>")
    }

    env = Environment(loader=BaseLoader())
    template = env.from_string(HTML_TEMPLATE)
    content = template.render(**template_data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"HTML 已生成: {output_path}")


def render_all(yaml_path: Path):
    """
    從 data.yaml 生成所有輸出檔案

    Args:
        yaml_path: data.yaml 的路徑
    """
    yaml_path = Path(yaml_path)
    output_dir = yaml_path.parent

    # 載入資料
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 生成 Markdown
    md_path = output_dir / "notes.md"
    render_markdown(data, md_path)

    # 生成 HTML
    html_path = output_dir / "index.html"
    render_html(data, html_path)

    return md_path, html_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使用方式: python render.py <data.yaml 路徑>")
        sys.exit(1)

    yaml_path = Path(sys.argv[1])
    render_all(yaml_path)
