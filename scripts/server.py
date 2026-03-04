import http.server
import socketserver
import json
import yaml
from pathlib import Path
import os
import subprocess
import sys

# 設定路徑
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PORT = 10002

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/save':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                
                video_id = data.get('video_id')
                frame_index = data.get('frame_index') # 0-indexed index in 'frames' list
                new_summary = data.get('summary')
                new_title = data.get('title')
                
                if video_id is None:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Missing video_id"}).encode())
                    return

                yaml_path = PROJECT_ROOT / "library" / video_id / "data.yaml"
                if not yaml_path.exists():
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"data.yaml not found for {video_id}"}).encode())
                    return

                with open(yaml_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)

                if frame_index is not None:
                    # Update specific frame
                    if frame_index < len(content['frames']):
                        if new_summary is not None: content['frames'][frame_index]['summary'] = new_summary
                        if new_title is not None: content['frames'][frame_index]['title'] = new_title
                        if 'starred' in data: content['frames'][frame_index]['starred'] = data['starred']
                        content['frames'][frame_index]['analyzed'] = True
                else:
                    # Update video-level status
                    video_info = content.get('video', {})
                    for key in ['watched', 'watched_at', 'review_count', 'reviewed_at', 'folder']:
                        if key in data:
                            video_info[key] = data[key]
                    content['video'] = video_info

                with open(yaml_path, 'w', encoding='utf-8') as f:
                    yaml.dump(content, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
                
                print(f"  [server] Updated data for {video_id}")
                
                # Re-render
                subprocess.run([sys.executable, "-m", "scripts", "--render-only", str(yaml_path)], cwd=PROJECT_ROOT, capture_output=True)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            except Exception as e:
                print(f"  [server] Error in /api/save: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == '/api/library/save':
            try:
                content_length = int(self.headers['Content-Length'])
                data = json.loads(self.rfile.read(content_length))
                lib_path = PROJECT_ROOT / "library" / "library.yaml"
                
                with open(lib_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
                
                # Re-generate index.html after library change
                subprocess.run([sys.executable, "-m", "scripts", "--index"], cwd=PROJECT_ROOT, capture_output=True)
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def main():
    # 設置工作目錄到影片目錄，以便 SimpleHTTPRequestHandler 可以服務靜態檔案
    os.chdir(PROJECT_ROOT / "library")
    
    # 允許地址重用，避免重新啟動時提示 Address already in use
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
        print(f"🚀 Video Notes Server running at http://localhost:{PORT}")
        print(f"📂 Serving from: {os.getcwd()}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopping...")
            httpd.server_close()

if __name__ == "__main__":
    main()
