import subprocess
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

# 影片清單
video_urls = [
    "https://youtu.be/XzXwfGQe1Es",
    "https://youtu.be/wMkfVi0HlhQ",
    "https://youtu.be/6nsu16wghRg",
    "https://youtu.be/Y4MCcXziUOQ",
    "https://youtu.be/CX94uQ6Qo30",
    "https://youtu.be/S7ulqidC36w",
    "https://youtu.be/h-lPdigv4DU",
    "https://youtu.be/YNHp8YwxPwI",
    "https://youtu.be/a_m1rsK3HkA",
    "https://youtu.be/f_aaGpUz2Bc",
    "https://youtu.be/d8X05Q1YaGE",
    "https://youtu.be/RwzRrx8-d_w",
    "https://youtu.be/0baG4H2ruMU",
    "https://youtu.be/oSq0yRZtIB0",
    "https://youtu.be/alw6vXIPylI",
    "https://youtu.be/oHH5GsCJUyw",
    "https://youtu.be/PhulEY1N5rU",
    "https://youtu.be/2BYPh2bDQ2A",
    "https://youtu.be/GjwJVefi_HU",
    "https://youtu.be/HPvfKwCLvLs",
    "https://youtu.be/18DZEAcs89Y",
    "https://youtu.be/YEmW5ITHT9A",
    "https://youtu.be/E7wzj_VDv2w",
    "https://youtu.be/x8Vq1dTbNOk",
    "https://youtu.be/XWfePYlK45E",
    "https://youtu.be/M52U8ng29aA",
    "https://youtu.be/5BF2Q6Nk4nA",
    "https://youtu.be/XUXFUXCizQg",
    "https://youtu.be/nXCWmyPMN28"
]

def extract_id(url):
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1]
    return url.split("v=")[1]

base_dir = PROJECT_ROOT / "data"

for i, url in enumerate(video_urls):
    vid = extract_id(url)
    target_dir = base_dir / vid
    
    if target_dir.exists() and (target_dir / "data.yaml").exists():
        print(f"[{i+1}/{len(video_urls)}] Skipping {vid} (Already exists)")
        continue
        
    print(f"\n[{i+1}/{len(video_urls)}] Processing {vid}...")
    
    # 執行自動化指令 (不帶 --analyze)
    # 使用定時截圖 60 秒一張
    cmd = [
        "python", "-m", "video_notes",
        "--timed-interval", "60",
        "--project-type", "general",
        url
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    try:
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT, env=env)
        print(f"Successfully processed {vid}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to process {vid}: {e}")

print("\nBatch processing complete!")
