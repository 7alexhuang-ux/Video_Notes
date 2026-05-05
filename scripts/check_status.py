import os
from pathlib import Path
import yaml

video_configs = [
    "https://youtu.be/eO2hGi2bJME", "https://youtu.be/XzXwfGQe1Es", "https://youtu.be/wMkfVi0HlhQ",
    "https://youtu.be/6nsu16wghRg", "https://youtu.be/Y4MCcXziUOQ", "https://youtu.be/CX94uQ6Qo30",
    "https://youtu.be/S7ulqidC36w", "https://youtu.be/h-lPdigv4DU", "https://youtu.be/YNHp8YwxPwI",
    "https://youtu.be/a_m1rsK3HkA", "https://youtu.be/f_aaGpUz2Bc", "https://youtu.be/d8X05Q1YaGE",
    "https://youtu.be/RwzRrx8-d_w", "https://youtu.be/0baG4H2ruMU", "https://youtu.be/oSq0yRZtIB0",
    "https://youtu.be/alw6vXIPylI", "https://youtu.be/oHH5GsCJUyw", "https://youtu.be/x8Vq1dTbNOk",
    "https://youtu.be/XWfePYlK45E", "https://youtu.be/M52U8ng29aA", "https://youtu.be/5BF2Q6Nk4nA",
    "https://youtu.be/XUXFUXCizQg", "https://youtu.be/nXCWmyPMN28", "https://youtu.be/PhulEY1N5rU",
    "https://youtu.be/2BYPh2bDQ2A", "https://youtu.be/GjwJVefi_HU", "https://youtu.be/HPvfKwCLvLs",
    "https://youtu.be/18DZEAcs89Y", "https://youtu.be/YEmW5ITHT9A"
]

def extract_id(url):
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return url

PROJECT_ROOT = Path(__file__).resolve().parent.parent
base_dir = PROJECT_ROOT / "data"
success = []
failed = []

for url in video_configs:
    vid = extract_id(url)
    target_dir = base_dir / vid
    yaml_path = target_dir / "data.yaml"
    
    if yaml_path.exists():
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if data and data.get("chapters"):
                # Check if it was analyzed by LLM (has title/summary)
                frames = data.get("frames", [])
                if frames and frames[0].get("analyzed"):
                     success.append(vid)
                else:
                     failed.append(vid)
            else:
                failed.append(vid)
        except Exception:
            failed.append(vid)
    else:
        failed.append(vid)

print(f"Total: {len(video_configs)}")
print(f"Success: {len(success)}")
print(f"Failed: {len(failed)}")
print(f"Failed IDs: {failed}")
