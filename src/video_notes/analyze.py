"""
語義分析模組 - 使用 LLM (Ollama/Gemini/Claude) 分析逐字稿並生成標題、摘要與章節
v0.4.0 更新：
- 移除視覺分析功能 (Vision-less)
- 整合 Ollama (DeepSeek-R1) 本地分析
- 純逐字稿驅動的語義分析
"""

import yaml
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import os
import requests
import json

def analyze_frame_with_ollama(
    transcript: str,
    timestamp: str,
    project_type: str = "general",
    model: str = "gpt-oss:20b"
) -> Tuple[str, str, Optional[float], Optional[bool], Optional[str]]:
    """
    使用 Ollama 本地模型分析逐字稿
    """
    if not transcript:
        return f"{timestamp} - 無內容", "", None, None, None

    if project_type == "critique":
        prompt = f"""請分析以下建築設計評圖影片的逐字稿片段。
時間標記: {timestamp}
內容: {transcript}

請執行以下分析：
1. **識別作品/學生**：標註圖紙編號 (如 IMG_xxxx)、學生姓名。
2. **偵測分數**：記錄具體分數。
3. **過關狀態**：記錄是否及格。
4. **內容摘要**：總結老師的核心建議。請務必使用「條列式、有層次」的 Markdown 格式（使用 - 或 * 開頭，並適當換行），不要寫成一整段長文。

請「僅」以 YAML 格式輸出，若 summary 包含多行內容，請使用 `|` 來標註：
```yaml
title: "標題 (如：學生 A - 基地分析)"
summary: |
  - 第一點建議
    - 補充細節
  - 第二點建議
student: "學生姓名或圖紙編號"
score: 數字
pass: true/false
```
使用繁體中文。不要輸出任何解釋文字。"""
    else:
        prompt = f"""請分析以下教學影片的逐字稿片段。
時間標記: {timestamp}
內容: {transcript}

請執行以下分析：
1. **提取核心主題**：生成一個簡短標題。
2. **內容摘要**：總結核心知識點。請務必使用「條列式、有層次」的 Markdown 格式（例如使用 - 或 * 開頭，並適當縮排與換行），不要寫成一整段長文。

請「僅」以 YAML 格式輸出，若 summary 包含多行內容，請使用 `|` 來標註：
```yaml
title: "標題"
summary: |
  - 第一塊知識點
    - 核心細節 1
    - 核心細節 2
  - 第二塊知識點
```
使用繁體中文。不要輸出任何解釋文字。"""

    try:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        response_text = response.json().get("response", "")

        # 清洗 DeepSeek 的 <think> 標籤
        if "<think>" in response_text:
            response_text = response_text.split("</think>")[-1].strip()

        # 解析 YAML
        result = parse_yaml_from_text(response_text)
        
        return (
            result.get("title", f"{timestamp} - 分析"),
            result.get("summary", ""),
            result.get("score"),
            result.get("pass"),
            result.get("student")
        )
    except Exception as e:
        print(f"  Ollama 分析錯誤: {e}")
        return f"{timestamp} - 分析失敗", transcript[:100], None, None, None

def analyze_global_chapters(
    frames: List[Dict[str, Any]],
    model: str = "gpt-oss:20b"
) -> List[Dict[str, Any]]:
    """使用 LLM 將零散的 frames 進行大塊的章節分組"""
    if not frames:
        return []

    # 準備簡化版的 frames 資訊以節省 Token
    frame_info = []
    for i, f in enumerate(frames):
        frame_info.append(f"{i}) {f['timestamp']} - {f.get('title', '待分析')}")
    
    frame_list_str = "\n".join(frame_info)
    
    prompt = f"""請擔任資深影片剪輯師與內容架構師。
以下是從教學影片中提取的多個知識點（戳記）。目前這些點過於零散，請將它們『有意識地』歸類為 3-7 個『大章節』。

分組原則：
1. **大塊化**：避免產生過多只有 1-2 個點的小章節。
2. **主題性**：每個大章節應該代表一個完整的教學單元或邏輯段落。
3. **層次感**：章節標題應精煉且具代表性。

知識點列表：
{frame_list_str}

請僅輸出 YAML 格式的 chapters 列表，包含 title, start_index, end_index：
```yaml
chapters:
  - title: "大章節標題 1"
    start_index: 0
    end_index: 5
  - title: "大章節標題 2"
    start_index: 6
    end_index: 12
```
使用繁體中文。不要輸出任何解釋。"""

    try:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        response = requests.post(url, json=payload, timeout=40)
        response.raise_for_status()
        response_text = response.json().get("response", "")

        # 清洗 DeepSeek 的 <think> 標籤
        if "<think>" in response_text:
            response_text = response_text.split("</think>")[-1].strip()

        # 解析 YAML
        result = parse_yaml_from_text(response_text)
        return result.get("chapters", [])
    except Exception as e:
        print(f"  Ollama 全域章節分析錯誤: {e}")
        return []

