"""
自動章節分類模組 (v0.3.0)

使用混合策略自動將 frames 分成章節：
1. 時間間隔分析：超過 N 秒沒有標記視為章節邊界
2. 標題語意分群：相似標題歸為同一章節
3. 內容變化偵測：摘要內容主題變化時分章
"""

from pathlib import Path
from typing import List, Dict, Any
import yaml
import re
from .analyze import analyze_global_chapters


def extract_keywords(text: str) -> set:
    """從文字中提取關鍵詞"""
    if not text:
        return set()

    # 移除常見的無意義詞彙
    stopwords = {
        '的', '是', '在', '和', '了', '與', '及', '或', '也', '都', '就', '會',
        '要', '可以', '這個', '那個', '什麼', '怎麼', '如何', '為什麼',
        'the', 'a', 'an', 'is', 'are', 'and', 'or', 'to', 'of', 'in', 'on'
    }

    # 提取詞彙（中文按字元，英文按單詞）
    words = set()

    # 英文單詞
    english_words = re.findall(r'[a-zA-Z]+', text.lower())
    words.update(w for w in english_words if len(w) > 2 and w not in stopwords)

    # 中文（取 2-4 字的組合）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for segment in chinese_chars:
        if len(segment) >= 2:
            words.add(segment)

    return words


def calculate_similarity(keywords1: set, keywords2: set) -> float:
    """計算兩組關鍵詞的相似度 (Jaccard)"""
    if not keywords1 or not keywords2:
        return 0.0

    intersection = len(keywords1 & keywords2)
    union = len(keywords1 | keywords2)

    return intersection / union if union > 0 else 0.0


def auto_generate_chapters(
    frames: List[Dict[str, Any]],
    min_chapter_size: int = 2,
    max_time_gap: float = 90.0,
    similarity_threshold: float = 0.15
) -> List[Dict[str, Any]]:
    """
    自動生成章節

    Args:
        frames: frame 資料列表
        min_chapter_size: 最小章節大小（至少幾個 frame）
        max_time_gap: 最大時間間隔（超過此秒數視為新章節）
        similarity_threshold: 相似度閾值（低於此值視為新章節）

    Returns:
        chapters 列表
    """
    if not frames:
        return []

    if len(frames) <= min_chapter_size:
        # 太少 frame，整個視為一章
        return [{
            "title": frames[0].get("title", "全部內容") if frames else "全部內容",
            "start_index": 0,
            "end_index": len(frames) - 1
        }]

    # 提取每個 frame 的關鍵詞
    frame_keywords = []
    for frame in frames:
        title = frame.get("title", "")
        summary = frame.get("summary", "")
        keywords = extract_keywords(title) | extract_keywords(summary[:100] if summary else "")
        frame_keywords.append(keywords)

    # 尋找章節邊界
    boundaries = [0]  # 第一個 frame 一定是邊界

    for i in range(1, len(frames)):
        is_boundary = False

        # 檢查時間間隔
        prev_time = frames[i-1].get("timestamp_seconds", 0)
        curr_time = frames[i].get("timestamp_seconds", 0)
        time_gap = curr_time - prev_time

        if time_gap > max_time_gap:
            is_boundary = True

        # 檢查語意相似度
        if not is_boundary and frame_keywords[i] and frame_keywords[i-1]:
            similarity = calculate_similarity(frame_keywords[i], frame_keywords[i-1])
            if similarity < similarity_threshold:
                is_boundary = True

        if is_boundary:
            boundaries.append(i)

    # 確保最後一個 frame 被包含
    if boundaries[-1] != len(frames) - 1:
        # 最後一個邊界到結尾
        pass

    # 合併太小的章節
    merged_boundaries = [boundaries[0]]
    for i in range(1, len(boundaries)):
        prev_boundary = merged_boundaries[-1]
        curr_boundary = boundaries[i]

        # 如果章節太小，跳過這個邊界
        if curr_boundary - prev_boundary < min_chapter_size:
            continue

        merged_boundaries.append(curr_boundary)

    # 生成章節
    chapters = []
    for i, start_idx in enumerate(merged_boundaries):
        if i + 1 < len(merged_boundaries):
            end_idx = merged_boundaries[i + 1] - 1
        else:
            end_idx = len(frames) - 1

        # 章節標題：使用第一個 frame 的標題，簡化後作為章節名
        first_frame_title = frames[start_idx].get("title", f"第 {i+1} 章")
        chapter_title = simplify_title(first_frame_title, i + 1)

        chapters.append({
            "title": chapter_title,
            "start_index": start_idx,
            "end_index": end_idx
        })

    return chapters


def simplify_title(title: str, chapter_num: int) -> str:
    """簡化標題作為章節名稱"""
    if not title:
        return f"第 {chapter_num} 章"

    # 移除常見的前綴
    title = re.sub(r'^([\d]+[\.、:]?\s*)', '', title)

    # 取冒號前的部分作為主標題
    if '：' in title:
        title = title.split('：')[0]
    elif ':' in title:
        title = title.split(':')[0]

    # 限制長度
    if len(title) > 20:
        title = title[:20] + '...'

    return title or f"第 {chapter_num} 章"


def update_data_yaml_with_chapters(yaml_path: Path, chapters: List[Dict[str, Any]]) -> None:
    """更新 data.yaml，加入章節資訊"""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["chapters"] = chapters

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"已更新章節資訊到: {yaml_path}")
    print(f"共 {len(chapters)} 個章節:")
    for ch in chapters:
        frame_count = ch["end_index"] - ch["start_index"] + 1
        print(f"  - {ch['title']} ({frame_count} 個標記)")


def process_auto_chapters(yaml_path: Path) -> List[Dict[str, Any]]:
    """
    處理自動章節分類

    Args:
        yaml_path: data.yaml 路徑

    Returns:
        生成的章節列表
    """
    yaml_path = Path(yaml_path)

    # 載入資料
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    frames = data.get("frames", [])

    if not frames:
        print("沒有找到 frames 資料")
        return []

    # 優先使用 LLM 進行大章節有意識分組
    print("🧠 正在使用 LLM 進行全域章節架構分析...")
    llm_chapters = analyze_global_chapters(frames)
    
    if llm_chapters and len(llm_chapters) > 0:
        chapters = llm_chapters
        print(f"✅ LLM 已完成分組: {len(chapters)} 個大章節")
    else:
        print("⚠️ LLM 分析失敗或返回空，回退到啟發式演算法...")
        chapters = auto_generate_chapters(frames)

    # 更新 yaml
    update_data_yaml_with_chapters(yaml_path, chapters)

    return chapters


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用方式: python auto_chapters.py <data.yaml 路徑>")
        sys.exit(1)

    yaml_path = Path(sys.argv[1])
    process_auto_chapters(yaml_path)
