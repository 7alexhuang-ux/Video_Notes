"""
對齊模組 - 將截圖與逐字稿時間碼對齊，生成 data.yaml

v0.3.0 更新：
- 支援 chapters 章節結構
- 支援逐字稿字幕時間碼
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from .keyframes import KeyFrame, timestamp_to_display
from .transcribe import TranscriptSegment, parse_srt


@dataclass
class FrameData:
    """單張截圖的完整資料 (v0.3.0)"""
    timestamp: str  # 顯示格式 HH:MM:SS
    timestamp_seconds: float
    image: str  # 相對路徑
    transcript: str
    note: str = ""  # 用戶可自行補充
    # v0.2.0 新增欄位
    title: str = ""  # 自動生成或手動編輯的標題
    summary: str = ""  # 整合後的內文摘要
    visual_analysis: str = ""  # 視覺分析結果
    source: str = "auto"  # auto | manual
    analyzed: bool = False  # AI 是否已分析


@dataclass
class ChapterData:
    """章節資料 (v0.3.0)"""
    title: str  # 章節標題
    start_index: int  # 開始的 frame 索引
    end_index: int  # 結束的 frame 索引（含）


@dataclass
class VideoData:
    """影片完整資料"""
    title: str
    url: str
    duration: str
    downloaded_at: str


def find_transcript_for_timestamp(
    timestamp: float,
    segments: List[TranscriptSegment],
    window: float = 10.0
) -> str:
    """
    找出對應時間點前後的逐字稿

    Args:
        timestamp: 截圖時間點（秒）
        segments: 逐字稿段落列表
        window: 時間窗口（秒），往前後各取多少秒的內容

    Returns:
        對應的逐字稿文字
    """
    relevant_texts = []

    for seg in segments:
        # 檢查段落是否在時間窗口內
        if seg.end >= (timestamp - window) and seg.start <= (timestamp + window):
            relevant_texts.append(seg.text)

    return "\n".join(relevant_texts)


def find_transcript_between(
    start: float,
    end: float,
    segments: List[TranscriptSegment]
) -> str:
    """
    找出兩個時間點之間的逐字稿

    Args:
        start: 開始時間（秒）
        end: 結束時間（秒）
        segments: 逐字稿段落列表

    Returns:
        對應的逐字稿文字
    """
    relevant_texts = []

    for seg in segments:
        # 段落在時間範圍內
        if seg.start >= start and seg.end <= end:
            relevant_texts.append(seg.text)
        # 段落跨越開始點
        elif seg.start < start < seg.end:
            relevant_texts.append(seg.text)
        # 段落跨越結束點
        elif seg.start < end < seg.end:
            relevant_texts.append(seg.text)

    return "\n".join(relevant_texts)


def align_keyframes_with_transcript(
    keyframes: List[KeyFrame],
    segments: List[TranscriptSegment],
    video_info: dict,
    output_dir: Path,
    segments_en: Optional[List[TranscriptSegment]] = None
) -> Path:
    """
    將截圖與逐字稿對齊，生成 data.yaml

    Args:
        keyframes: 關鍵幀列表
        segments: 逐字稿段落列表 (ZH/Primary)
        video_info: 影片資訊（標題、URL 等）
        output_dir: 輸出目錄
        segments_en: 額外的英文逐字稿段落 (EN/Secondary)
    """
    output_dir = Path(output_dir)

    # 準備影片資料
    video_data = {
        "title": video_info.get("title", "Unknown"),
        "url": video_info.get("webpage_url", video_info.get("url", "")),
        "duration": format_duration(video_info.get("duration", 0)),
        "downloaded_at": datetime.now().strftime("%Y-%m-%d"),
        "is_bilingual": segments_en is not None
    }

    # 準備幀資料
    frames_data = []
    for i, kf in enumerate(keyframes):
        # 決定這張截圖對應的時間範圍
        if i < len(keyframes) - 1:
            end_time = keyframes[i + 1].timestamp
        else:
            end_time = kf.timestamp + 30

        # 找對應的逐字稿
        transcript = find_transcript_between(kf.timestamp, end_time, segments)
        transcript_en = ""
        if segments_en:
            transcript_en = find_transcript_between(kf.timestamp, end_time, segments_en)

        # 相對路徑
        image_rel_path = f"frames/{kf.image_path.name}"

        # 預填標題
        prefilled_title = transcript.strip().split('\n')[0][:20] if transcript else ""

        frame_entry = {
            "timestamp": timestamp_to_display(kf.timestamp),
            "timestamp_seconds": round(kf.timestamp, 2),
            "image": image_rel_path,
            "transcript": transcript,
            "note": "",
            "title": prefilled_title,
            "summary": "",
            "visual_analysis": "",
            "source": "auto",
            "analyzed": False
        }
        
        if segments_en:
            frame_entry["transcript_en"] = transcript_en

        frames_data.append(frame_entry)

    # 組合完整資料 (v0.3.0 結構)
    data = {
        "video": video_data,
        "chapters": [],
        "frames": frames_data
    }

    # 儲存 YAML
    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"資料已儲存: {yaml_path}")
    return yaml_path


def save_data_yaml(yaml_path: Path, data: Dict[str, Any]) -> None:
    """儲存 data.yaml"""
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def format_duration(seconds: int) -> str:
    """將秒數轉換為 HH:MM:SS 格式"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def load_data_yaml(yaml_path: Path) -> dict:
    """載入 data.yaml"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    import sys
    print("此模組需要透過 main.py 執行")
