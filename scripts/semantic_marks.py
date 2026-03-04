"""
語義戳記模組 - 使用 LLM 分析逐字稿，找出語義轉折點

適用於：
- 講座、教學影片（講話內容比畫面更重要）
- 訪談、對話影片
"""

from pathlib import Path
from typing import List, Dict, Any
import json
import yaml

try:
    from .transcribe import parse_srt, TranscriptSegment
except ImportError:
    from transcribe import parse_srt, TranscriptSegment


def format_timestamp(seconds: float) -> str:
    """將秒數轉換為 MM:SS 格式"""
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"


def generate_semantic_prompt(segments: List[TranscriptSegment], video_title: str) -> str:
    """
    生成 LLM 分析用的 prompt

    Args:
        segments: SRT 字幕段落列表
        video_title: 影片標題

    Returns:
        prompt 字串
    """
    # 合併字幕為帶時間戳的文本
    transcript_with_time = []
    for seg in segments:
        time_str = format_timestamp(seg.start)
        transcript_with_time.append(f"[{time_str}] {seg.text}")

    full_transcript = "\n".join(transcript_with_time)

    prompt = f"""你是一位專業的影片內容分析師。請分析以下「{video_title}」的逐字稿，找出語義轉折點。

## 任務
找出影片中的**主題轉換點**，這些點代表講者開始談論新主題或新觀點的位置。

## 分析原則
1. 尋找話題轉變：講者從一個概念轉到另一個概念
2. 尋找結構標記：「首先」「其次」「另外」「接下來」等
3. 尋找問答轉折：問題或結論的開始
4. 建議每 2-5 分鐘找出 1 個轉折點

## 逐字稿（含時間戳）
{full_transcript}

## 輸出格式
請以 JSON 陣列格式輸出，每個轉折點包含：
- time: 時間戳（格式 "MM:SS"）
- seconds: 秒數（數字）
- title: 該段落的主題標題（10-20字）
- summary: 該段落的簡短摘要（30-50字）

範例：
```json
[
  {{"time": "00:00", "seconds": 0, "title": "課程介紹", "summary": "說明本次課程的目標和大綱"}},
  {{"time": "02:30", "seconds": 150, "title": "核心概念", "summary": "講解最重要的核心觀念"}}
]
```

請只輸出 JSON 陣列，不要加其他說明。"""

    return prompt


def analyze_with_claude(prompt: str) -> List[Dict[str, Any]]:
    """使用 Claude API 分析逐字稿"""
    import anthropic

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # 解析 JSON
    # 嘗試提取 JSON 區塊
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end]
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end]

    return json.loads(response_text.strip())


def generate_semantic_marks(
    project_dir: Path,
    provider: str = "claude"
) -> List[Dict[str, Any]]:
    """
    分析影片逐字稿，生成語義戳記

    Args:
        project_dir: 專案目錄（包含 subtitle.srt 和 data.yaml）
        provider: LLM 提供者 ("claude" 或 "openai")

    Returns:
        語義戳記列表
    """
    project_dir = Path(project_dir)

    # 讀取 SRT
    srt_path = project_dir / "subtitle.srt"
    if not srt_path.exists():
        raise FileNotFoundError(f"找不到字幕檔: {srt_path}")

    segments = parse_srt(srt_path)
    print(f"已載入 {len(segments)} 段字幕")

    # 讀取影片標題
    yaml_path = project_dir / "data.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    video_title = data.get("video", {}).get("title", "未命名影片")

    # 生成 prompt
    prompt = generate_semantic_prompt(segments, video_title)
    print(f"正在使用 {provider} 分析語義...")

    # 調用 LLM
    if provider == "claude":
        marks = analyze_with_claude(prompt)
    else:
        raise ValueError(f"不支援的 provider: {provider}")

    print(f"找到 {len(marks)} 個語義轉折點")
    return marks


def apply_semantic_marks(project_dir: Path, marks: List[Dict[str, Any]]) -> None:
    """
    將語義戳記應用到 data.yaml

    這會：
    1. 根據語義戳記生成新的 frames
    2. 更新 data.yaml

    Args:
        project_dir: 專案目錄
        marks: 語義戳記列表
    """
    project_dir = Path(project_dir)
    yaml_path = project_dir / "data.yaml"

    # 讀取現有資料
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 讀取 SRT 以獲取對應時間段的逐字稿
    srt_path = project_dir / "subtitle.srt"
    segments = parse_srt(srt_path) if srt_path.exists() else []

    # 建立新的 frames
    new_frames = []
    for i, mark in enumerate(marks):
        seconds = mark.get("seconds", 0)

        # 找出這個時間點附近的逐字稿
        end_seconds = marks[i + 1]["seconds"] if i + 1 < len(marks) else float('inf')
        transcript_parts = [
            seg.text for seg in segments
            if seg.start >= seconds and seg.start < end_seconds
        ]
        transcript = "\n".join(transcript_parts)

        frame = {
            "timestamp": mark.get("time", format_timestamp(seconds)),
            "timestamp_seconds": seconds,
            "title": mark.get("title", ""),
            "summary": mark.get("summary", ""),
            "transcript": transcript,
            "source": "semantic",  # 標記來源為語義分析
            "analyzed": True
        }
        new_frames.append(frame)

    # 更新資料
    data["frames"] = new_frames

    # 保存
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"已更新 data.yaml，共 {len(new_frames)} 個語義段落")


def capture_frames_for_marks(project_dir: Path) -> None:
    """
    為語義戳記截取對應的影片畫面

    Args:
        project_dir: 專案目錄
    """
    import cv2

    project_dir = Path(project_dir)
    video_path = project_dir / "video.mp4"
    frames_dir = project_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    # 讀取 data.yaml
    yaml_path = project_dir / "data.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)

    for frame_data in data.get("frames", []):
        seconds = frame_data.get("timestamp_seconds", 0)
        frame_num = int(seconds * fps)

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()

        if ret:
            # 生成檔名
            mins = int(seconds) // 60
            secs = int(seconds) % 60
            filename = f"{mins:02d}_{secs:02d}_00.png"
            image_path = frames_dir / filename

            # 保存高品質 PNG
            cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])
            frame_data["image"] = f"frames/{filename}"
            print(f"截圖: {filename}")

    cap.release()

    # 更新 data.yaml
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print("截圖完成")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用方式: python semantic_marks.py <專案目錄>")
        print("範例: python semantic_marks.py projects/video_notes/GjwJVefi_HU")
        sys.exit(1)

    project_dir = Path(sys.argv[1])

    # 1. 生成語義戳記
    marks = generate_semantic_marks(project_dir)

    # 2. 應用到 data.yaml
    apply_semantic_marks(project_dir, marks)

    # 3. 截取對應畫面
    capture_frames_for_marks(project_dir)

    print("\n語義戳記生成完成！")