def parse_yaml_from_text(text: str) -> Dict[str, Any]:
    """從模型輸出的文字中提取並解析 YAML"""
    try:
        if "```yaml" in text:
            yaml_text = text.split("```yaml")[1].split("```")[0].strip()
        elif "```" in text:
            yaml_text = text.split("```")[1].split("```")[0].strip()
        else:
            yaml_text = text.strip()
            
        return yaml.safe_load(yaml_text) or {}
    except:
        return {}

def analyze_frame_semantic(
    transcript: str,
    timestamp: str,
    project_type: str = "general",
    provider: str = "ollama",
    api_key: Optional[str] = None
) -> Tuple[str, str, str, Optional[float], Optional[bool], Optional[str]]:
    """
    僅使用逐字稿進行語義分析
    """
    if provider == "ollama":
        title, summary, score, pass_status, student = analyze_frame_with_ollama(
            transcript, timestamp, project_type
        )
        return title, summary, "", score, pass_status, student # visual_analysis 永遠為空

    # 其他 Provider (Gemini/Claude)
    if provider == "gemini":
        try:
            import google.generativeai as genai
            api_key = api_key or os.environ.get("GOOGLE_API_KEY")
            if not api_key: return f"{timestamp} - 缺失 Key", "", "", None, None, None
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
        except ImportError: return f"{timestamp} - 缺失套件", "", "", None, None, None

    elif provider == "claude":
        try:
            from anthropic import Anthropic
            api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key: return f"{timestamp} - 缺失 Key", "", "", None, None, None
            client = Anthropic(api_key=api_key)
        except ImportError: return f"{timestamp} - 缺失套件", "", "", None, None, None
    else:
        return f"{timestamp} - 錯誤 Provider", "", "", None, None, None

    # Prompt (保持一致)
    if project_type == "critique":
        prompt = f"""分析以下建築設計評圖影片的逐字稿片段。
時間標記: {timestamp}
內容: {transcript}

請執行以下分析：
1. **識別作品/學生**；2. **偵測分數**；3. **過關狀態**；4. **內容摘要**。
重點限制：內容摘要 (summary) 請務必使用「條列式、有層次」的 Markdown 格式（如 - 第一點），請勿寫成整段長文。
請以 YAML 輸出 title, summary, student, score, pass。繁體中文。若 summary 有多行請以 | 標註。"""
    else:
        prompt = f"""分析以下教學影片的逐字稿片段。
時間標記: {timestamp}
內容: {transcript}
重點要求：內容摘要 (summary) 請務必使用「條列式、有層次」的 Markdown 格式（例如使用 - 或 * 縮排與換行），切勿寫成一大段長文。
請以 YAML 輸出 title, summary。繁體中文。若 summary 有多行請以 | 標註。"""

    try:
        if provider == "gemini":
            response = model.generate_content(prompt)
            response_text = response.text
        else:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = message.content[0].text

        result = parse_yaml_from_text(response_text)
        return (
            result.get("title", f"{timestamp} - 分析"),
            result.get("summary", ""),
            "", 
            result.get("score"),
            result.get("pass"),
            result.get("student")
        )
    except Exception as e:
        print(f"  API 分析錯誤: {e}")
        return f"{timestamp} - 分析失敗", transcript[:100], "", None, None, None

def analyze_data_yaml(
    yaml_path: Path,
    provider: str = "ollama",
    api_key: Optional[str] = None,
    skip_analyzed: bool = True,
    project_type: str = "general"
) -> Path:
    """
    分析 data.yaml 中所有未分析的截圖 (純語義模式)
    """
    yaml_path = Path(yaml_path)
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    frames = data.get("frames", [])
    total = len(frames)

    print(f"🔍 開始語義分析 (Provider: {provider}, Type: {project_type})")

    for i, frame in enumerate(frames):
        if skip_analyzed and frame.get("analyzed", False):
            continue

        print(f"[{i+1}/{total}] 分析中: {frame['timestamp']}...")

        try:
            title, summary, _, score, pass_status, student = analyze_frame_semantic(
                transcript=frame.get("transcript", ""),
                timestamp=frame["timestamp"],
                project_type=project_type,
                provider=provider,
                api_key=api_key
            )

            # 更新資料
            frame["title"] = title
            frame["summary"] = summary
            frame["visual_analysis"] = "" # 移除視覺分析內容
            if score is not None: frame["score"] = score
            if pass_status is not None: frame["pass"] = pass_status
            if student: frame["student"] = student
            frame["analyzed"] = True
            frame["source"] = frame.get("source", "auto")

            print(f"  ✅ {title}")

        except Exception as e:
            print(f"  ❌ 分析失敗: {e}")
            frame["analyzed"] = False

    # 儲存更新
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\n✨ 分析完成: {yaml_path}")
    return yaml_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <data.yaml> [provider]")
        sys.exit(1)
    analyze_data_yaml(Path(sys.argv[1]), provider=sys.argv[2] if len(sys.argv) > 2 else "ollama")
