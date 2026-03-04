"""
關鍵幀提取模組 - 使用視覺變化檢測提取重要畫面
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class KeyFrame:
    """關鍵幀資料結構"""
    timestamp: float  # 秒數
    frame_number: int
    image_path: Path
    change_score: float  # 場景變化分數


def timestamp_to_filename(seconds: float) -> str:
    """將秒數轉換為檔名格式 HH_MM_SS"""
    hours = int(seconds) // 3600
    minutes = (int(seconds) % 3600) // 60
    secs = int(seconds) % 60
    return f"{hours:02d}_{minutes:02d}_{secs:02d}"


def timestamp_to_display(seconds: float) -> str:
    """將秒數轉換為顯示格式 HH:MM:SS"""
    hours = int(seconds) // 3600
    minutes = (int(seconds) % 3600) // 60
    secs = int(seconds) % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def calculate_frame_difference(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """
    計算兩幀之間的差異分數
    使用 LAB 色彩空間，對人眼感知更敏感
    """
    # 轉換為 LAB 色彩空間
    lab1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2LAB)
    lab2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2LAB)

    # 計算絕對差異
    diff = cv2.absdiff(lab1, lab2)

    # 計算平均差異分數（標準化到 0-1）
    score = np.mean(diff) / 255.0
    return score


def calculate_sharpness(frame: np.ndarray) -> float:
    """
    計算畫面清晰度（拉普拉斯變異數）
    數值越高表示越清晰
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return laplacian.var()


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    threshold: float = 0.15,
    min_interval: float = 5.0,
    max_frames: int = 50,
    sample_rate: int = 2,  # 每秒取樣幀數
    timed_interval: float = 0  # 定時截圖間隔（秒），0 表示使用場景變化檢測
) -> List[KeyFrame]:
    """
    從影片中提取關鍵幀

    Args:
        video_path: 影片路徑
        output_dir: 截圖輸出目錄
        threshold: 場景變化閾值（0-1，越低越敏感）
        min_interval: 最小截圖間隔（秒）
        max_frames: 最大截圖數量
        sample_rate: 每秒取樣幀數
        timed_interval: 定時截圖間隔（秒），設為 >0 時使用定時模式而非場景變化檢測

    Returns:
        List[KeyFrame]: 關鍵幀列表
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"無法開啟影片: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    print(f"影片資訊: {fps:.1f} FPS, {total_frames} 幀, {duration:.1f} 秒")

    keyframes = []
    frames_dir.mkdir(parents=True, exist_ok=True)

    # === 定時截圖模式 ===
    if timed_interval > 0:
        print(f"使用定時截圖模式，間隔 {timed_interval} 秒")
        target_times = []
        t = 0
        while t < duration and len(target_times) < max_frames:
            target_times.append(t)
            t += timed_interval

        for target_time in target_times:
            frame_num = int(target_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if ret:
                filename = timestamp_to_filename(target_time)
                image_path = frames_dir / f"{filename}.png"
                # 使用最高品質 PNG (壓縮等級 0 = 無壓縮)
                cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])
                keyframes.append(KeyFrame(
                    timestamp=target_time,
                    frame_number=frame_num,
                    image_path=image_path,
                    change_score=0.0
                ))
                print(f"截圖 #{len(keyframes)}: {timestamp_to_display(target_time)}")

        cap.release()
        print(f"\n完成！共提取 {len(keyframes)} 張關鍵幀（定時模式）")
        return keyframes

    # === 場景變化檢測模式 ===
    # 計算取樣間隔
    sample_interval = int(fps / sample_rate)
    if sample_interval < 1:
        sample_interval = 1

    prev_frame = None
    last_keyframe_time = -min_interval  # 確保第一幀可以被選中

    # 候選幀列表（用於在同一場景內選擇最清晰的）
    scene_candidates = []
    scene_start_time = 0

    frame_number = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 只處理取樣幀
        if frame_number % sample_interval != 0:
            frame_number += 1
            continue

        current_time = frame_number / fps

        if prev_frame is not None:
            diff_score = calculate_frame_difference(prev_frame, frame)

            # 檢測到場景變化
            if diff_score > threshold:
                # 從前一場景的候選中選出最清晰的
                if scene_candidates and (current_time - last_keyframe_time) >= min_interval:
                    best_candidate = max(scene_candidates, key=lambda x: x[2])

                    # 儲存截圖 (最高品質)
                    filename = timestamp_to_filename(best_candidate[1])
                    image_path = frames_dir / f"{filename}.png"
                    cv2.imwrite(str(image_path), best_candidate[0], [cv2.IMWRITE_PNG_COMPRESSION, 0])

                    keyframes.append(KeyFrame(
                        timestamp=best_candidate[1],
                        frame_number=int(best_candidate[1] * fps),
                        image_path=image_path,
                        change_score=diff_score
                    ))

                    last_keyframe_time = best_candidate[1]
                    print(f"截圖 #{len(keyframes)}: {timestamp_to_display(best_candidate[1])}")

                # 重置場景候選
                scene_candidates = []
                scene_start_time = current_time

            # 收集場景內的候選幀
            sharpness = calculate_sharpness(frame)
            scene_candidates.append((frame.copy(), current_time, sharpness))

            # 限制候選數量以節省記憶體
            if len(scene_candidates) > 30:
                # 保留最清晰的幾幀
                scene_candidates.sort(key=lambda x: x[2], reverse=True)
                scene_candidates = scene_candidates[:10]
        else:
            # 第一幀直接加入候選
            sharpness = calculate_sharpness(frame)
            scene_candidates.append((frame.copy(), current_time, sharpness))

        prev_frame = frame.copy()
        frame_number += 1

        # 檢查是否達到最大截圖數
        if len(keyframes) >= max_frames:
            print(f"已達最大截圖數 {max_frames}")
            break

        # 進度顯示
        if frame_number % (int(fps) * 30) == 0:  # 每 30 秒顯示一次
            progress = (frame_number / total_frames) * 100
            print(f"進度: {progress:.1f}%")

    # 處理最後一個場景
    if scene_candidates and len(keyframes) < max_frames:
        best_candidate = max(scene_candidates, key=lambda x: x[2])
        if (best_candidate[1] - last_keyframe_time) >= min_interval:
            filename = timestamp_to_filename(best_candidate[1])
            image_path = frames_dir / f"{filename}.png"
            cv2.imwrite(str(image_path), best_candidate[0], [cv2.IMWRITE_PNG_COMPRESSION, 0])

            keyframes.append(KeyFrame(
                timestamp=best_candidate[1],
                frame_number=int(best_candidate[1] * fps),
                image_path=image_path,
                change_score=0.0
            ))
            print(f"截圖 #{len(keyframes)}: {timestamp_to_display(best_candidate[1])} (結尾)")

    cap.release()

    print(f"\n完成！共提取 {len(keyframes)} 張關鍵幀")
    return keyframes


def extract_frames_at_timestamps(
    video_path: Path,
    output_dir: Path,
    timestamps: List[float]
) -> List[KeyFrame]:
    """
    從影片中特定秒數提取截圖

    Args:
        video_path: 影片路徑
        output_dir: 截圖輸出目錄
        timestamps: 秒數列表
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"無法開啟影片: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    keyframes = []

    for ts in sorted(list(set(timestamps))):
        frame_num = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            filename = timestamp_to_filename(ts)
            image_path = frames_dir / f"{filename}.png"
            # 使用最高品質 PNG
            cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])
            keyframes.append(KeyFrame(
                timestamp=ts,
                frame_number=frame_num,
                image_path=image_path,
                change_score=0.0
            ))
            print(f"提取時間點截圖: {timestamp_to_display(ts)}")

    cap.release()
    return keyframes


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使用方式: python keyframes.py <影片路徑> [輸出目錄]")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else video_path.parent

    keyframes = extract_keyframes(video_path, output_dir)
    for kf in keyframes:
        print(f"  {timestamp_to_display(kf.timestamp)}: {kf.image_path.name}")
