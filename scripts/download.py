"""
下載模組 - 使用 yt-dlp 下載 YouTube 影片與字幕
"""

import subprocess
import re
import json
from pathlib import Path
from typing import Optional, Tuple


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
    raise ValueError(f"無法從 URL 提取影片 ID: {url}")


def get_video_info(url: str, yt_dlp_path: str = "yt-dlp") -> dict:
    """取得影片資訊（標題、時長等）"""
    result = subprocess.run(
        [yt_dlp_path, "--dump-json", "--no-download", url],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    if result.returncode != 0:
        raise RuntimeError(f"無法取得影片資訊: {result.stderr}")
    return json.loads(result.stdout)


def download_video(
    url: str,
    output_dir: Path,
    yt_dlp_path: str = "yt-dlp"
) -> Tuple[Path, Optional[Path]]:
    """
    下載影片和字幕

    Returns:
        Tuple[Path, Optional[Path]]: (影片路徑, 字幕路徑 or None)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_path = output_dir / "video.mp4"
    subtitle_path = output_dir / "subtitle.srt"

    # 檢查是否已有影片（可能是之前下載的分離檔案）
    if not video_path.exists():
        # 檢查是否有分離的視訊檔案（ffmpeg 不可用時會產生）
        separated_videos = list(output_dir.glob("video.f*.mp4"))
        if separated_videos:
            # 使用最大的視訊檔案（通常是最高品質）
            largest = max(separated_videos, key=lambda p: p.stat().st_size)
            print(f"使用現有視訊檔案: {largest.name}")
            largest.rename(video_path)
        else:
            # 嘗試下載（優先使用不需要合併的格式）
            print(f"正在下載影片...")

            # 策略 1: 嘗試下載高品質影片
            # 不限格式下載最佳畫質 (解決 4K 畫質常為 webm 的問題)，再由 ffmpeg 合併為 mp4
            video_cmd = [
                yt_dlp_path,
                "-f", "bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "-o", str(video_path),
                url
            ]
            result = subprocess.run(video_cmd, capture_output=True, text=True, encoding='utf-8')

            # 檢查是否成功或產生分離檔案
            if not video_path.exists():
                # 某些情況下會產生 .f137.mp4 等分離檔案
                separated_videos = list(output_dir.glob("video.f*.mp4"))
                if separated_videos:
                    largest = max(separated_videos, key=lambda p: p.stat().st_size)
                    print(f"ffmpeg 不可用，使用最佳視訊檔案: {largest.name}")
                    largest.rename(video_path)
                elif result.returncode != 0:
                    # 嘗試第二次下載單一合併檔案（較低品質但保證有音訊）
                    print("第一次下載失敗，嘗試下載單一合併檔...")
                    subprocess.run([yt_dlp_path, "-f", "best", "-o", str(video_path), url])
                    if not video_path.exists():
                        raise RuntimeError(f"下載影片失敗: {result.stderr}")
    else:
        print(f"使用現有影片: {video_path}")

    # 嘗試下載字幕（優先繁體中文，其次簡體中文，最後自動字幕）
    subtitle_found = False
    for lang in ["zh-TW", "zh-Hant", "zh-CN", "zh-Hans", "zh", "en"]:
        sub_cmd = [
            yt_dlp_path,
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", lang,
            "--sub-format", "srt",
            "--convert-subs", "srt",
            "--skip-download",
            "-o", str(output_dir / "subtitle"),
            url
        ]
        result = subprocess.run(sub_cmd, capture_output=True, text=True, encoding='utf-8')

        # 檢查是否有字幕檔案生成
        for srt_file in output_dir.glob("subtitle*.srt"):
            srt_file.rename(subtitle_path)
            subtitle_found = True
            print(f"找到字幕: {lang}")
            break
        if subtitle_found:
            break

    if not subtitle_found:
        print("警告: 未找到字幕，將使用 Whisper 轉錄")
        subtitle_path = None

    return video_path, subtitle_path


def format_duration(seconds: int) -> str:
    """將秒數轉換為 HH:MM:SS 格式"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使用方式: python download.py <YouTube URL>")
        sys.exit(1)

    url = sys.argv[1]
    video_id = extract_video_id(url)
    output_dir = Path(f"../../projects/video_notes/{video_id}")

    info = get_video_info(url)
    print(f"影片標題: {info.get('title', 'Unknown')}")
    print(f"影片時長: {format_duration(info.get('duration', 0))}")

    video_path, sub_path = download_video(url, output_dir)
    print(f"影片已下載: {video_path}")
    if sub_path:
        print(f"字幕已下載: {sub_path}")
