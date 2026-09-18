import subprocess
import json
import sys

yt_dlp = ".venv/Scripts/yt-dlp.exe"
video_id = sys.argv[1] if len(sys.argv) > 1 else "j5_471mO14c"
cmd = [yt_dlp, "--dump-json", f"https://www.youtube.com/watch?v={video_id}"]
res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode == 0:
    data = json.loads(res.stdout)
    print("Title:", data.get("title"))
    print("Duration:", data.get("duration"))
    print("Chapters:")
    for c in data.get("chapters") or []:
        print(f"  {c.get('start_time')}s ({c.get('start_time')//60:02d}:{c.get('start_time')%60:02d}) - {c.get('title')}")
else:
    print("Error:", res.stderr[:300])
