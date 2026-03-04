"""
Video Notes CLI - YouTube 影片筆記自動化系統 (v0.3.0)

使用方式:
    python -m video_notes https://www.youtube.com/watch?v=VIDEO_ID
    python -m video_notes --analyze https://youtube.com/...
    python -m video_notes --analyze-only projects/video_notes/VIDEO_ID/data.yaml
    python -m video_notes --auto-chapters projects/video_notes/VIDEO_ID/data.yaml
    python -m video_notes --help
"""

import argparse
import sys
from pathlib import Path

# 設定專案根目錄
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_BASE = PROJECT_ROOT / "library"


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 影片筆記自動化系統 (v0.3.0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python -m video_notes https://www.youtube.com/watch?v=GjwJVefi_HU
  python -m video_notes --analyze https://youtube.com/...  # 含視覺分析
  python -m video_notes --whisper-model medium https://youtube.com/...
  python -m video_notes --threshold 0.2 --min-interval 3 https://youtube.com/...
  python -m video_notes --render-only projects/video_notes/VIDEO_ID/data.yaml
  python -m video_notes --analyze-only projects/video_notes/VIDEO_ID/data.yaml
        """
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube 影片 URL"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        help=f"輸出目錄（預設: {OUTPUT_BASE}/[video_id]）"
    )

    # 截圖參數
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.15,
        help="場景變化閾值（0-1，越低越敏感，預設: 0.15）"
    )

    parser.add_argument(
        "--min-interval", "-i",
        type=float,
        default=5.0,
        help="最小截圖間隔秒數（預設: 5）"
    )

    parser.add_argument(
        "--max-frames", "-m",
        type=int,
        default=50,
        help="最大截圖數量（預設: 50）"
    )

    parser.add_argument(
        "--timed-interval",
        type=float,
        default=0,
        help="定時截圖間隔（秒），設為 >0 時使用定時模式而非場景變化檢測。建議值: 30-60"
    )

    # Whisper 參數
    parser.add_argument(
        "--whisper-model", "-w",
        default="small",
        choices=["tiny", "base", "small", "medium", "large-v3", "auto"],
        help="Whisper 模型（預設: small）"
    )

    parser.add_argument(
        "--language", "-l",
        default="zh",
        help="轉錄語言（預設: zh）"
    )

    # v0.2.0: 視覺分析選項
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="啟用 LLM 視覺分析（生成標題、摘要、視覺分析）"
    )


    # 單獨執行模式
    parser.add_argument(
        "--render-only",
        type=Path,
        metavar="YAML_PATH",
        help="只執行渲染（從現有 data.yaml 生成 Markdown 和 HTML）"
    )

    parser.add_argument(
        "--analyze-only",
        type=Path,
        metavar="YAML_PATH",
        help="只執行視覺分析（分析現有 data.yaml 中未處理的截圖）"
    )

    parser.add_argument(
        "--analyze-pending",
        type=Path,
        metavar="YAML_PATH",
        help="只分析手動新增的標記（source: manual, analyzed: false）"
    )

    parser.add_argument(
        "--index",
        action="store_true",
        help="生成影片索引頁（列出所有影片及分析狀態）"
    )

    parser.add_argument(
        "--analyze-provider",
        default="ollama",
        choices=["ollama", "gemini", "claude"],
        help="語義分析 LLM 提供者 (預設: ollama)"
    )

    parser.add_argument(
        "--project-type",
        choices=["general", "critique"],
        help="專案類型: general (一般課堂), critique (復原圖分析)"
    )

    parser.add_argument(
        "--auto-chapters",
        type=Path,
        metavar="YAML_PATH",
        help="自動生成章節分類（分析 data.yaml 中的標記並分群）"
    )

    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="跳過下載（使用已存在的影片和字幕）"
    )

    parser.add_argument(
        "--yt-dlp-path",
        default=str(PROJECT_ROOT / "yt-dlp.exe"),
        help="yt-dlp 執行檔路徑"
    )

    args = parser.parse_args()

    # 生成索引頁
    if args.index:
        from .index import generate_index
        generate_index(OUTPUT_BASE)
        return 0

    # 自動章節分類
    if args.auto_chapters:
        from .auto_chapters import process_auto_chapters
        from .render import render_all
        print(f"自動生成章節: {args.auto_chapters}")
        process_auto_chapters(args.auto_chapters)
        print("\n重新渲染...")
        render_all(args.auto_chapters)
        return 0

    # 只渲染模式
    if args.render_only:
        from .render import render_all
        print(f"從 {args.render_only} 渲染...")
        render_all(args.render_only)
        return 0

    # 第一階段：確定專案模式 (適用於需要分析的模式)
    project_type = args.project_type
    need_selection = (args.url or args.analyze_only or args.analyze_pending)
    if not project_type and need_selection:
        print("\n請選擇影片類型：")
        print("1) 一般性課堂 (General Course)")
        print("2) 復原圖分析 (Restoration Analysis / Critique)")
        choice = input("輸入序號 [1/2]: ").strip()
        project_type = "critique" if choice == "2" else "general"
        print(f"-> 已選擇: {project_type}")

    # 只分析模式
    if args.analyze_only:
        from .analyze import analyze_data_yaml
        from .auto_chapters import process_auto_chapters
        from .render import render_all
        from .index import generate_index
        print(f"分析 {args.analyze_only}...")
        analyze_data_yaml(
            args.analyze_only, 
            provider=args.analyze_provider,
            project_type=project_type
        )
        print("\n生成章節...")
        process_auto_chapters(args.analyze_only)
        print("\n重新渲染...")
        render_all(args.analyze_only)
        generate_index(OUTPUT_BASE)
        return 0

    # 只分析待處理標記
    if args.analyze_pending:
        from .analyze import analyze_data_yaml
        from .render import render_all
        import yaml

        yaml_path = Path(args.analyze_pending)
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 過濾出待處理的手動標記
        pending = [f for f in data.get("frames", [])
                   if f.get("source") == "manual" and not f.get("analyzed", False)]

        if not pending:
            print("沒有待處理的手動標記")
            return 0

        print(f"找到 {len(pending)} 個待處理的手動標記")
        analyze_data_yaml(
            yaml_path, 
            provider=args.analyze_provider, 
            skip_analyzed=True,
            project_type=project_type,
            use_vision=args.use_vision
        )
        print("\n重新渲染...")
        render_all(yaml_path)
        return 0

    # 需要 URL
    if not args.url:
        parser.print_help()
        return 1

    # 匯入模組
    from .download import extract_video_id, get_video_info, download_video
    from .keyframes import extract_keyframes
    from .transcribe import transcribe_audio, parse_srt
    from .align import align_keyframes_with_transcript
    from .render import render_all


    # 提取影片 ID
    try:
        video_id = extract_video_id(args.url)
        print(f"影片 ID: {video_id}")
    except ValueError as e:
        print(f"錯誤: {e}")
        return 1

    # 設定輸出目錄
    output_dir = args.output or (OUTPUT_BASE / video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄: {output_dir}")

    # 檢查 yt-dlp
    yt_dlp_path = args.yt_dlp_path
    if not Path(yt_dlp_path).exists():
        # 嘗試在 PATH 中尋找
        yt_dlp_path = "yt-dlp"

    # Step 1: 下載影片和字幕
    video_path = output_dir / "video.mp4"
    subtitle_path = output_dir / "subtitle.srt"

    if args.skip_download and video_path.exists():
        print("跳過下載，使用現有影片")
    else:
        print("\n=== Step 1: 下載影片 ===")
        try:
            video_info = get_video_info(args.url, yt_dlp_path)
            print(f"標題: {video_info.get('title', 'Unknown')}")

            video_path, downloaded_subtitle = download_video(
                args.url, output_dir, yt_dlp_path
            )
            if downloaded_subtitle:
                subtitle_path = downloaded_subtitle
        except Exception as e:
            print(f"下載失敗: {e}")
            return 1

    # 取得影片資訊（如果還沒有）
    try:
        video_info = get_video_info(args.url, yt_dlp_path)
    except Exception:
        video_info = {"title": video_id, "url": args.url, "duration": 0}

    # Step 2: 取得逐字稿
    print("\n=== Step 2: 處理逐字稿 ===")
    if subtitle_path and subtitle_path.exists():
        print(f"使用現有字幕: {subtitle_path}")
        segments = parse_srt(subtitle_path)
    else:
        print("使用 Whisper 轉錄...")
        try:
            segments = transcribe_audio(
                video_path,
                output_dir,
                model_name=args.whisper_model,
                language=args.language
            )
        except ImportError as e:
            print(f"錯誤: {e}")
            print("提示: pip install openai-whisper")
            return 1
        except Exception as e:
            print(f"轉錄失敗: {e}")
            return 1

    print(f"逐字稿段落數: {len(segments)}")

    # Step 3: 提取關鍵幀
    print("\n=== Step 3: 提取關鍵幀 ===")
    print("提示: 已根據指示停用 OpenCV 場景變化檢測，改用語義檢測與定時模式。")
    timed_interval = args.timed_interval if args.timed_interval > 0 else 60.0 # 預設每分鐘一張
    try:
        # 計算語義截圖點
        print("進行語義關鍵點偵測...")
        semantic_ts = [0.0] # 永遠包含第一幀
        for i in range(len(segments) - 1):
            pause = segments[i+1].start - segments[i].end
            if pause > 5.0:  # 停頓超過 5 秒
                semantic_ts.append(segments[i+1].start)
            
            # 關鍵字檢測
            if any(k in segments[i].text for k in ["這一位", "同學", "圖", "平面", "配置", "分數", "大家看"]):
                semantic_ts.append(segments[i].start)

        # 補充定時點
        duration = video_info.get("duration_seconds", 600)
        t = 0
        while t < duration:
            semantic_ts.append(t)
            t += timed_interval

        # 去重與排序
        semantic_ts = sorted(list(set([round(t, 1) for t in semantic_ts])))
        
        # 限制數量
        if len(semantic_ts) > args.max_frames:
            # 均勻取樣
            step = len(semantic_ts) // args.max_frames
            semantic_ts = semantic_ts[::step]

        from .keyframes import extract_frames_at_timestamps
        keyframes = extract_frames_at_timestamps(
            video_path, output_dir, semantic_ts[:args.max_frames]
        )

        # 如果結果還是太少
        if len(keyframes) < 5 and timed_interval == 0:
            duration = video_info.get("duration", 600)
            auto_interval = max(30, duration // 20)
            print(f"\n截圖結果太少，自動補足定時截圖（每 {auto_interval} 秒）")
            # ... 這裡可以再補

    except Exception as e:
        print(f"關鍵幀提取失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 4: 對齊並生成 data.yaml
    print("\n=== Step 4: 對齊與生成資料 ===")
    yaml_path = align_keyframes_with_transcript(
        keyframes, segments, video_info, output_dir
    )

    # Step 5: 語義分析 (v0.4.0 預設執行語義分析)
    if args.analyze or True: # 目前預設開啟，確保有章節
        print(f"\n=== Step 5: 語義分析 (Provider: {args.analyze_provider}) ===")
        try:
            from .analyze import analyze_data_yaml
            analyze_data_yaml(
                yaml_path, 
                provider=args.analyze_provider,
                project_type=project_type
            )
        except Exception as e:
            print(f"警告: 分析失敗: {e}")

    # Step 6: 自動分類章節
    print("\n=== Step 6: 自動分類章節 ===")
    try:
        from .auto_chapters import process_auto_chapters
        process_auto_chapters(yaml_path)
    except Exception as e:
        print(f"警告: 章節生成失敗: {e}")

    # Step 7: 渲染輸出
    print("\n=== Step 7: 生成 Markdown 和 HTML ===")
    md_path, html_path = render_all(yaml_path)

    # Step 8: 更新主索引頁
    print("\n=== Step 8: 更新主索引頁 ===")
    try:
        from .index import generate_index
        generate_index(OUTPUT_BASE)
    except Exception as e:
        print(f"警告: 無法更新索引頁: {e}")

    # 完成
    print("\n" + "=" * 50)
    print(f"✨ 處理完成！\n網頁路徑: {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
