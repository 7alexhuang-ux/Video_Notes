"""
影片索引頁生成模組 - 列出所有影片及其分析狀態 (v0.4.5)
"""

from pathlib import Path
from datetime import datetime
import yaml
import json
import os

# HTML 模板 - 列表式、支援資料夾、星號卡片、自動儲存
INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Library - AI Notes Agent</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text-color: #f1f5f9;
            --accent-color: #38bdf8;
            --secondary-bg: #1e293b;
            --glass-border: rgba(255, 255, 255, 0.1);
            --success-color: #10b981;
            --folder-color: #fbbf24;
        }

        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: radial-gradient(circle at top right, #1e293b, #0f172a);
            color: var(--text-color);
            margin: 0;
            min-height: 100vh;
        }

        .container { max-width: 1400px; margin: 0 auto; padding: 40px 20px; }

        header { margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-end; }
        header h1 { font-size: 2.5rem; font-weight: 800; letter-spacing: -0.025em; margin: 0; }
        
        .tab-bar { margin-bottom: 24px; display: flex; gap: 8px; border-bottom: 1px solid var(--glass-border); padding-bottom: 8px; }
        .tab { 
            padding: 8px 24px; cursor: pointer; border-radius: 8px 8px 0 0; font-weight: 600; opacity: 0.5;
            transition: all 0.2s;
        }
        .tab.active { opacity: 1; background: var(--secondary-bg); color: var(--accent-color); border-bottom: 2px solid var(--accent-color); }

        .stat-pills { display: flex; gap: 12px; }
        .pill { background: var(--secondary-bg); padding: 6px 16px; border-radius: 99px; border: 1px solid var(--glass-border); font-size: 0.85rem; font-weight: 500; }
        .pill span { color: var(--accent-color); font-weight: 700; margin-right: 4px; }

        /* List View Styles */
        .library-section { margin-bottom: 40px; }
        .folder-container { margin-bottom: 20px; background: var(--card-bg); border-radius: 12px; border: 1px solid var(--glass-border); overflow: hidden; }
        .collapsed { background: none; border-color: transparent; }
        .folder-header { 
            padding: 16px 20px; background: rgba(255,255,255,0.03); cursor: pointer; display: flex; align-items: center; justify-content: space-between;
            border-bottom: 1px solid var(--glass-border);
        }
        .collapsed .folder-header { border-bottom: none; background: rgba(255,255,255,0.01); }
        .folder-title { display: flex; align-items: center; gap: 12px; font-weight: 700; color: var(--folder-color); }
        .folder-arrow { transition: transform 0.2s; }
        .collapsed .folder-arrow { transform: rotate(-90deg); }
        .folder-content { padding: 8px 0; min-height: 20px; }
        .collapsed .folder-content { display: none; }

        .video-item { 
            display: grid; grid-template-columns: 40px 1fr 120px 100px 160px 140px; align-items: center; padding: 12px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s; cursor: grab;
        }
        .video-item:last-child { border-bottom: none; }
        .video-item:hover { background: rgba(255,255,255,0.02); }
        
        .drag-handle { color: #475569; font-size: 1.2rem; }
        .video-main { display: flex; flex-direction: column; gap: 2px; }
        .video-name { font-weight: 600; text-decoration: none; color: inherit; font-size: 0.95rem; }
        .video-name:hover { color: var(--accent-color); }
        .video-sub { font-size: 0.75rem; color: #64748b; display: flex; gap: 10px; }

        .status-cell { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; }
        .check-box { 
            width: 18px; height: 18px; border-radius: 4px; border: 2px solid #475569; cursor: pointer;
            display: flex; align-items: center; justify-content: center; transition: all 0.2s;
        }
        .check-box.checked { background: var(--success-color); border-color: var(--success-color); }
        .check-box.checked::after { content: '✓'; color: white; font-size: 12px; font-weight: 900; }

        .review-counter { display: flex; align-items: center; gap: 8px; background: #1e293b; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--glass-border); }
        .rev-btn { cursor: pointer; opacity: 0.6; transition: opacity 0.2s; }
        .rev-btn:hover { opacity: 1; color: var(--accent-color); }
        .rev-val { font-family: monospace; font-weight: 700; min-width: 12px; text-align: center; }

        .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; background: #334155; }
        .badge.analyzed { background: rgba(16, 185, 129, 0.2); color: #10b981; }

        .controls-top { margin-bottom: 20px; display: flex; gap: 10px; }
        .view-section { display: none; }
        .view-section.active { display: block; }
        
        /* Star Card Specific */
        .star-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; padding: 20px; }
        .star-card { background: var(--card-bg); border-radius: 12px; overflow: hidden; border: 1px solid var(--glass-border); display: flex; flex-direction: column; cursor: grab; }
        .star-card img { width: 100%; height: 200px; object-fit: cover; }
        .star-card-body { padding: 16px; flex-grow: 1; }
        .star-card-title { font-weight: 700; margin-bottom: 8px; color: var(--accent-color); font-size: 1rem; }
        .star-card-summary { font-size: 0.85rem; opacity: 0.8; line-height: 1.6; }
        .star-card-meta { margin-top: 12px; font-size: 0.75rem; color: #64748b; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px; }

        .btn { 
            padding: 8px 16px; border-radius: 8px; border: 1px solid var(--glass-border); background: var(--secondary-bg); 
            color: white; font-size: 0.85rem; cursor: pointer; transition: all 0.2s;
        }
        .btn:hover { background: #334155; border-color: var(--accent-color); }
        .btn.primary { background: var(--accent-color); color: #0f172a; font-weight: 700; border: none; }

        #save-status { position: fixed; bottom: 20px; right: 20px; padding: 12px 24px; border-radius: 12px; background: var(--success-color); color: white; font-weight: 700; transform: translateY(100px); transition: transform 0.3s; z-index: 1000; box-shadow: 0 10px 30px rgba(0,0,0,0.3); pointer-events: none; }
        #save-status.visible { transform: translateY(0); }

        .sortable-ghost { opacity: 0.4; background: var(--accent-color) !important; }

        @media (max-width: 1000px) {
            .video-item { grid-template-columns: 40px 1fr 100px; }
            .hide-mobile { display: none; }
        }
    </style>
</head>
<body>
    <div id="save-status">✅ 已自動同步</div>
    <div class="container">
        <header>
            <div>
                <h1>Video Library</h1>
                <p style="color: #64748b; margin-top: 4px;">由 AI 自動提煉的互動式筆記系統</p>
            </div>
            <div class="stat-pills" id="global-stats"></div>
        </header>

        <div class="tab-bar">
            <div class="tab active" onclick="switchView('library')">📚 檔案庫</div>
            <div class="tab" onclick="switchView('stars')">⭐ 重點摘錄</div>
        </div>

        <div id="library-view" class="view-section active">
            <div class="controls-top">
                <button class="btn primary" onclick="addNewFolder('library')">+ 新增分類</button>
                <button class="btn" onclick="autoCategorize()">🪄 按日期分類</button>
                <button class="btn" style="margin-left: auto;" onclick="toggleAllFolders()">展開/摺疊全部</button>
            </div>
            <div id="library-root" class="library-section"></div>
        </div>

        <div id="stars-view" class="view-section">
            <div class="controls-top">
                <button class="btn primary" onclick="addNewFolder('stars')">+ 新增主題</button>
                <button class="btn" style="margin-left: auto;" onclick="toggleAllFolders('.stars-section')">展開/摺疊全部</button>
            </div>
            <div id="stars-root" class="library-section stars-section"></div>
        </div>

        <footer>
            Video Notes v0.4.5 | 最後同步於 <span id="sync-time"></span>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>

    <script>
        let library = LIBRARY_DATA_PLACEHOLDER; 
        const videosMap = VIDEO_MAP_PLACEHOLDER; 
        const starredFrames = STARRED_DATA_PLACEHOLDER;

        function switchView(view) {
            document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.textContent.includes(view === 'library' ? '檔案庫' : '重點')));
            document.querySelectorAll('.view-section').forEach(s => s.classList.toggle('active', s.id === view + '-view'));
            if (view === 'stars') renderStars();
            else renderLibrary();
        }

        function renderLibrary() {
            const root = document.getElementById('library-root');
            root.innerHTML = '';
            if (!library.structure) library.structure = [];
            library.structure.forEach((item, idx) => {
                if (item.type === 'folder') root.appendChild(createFolderEl(item, ['structure', idx]));
                else root.appendChild(createVideoEl(item.id, ['structure', idx]));
            });
            initDragDrop('.sortable-list', 'library');
            updateStats();
        }

        function renderStars() {
            const root = document.getElementById('stars-root');
            root.innerHTML = '';
            if (!library.starred_structure) library.starred_structure = [];
            library.starred_structure.forEach((item, idx) => {
                if (item.type === 'folder') root.appendChild(createStarFolderEl(item, ['starred_structure', idx]));
                else root.appendChild(createStarCardEl(item.vid, item.idx, ['starred_structure', idx]));
            });
            initDragDrop('.sortable-stars', 'stars');
            updateStats();
        }

        function createFolderEl(folder, path) {
            const container = document.createElement('div');
            container.className = 'folder-container';
            const header = document.createElement('div');
            header.className = 'folder-header';
            header.innerHTML = `<div class="folder-title"><span class="folder-arrow">▼</span> 📂 <span>${folder.name}</span> <span class="badge" style="background:#1e293b; color:#94a3b8; margin-left:8px;">${folder.items.length}</span></div>`;
            header.onclick = () => container.classList.toggle('collapsed');
            const content = document.createElement('div');
            content.className = 'folder-content sortable-list';
            folder.items.forEach((item, i) => {
                if (item.type === 'video') content.appendChild(createVideoEl(item.id, [...path, 'items', i]));
                else if (item.type === 'folder') content.appendChild(createFolderEl(item, [...path, 'items', i]));
            });
            container.appendChild(header);
            container.appendChild(content);
            return container;
        }

        function createStarFolderEl(folder, path) {
            const container = document.createElement('div');
            container.className = 'folder-container';
            const header = document.createElement('div');
            header.className = 'folder-header';
            header.innerHTML = `<div class="folder-title"><span class="folder-arrow">▼</span> ⭐ <span>${folder.name}</span> <span class="badge" style="background:#1e293b; color:#fbbf24; margin-left:8px;">${folder.items.length}</span></div>`;
            header.onclick = () => container.classList.toggle('collapsed');
            const content = document.createElement('div');
            content.className = 'folder-content star-grid sortable-stars';
            folder.items.forEach((item, i) => {
                if (item.type === 'star') content.appendChild(createStarCardEl(item.vid, item.idx, [...path, 'items', i]));
                else if (item.type === 'folder') content.appendChild(createStarFolderEl(item, [...path, 'items', i]));
            });
            container.appendChild(header);
            container.appendChild(content);
            return container;
        }

        function createVideoEl(id, path) {
            const video = videosMap[id];
            if (!video) return document.createElement('div');
            const el = document.createElement('div');
            el.className = 'video-item';
            el.dataset.id = id;
            const isWatched = video.watched || false;
            el.innerHTML = `
                <div class="drag-handle">⋮⋮</div>
                <div class="video-main">
                    <a href="${id}/index.html" class="video-name">${video.title}</a>
                    <div class="video-sub">
                        <span>⏱️ ${video.duration}</span>
                        <span>📅 ${video.downloaded_at}</span>
                        <span class="badge ${video.analyzed_count > 0 ? 'analyzed' : ''}">${video.analyzed_count}/${video.total_frames} 分析</span>
                    </div>
                </div>
                <div class="status-cell hide-mobile">
                    <div class="check-box ${isWatched ? 'checked' : ''}" onclick="toggleWatched('${id}')"></div>
                    <span>${isWatched ? '已看完' : '未看'}</span>
                </div>
                <div class="review-counter hide-mobile">
                    <span class="rev-btn" onclick="updateReview('${id}', -1)">−</span>
                    <span class="rev-val">${video.review_count || 0}</span>
                    <span class="rev-btn" onclick="updateReview('${id}', 1)">+</span>
                </div>
                <div class="hide-mobile" style="font-size: 0.75rem; color: #64748b;">
                    ${video.watched_at ? `👁️ ${video.watched_at.split(' ')[0]}` : ''}<br>
                    ${video.reviewed_at ? `🔄 ${video.reviewed_at.split(' ')[0]}` : ''}
                </div>
                <div class="hide-mobile">${video.max_score !== null ? `<span class="badge" style="background: ${video.max_score >= 60 ? 'rgba(16,185,129,0.2)' : 'rgba(233,69,96,0.2)'}; color: ${video.max_score >= 60 ? '#10b981' : '#f87171'}">Score: ${video.max_score}</span>` : ''}</div>
            `;
            return el;
        }

        function createStarCardEl(vid, frameIdx, path) {
            const star = starredFrames.find(s => s.video_id === vid && s.frame_index === frameIdx);
            if (!star) return document.createElement('div');
            const el = document.createElement('div');
            el.className = 'star-card';
            el.dataset.vid = vid; el.dataset.idx = frameIdx;
            el.innerHTML = `
                <a href="${vid}/index.html#frame-${frameIdx + 1}" style="display:block;"><img src="${vid}/${star.image}" loading="lazy"></a>
                <div class="star-card-body">
                    <div class="star-card-title">${star.title || '無標題'}</div>
                    <div class="star-card-summary">${(star.summary || '').replace(/\\n/g, '<br>')}</div>
                    <div class="star-card-meta">🎬 ${star.video_title} (${star.timestamp})</div>
                </div>
            `;
            return el;
        }

        function initDragDrop(selector, groupName) {
            document.querySelectorAll(selector).forEach(list => {
                new Sortable(list, {
                    group: groupName, animation: 150, handle: '.drag-handle, .video-item, .star-card', ghostClass: 'sortable-ghost',
                    onEnd: () => {
                        if (groupName === 'library') rebuildLibraryFromDOM();
                        else rebuildStarsFromDOM();
                    }
                });
            });
        }

        function rebuildLibraryFromDOM() { library.structure = scanNode(document.getElementById('library-root'), 'video'); saveLibrary(); }
        function rebuildStarsFromDOM() { library.starred_structure = scanNode(document.getElementById('stars-root'), 'star'); saveLibrary(); }

        function scanNode(node, typeName) {
            const items = [];
            Array.from(node.children).forEach(child => {
                if (child.classList.contains('video-item')) items.push({ type: 'video', id: child.dataset.id });
                else if (child.classList.contains('star-card')) items.push({ type: 'star', vid: child.dataset.vid, idx: parseInt(child.dataset.idx) });
                else if (child.classList.contains('folder-container')) {
                    const name = child.querySelector('.folder-title span:not(.folder-arrow):not(.badge)').textContent;
                    items.push({ type: 'folder', name: name, items: scanNode(child.querySelector('.folder-content'), typeName) });
                }
            });
            return items;
        }

        function toggleWatched(id) {
            const video = videosMap[id];
            video.watched = !video.watched;
            video.watched_at = video.watched ? new Date().toISOString().replace('T', ' ').substring(0, 19) : null;
            saveVideoStatus(id, { watched: video.watched, watched_at: video.watched_at });
            renderLibrary();
        }

        function updateReview(id, delta) {
            const video = videosMap[id];
            video.review_count = Math.max(0, (video.review_count || 0) + delta);
            if (delta > 0) video.reviewed_at = new Date().toISOString().replace('T', ' ').substring(0, 19);
            saveVideoStatus(id, { review_count: video.review_count, reviewed_at: video.reviewed_at });
            renderLibrary();
        }

        function saveVideoStatus(id, data) {
            fetch('http://localhost:10002/api/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ video_id: id, ...data }) });
            showToast();
        }

        function saveLibrary() {
            fetch('http://localhost:10002/api/library/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(library) });
            showToast();
        }

        function showToast() {
            const toast = document.getElementById('save-status');
            toast.classList.add('visible');
            setTimeout(() => toast.classList.remove('visible'), 2000);
        }

        function addNewFolder(view) {
            const name = prompt('資料夾名稱:');
            if (name) {
                if (view === 'library') library.structure.unshift({ type: 'folder', name, items: [] });
                else library.starred_structure.unshift({ type: 'folder', name, items: [] });
                saveLibrary();
                view === 'library' ? renderLibrary() : renderStars();
            }
        }

        function toggleAllFolders(selector = '.folder-container') {
            const anyOpen = document.querySelector(selector + ':not(.collapsed)');
            document.querySelectorAll(selector).forEach(f => {
                if (anyOpen) f.classList.add('collapsed');
                else f.classList.remove('collapsed');
            });
        }

        function autoCategorize() {
            const videos = Object.values(videosMap);
            const groups = {};

            videos.forEach(v => {
                // 1. Determine Category (from folder property)
                const category = v.folder || "未分類";

                // 2. Extract Date from Title (Matches YYYY MMDD, YYYY-MM-DD, or YYYYMMDD)
                let date = "未定日期";
                // 擴增正則表達式，不僅支援 YYYY MMDD，也支援 YYYYMMDD
                const dateMatch = v.title.match(/(20\\d{2})[- \\/]?([01]\\d)[- \\/]?([0-3]\\d)/);
                if (dateMatch) {
                    date = `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`;
                }

                if (!groups[category]) groups[category] = {};
                if (!groups[category][date]) groups[category][date] = [];
                
                groups[category][date].push({ type: 'video', id: v.video_id });
            });

            // 3. Build hierarchical structure
            library.structure = Object.keys(groups).sort().map(category => {
                const dateFolders = Object.keys(groups[category]).sort().reverse().map(date => ({
                    type: 'folder', 
                    name: date, 
                    items: groups[category][date]
                }));
                
                return {
                    type: 'folder',
                    name: category,
                    items: dateFolders
                };
            });

            saveLibrary();
            renderLibrary();
        }

        function updateStats() {
            let total = 0, watched = 0, reviewed = 0;
            Object.values(videosMap).forEach(v => { total++; if (v.watched) watched++; if (v.review_count > 0) reviewed++; });
            document.getElementById('global-stats').innerHTML = `
                <div class="pill"><span>${total}</span> 總數</div>
                <div class="pill"><span>${watched}</span> 已完食</div>
                <div class="pill"><span>${reviewed}</span> 已複習</div>
            `;
            document.getElementById('sync-time').textContent = new Date().toLocaleTimeString();
        }

        renderLibrary();
    </script>
</body>
</html>
"""

def scan_video_projects(base_dir: Path):
    """掃描所有影片專案並收集資訊"""
    videos = []
    starred_frames = []

    for project_dir in base_dir.iterdir():
        if not project_dir.is_dir(): continue
        data_yaml = project_dir / "data.yaml"
        if not data_yaml.exists(): continue

        try:
            with open(data_yaml, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            v_info = data.get("video", {})
            v_title = v_info.get("title", project_dir.name)
            frames = data.get("frames", [])

            # Collect starred frames
            for i, f in enumerate(frames):
                if f.get("starred"):
                    starred_frames.append({
                        "video_id": project_dir.name,
                        "video_title": v_title,
                        "frame_index": i,
                        "timestamp": f.get("timestamp"),
                        "title": f.get("title"),
                        "summary": f.get("summary"),
                        "image": f.get("image")
                    })

            analyzed_count = sum(1 for f in frames if f.get("analyzed", False))
            manual_count = sum(1 for f in frames if f.get("source") == "manual")
            scores = [f["score"] for f in frames if f.get("score") is not None]
            max_score = max(scores) if scores else None
            
            thumbnail = None
            frames_dir = project_dir / "frames"
            if frames_dir.exists():
                first_frame = list(frames_dir.glob("*.png"))
                if first_frame: thumbnail = f"{project_dir.name}/frames/{first_frame[0].name}"

            videos.append({
                "video_id": project_dir.name,
                "title": v_title,
                "url": v_info.get("url", ""),
                "duration": v_info.get("duration", "00:00"),
                "downloaded_at": v_info.get("downloaded_at", ""),
                "total_frames": len(frames),
                "analyzed_count": analyzed_count,
                "manual_count": manual_count,
                "max_score": max_score,
                "thumbnail": thumbnail,
                "watched": v_info.get("watched", False),
                "watched_at": v_info.get("watched_at"),
                "review_count": v_info.get("review_count", 0),
                "reviewed_at": v_info.get("reviewed_at")
            })
        except: continue
    return videos, starred_frames

def generate_index(base_dir: Path) -> Path:
    """生成影片索引頁"""
    base_dir = Path(base_dir)
    print("掃描影片專案與星號...")
    videos, starred_frames = scan_video_projects(base_dir)

    lib_path = base_dir / "library.yaml"
    library = {"structure": [], "starred_structure": []}
    if lib_path.exists():
        with open(lib_path, "r", encoding="utf-8") as f:
            library = yaml.safe_load(f)
    
    if not library.get("structure"):
        library["structure"] = [{"type": "folder", "name": "未分類", "items": [{"type": "video", "id": v["video_id"]} for v in sorted(videos, key=lambda x:x['downloaded_at'], reverse=True)]}]
    if not library.get("starred_structure"):
        library["starred_structure"] = [{"type": "folder", "name": "全體重點", "items": []}]

    # 同步 structure
    lib_ids = set()
    def collect_ids(items):
        for it in items:
            if it['type'] == 'video': lib_ids.add(it['id'])
            elif it['type'] == 'folder': collect_ids(it['items'])
    collect_ids(library['structure'])
    for v in videos:
        if v["video_id"] not in lib_ids:
            library['structure'][0]['items'].append({"type": "video", "id": v["video_id"]})

    # 同步 stars
    starred_ids = set()
    def collect_stars(items):
        for it in items:
            if it['type'] == 'star': starred_ids.add(f"{it['vid']}-{it['idx']}")
            elif it['type'] == 'folder': collect_stars(it['items'])
    collect_stars(library['starred_structure'])
    for s in starred_frames:
        s_id = f"{s['video_id']}-{s['frame_index']}"
        if s_id not in starred_ids:
            library['starred_structure'][0]['items'].append({"type": "star", "vid": s['video_id'], "idx": s['frame_index']})

    html_content = INDEX_TEMPLATE.replace(
        "LIBRARY_DATA_PLACEHOLDER", json.dumps(library, ensure_ascii=False)
    ).replace(
        "VIDEO_MAP_PLACEHOLDER", json.dumps({v["video_id"]: v for v in videos}, ensure_ascii=False)
    ).replace(
        "STARRED_DATA_PLACEHOLDER", json.dumps(starred_frames, ensure_ascii=False)
    ).replace(
        "GENERATED_AT_PLACEHOLDER", datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    index_path = base_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"索引頁已完成: {index_path}")
    return index_path

if __name__ == "__main__":
    import sys
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent / "library"
    if len(sys.argv) > 1: base_dir = Path(sys.argv[1])
    generate_index(base_dir)
