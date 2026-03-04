"""
轉錄模組 - 使用 Whisper 將影片音訊轉換為逐字稿
"""

import subprocess
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import json
import re


@dataclass
class TranscriptSegment:
    """逐字稿段落"""
    start: float  # 開始時間（秒）
    end: float    # 結束時間（秒）
    text: str     # 文字內容


def detect_gpu_vram() -> Optional[int]:
    """檢測 GPU VRAM（GB），若無 GPU 回傳 None"""
    try:
        import torch
        if torch.cuda.is_available():
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            return vram_bytes // (1024 ** 3)
    except ImportError:
        pass
    return None


def select_whisper_model(model_name: str = "auto") -> str:
    """
    選擇 Whisper 模型

    Args:
        model_name: 模型名稱或 "auto"

    Returns:
        選擇的模型名稱
    """
    models = {
        "tiny": 1,      # ~1 GB VRAM
        "base": 1,      # ~1 GB VRAM
        "small": 2,     # ~2 GB VRAM
        "medium": 5,    # ~5 GB VRAM
        "large-v3": 10  # ~10 GB VRAM
    }

    if model_name != "auto":
        if model_name in models:
            return model_name
        raise ValueError(f"未知的模型: {model_name}。可用: {list(models.keys())}")

    # 自動選擇
    vram = detect_gpu_vram()
    if vram is None:
        print("未檢測到 GPU，使用 CPU 模式，選擇 small 模型")
        return "small"

    print(f"檢測到 GPU VRAM: {vram} GB")

    # 選擇能跑的最大模型（留一些餘量）
    for model, required_vram in reversed(list(models.items())):
        if vram >= required_vram + 1:  # 留 1GB 餘量
            print(f"自動選擇模型: {model}")
            return model

    print("VRAM 不足，使用 tiny 模型")
    return "tiny"


def find_audio_source(video_path: Path) -> Path:
    """
    尋找可用的音訊來源
    優先順序：video.mp4 -> 分離的 m4a -> 分離的 mp3
    """
    video_path = Path(video_path)
    parent_dir = video_path.parent

    # 嘗試使用原始影片（如果有音訊軌道）
    if video_path.exists():
        # 檢查是否有分離的音訊檔案（優先使用，因為純視訊可能沒有音訊）
        audio_files = list(parent_dir.glob("video.f*.m4a")) + list(parent_dir.glob("*.m4a"))
        if audio_files:
            print(f"使用分離的音訊檔案: {audio_files[0].name}")
            return audio_files[0]

        # 沒有分離的音訊，嘗試使用影片本身
        return video_path

    raise FileNotFoundError(f"找不到音訊來源: {video_path}")


def transcribe_audio(
    video_path: Path,
    output_dir: Path,
    model_name: str = "small",
    language: str = "zh"
) -> List[TranscriptSegment]:
    """
    使用 Whisper 轉錄影片音訊

    Args:
        video_path: 影片或音訊路徑
        output_dir: 輸出目錄
        model_name: Whisper 模型名稱
        language: 語言代碼（zh, en 等）

    Returns:
        List[TranscriptSegment]: 逐字稿段落列表
    """
    try:
        import whisper
    except ImportError:
        raise ImportError("請安裝 openai-whisper: pip install openai-whisper")

    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 尋找可用的音訊來源
    audio_source = find_audio_source(video_path)

    # 選擇模型
    model_name = select_whisper_model(model_name)
    print(f"載入 Whisper 模型: {model_name}...")
    model = whisper.load_model(model_name)

    # 轉錄
    print("開始轉錄...")
    result = model.transcribe(
        str(audio_source),
        language=language,
        verbose=True
    )

    # 轉換為 TranscriptSegment 列表
    segments = []
    for seg in result.get("segments", []):
        segments.append(TranscriptSegment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip()
        ))

    # 儲存為 SRT 格式
    srt_path = output_dir / "subtitle.srt"
    save_as_srt(segments, srt_path)
    print(f"逐字稿已儲存: {srt_path}")

    # 儲存為 JSON 格式（保留更多細節）
    json_path = output_dir / "transcript.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return segments


def save_as_srt(segments: List[TranscriptSegment], output_path: Path):
    """將逐字稿儲存為 SRT 格式"""
    def format_time(seconds: float) -> str:
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg.start)} --> {format_time(seg.end)}\n")
            f.write(f"{seg.text}\n\n")


def parse_srt(srt_path: Path) -> List[TranscriptSegment]:
    """解析 SRT 字幕檔"""
    segments = []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    # SRT 格式: 序號, 時間碼, 文字, 空行
    pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\n([\s\S]*?)(?=\n\n|\n\d+\n|$)"

    for match in re.finditer(pattern, content):
        start_str = match.group(2).replace(",", ".")
        end_str = match.group(3).replace(",", ".")
        text = match.group(4).strip()

        # 解析時間碼
        start = parse_timestamp(start_str)
        end = parse_timestamp(end_str)

        if text:  # 忽略空字幕
            segments.append(TranscriptSegment(start=start, end=end, text=text))

    return segments


def parse_timestamp(ts: str) -> float:
    """解析時間碼字串為秒數"""
    parts = ts.replace(",", ".").split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使用方式: python transcribe.py <影片路徑> [模型名稱]")
        print("可用模型: tiny, base, small, medium, large-v3, auto")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    model_name = sys.argv[2] if len(sys.argv) > 2 else "small"
    output_dir = video_path.parent

    segments = transcribe_audio(video_path, output_dir, model_name)
    print(f"\n共轉錄 {len(segments)} 個段落")
