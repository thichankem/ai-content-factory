import os
import sys
import re
import io
import time
import requests
import subprocess
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICTURE_DIR = os.path.join(BASE_DIR, "picture")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def search_bing_images(query, max_results=10):
    url = f"https://www.bing.com/images/search?q={requests.utils.quote(query)}&first=1&scenario=ImageBasicHover"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return []
        matches = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', r.text)
        clean_urls = []
        for m in matches:
            m_clean = m.replace(r'\/', '/')
            if m_clean.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                clean_urls.append(m_clean)
        return clean_urls[:max_results]
    except Exception as e:
        print(f"Error searching Bing for '{query}': {e}")
        return []

def download_and_validate(url, min_width=1200, min_height=650):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200 or len(r.content) < 40000:
            return None
        img = Image.open(io.BytesIO(r.content))
        w, h = img.size
        if w < min_width or h < min_height:
            return None
        # Must not be an icon or square avatar
        ratio = w / h
        if ratio < 1.1 or ratio > 3.0:
            return None
        # Convert to RGB if necessary for saving as PNG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        return img
    except Exception:
        return None

def extract_youtube_frame(query, timestamp, out_path):
    print(f"  -> Attempting YouTube frame grab for query: '{query}' at {timestamp}")
    try:
        yt_dlp_path = os.path.join(BASE_DIR, ".venv", "Scripts", "yt-dlp.exe")
        if not os.path.exists(yt_dlp_path):
            yt_dlp_path = "yt-dlp"
        cmd = [
            yt_dlp_path,
            "--get-url",
            "-f", "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]/best",
            f"ytsearch1:{query}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if res.returncode != 0:
            print("     yt-dlp search failed:", res.stderr[:200])
            return False
        stream_url = res.stdout.strip().split('\n')[0]
        if not stream_url.startswith("http"):
            return False
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-ss", timestamp,
            "-i", stream_url,
            "-vframes", "1",
            "-q:v", "2",
            out_path
        ]
        ff_res = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=20)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 50000:
            print(f"     Successfully extracted 1080p frame to {out_path}")
            return True
        return False
    except Exception as e:
        print(f"     YouTube frame grab error: {e}")
        return False

# Target catalogs
CATALOG = {
    "01_Adobe_Premiere_Pro_2025": [
        {
            "name": "01_Assembly_and_Project_Bins.png",
            "query": "premiere pro 2024 2025 project panel bins assembly workspace screenshot high resolution",
            "yt_query": "premiere pro 2024 project panel organize bins tutorial",
            "yt_time": "00:02:15"
        },
        {
            "name": "02_Editing_Timeline_Program_Monitor.png",
            "query": "adobe premiere pro 2024 2025 timeline interface tracks program monitor screenshot high resolution",
            "yt_query": "adobe premiere pro 2025 timeline interface full walkthrough",
            "yt_time": "00:03:45"
        },
        {
            "name": "03_Lumetri_Color_Grading_Wheels.png",
            "query": "premiere pro lumetri color panel wheels curves color grading workspace screenshot",
            "yt_query": "premiere pro lumetri color grading tutorial 2024",
            "yt_time": "00:04:20"
        },
        {
            "name": "04_Audio_Essential_Sound_Mixer.png",
            "query": "premiere pro essential sound panel dialogue enhance speech ai track mixer screenshot",
            "yt_query": "premiere pro 2024 enhance speech essential sound tutorial",
            "yt_time": "00:01:50"
        },
        {
            "name": "05_Effect_Controls_and_Keyframing.png",
            "query": "premiere pro effect controls panel keyframes motion opacity masking screenshot",
            "yt_query": "premiere pro effect controls panel keyframing tutorial",
            "yt_time": "00:02:40"
        },
        {
            "name": "06_Captions_Text_Auto_Transcribe.png",
            "query": "premiere pro text panel create captions auto transcribe subtitles screenshot 2024",
            "yt_query": "premiere pro 2024 auto captions text panel tutorial",
            "yt_time": "00:03:10"
        },
        {
            "name": "07_Export_Render_Workspace.png",
            "query": "premiere pro 2024 new export workspace settings format presets screenshot",
            "yt_query": "premiere pro 2024 export settings best quality tutorial",
            "yt_time": "00:02:05"
        },
        {
            "name": "08_AI_Generative_Extend_Features.png",
            "query": "adobe premiere pro 2025 generative extend object addition removal firefly video screenshot",
            "yt_query": "premiere pro generative extend firefly 2024 2025 demo",
            "yt_time": "00:01:15"
        }
    ],
    "02_CapCut_Pro_Desktop": [
        {
            "name": "01_Main_Editing_Timeline_Workspace.png",
            "query": "capcut desktop pro main timeline workspace interface 2024 screenshot",
            "yt_query": "capcut desktop full tutorial 2024 complete guide interface",
            "yt_time": "00:04:10"
        },
        {
            "name": "02_Media_Library_and_Cloud.png",
            "query": "capcut desktop media library brand kit cloud materials screenshot",
            "yt_query": "capcut pc desktop import media brand space tutorial",
            "yt_time": "00:02:30"
        },
        {
            "name": "03_Audio_Vocal_Isolation_and_Noise_Reduction.png",
            "query": "capcut desktop audio inspector vocal isolation noise reduction voice effects pro screenshot",
            "yt_query": "capcut desktop audio vocal isolation noise reduction pro tutorial",
            "yt_time": "00:03:05"
        },
        {
            "name": "04_Text_and_Auto_Captions.png",
            "query": "capcut desktop auto captions subtitles text templates animation screenshot",
            "yt_query": "capcut desktop auto captions tutorial text effects 2024",
            "yt_time": "00:02:50"
        },
        {
            "name": "05_Video_Effects_and_Transitions.png",
            "query": "capcut desktop effects transitions tab body effects 3D zoom screenshot",
            "yt_query": "capcut desktop best effects and transitions tutorial 2024",
            "yt_time": "00:03:40"
        },
        {
            "name": "06_Color_Grading_HSL_Curves.png",
            "query": "capcut desktop color adjustment HSL curves color wheels lut screenshot",
            "yt_query": "capcut desktop color grading HSL curves tutorial 2024",
            "yt_time": "00:04:15"
        },
        {
            "name": "07_Video_Inspector_Mask_and_Cutout.png",
            "query": "capcut desktop video inspector basic cutout mask chroma key retouch screenshot",
            "yt_query": "capcut desktop auto cutout mask chroma key tutorial 2024",
            "yt_time": "00:03:30"
        },
        {
            "name": "08_Speed_Curve_and_Smooth_Slowmo.png",
            "query": "capcut desktop speed curve graph smooth slow motion optical flow screenshot",
            "yt_query": "capcut desktop speed ramping curve smooth slow motion tutorial",
            "yt_time": "00:02:15"
        },
        {
            "name": "09_Export_Settings_4K_60FPS.png",
            "query": "capcut desktop export settings resolution 4k bitrate codec screenshot",
            "yt_query": "capcut desktop best export settings 4k 60fps tutorial 2024",
            "yt_time": "00:01:45"
        },
        {
            "name": "10_AI_Smart_Tools_Script_to_Video.png",
            "query": "capcut desktop ai smart tools script to video auto reframe screenshot",
            "yt_query": "capcut desktop ai features script to video smart tools 2024",
            "yt_time": "00:02:20"
        }
    ],
    "03_DaVinci_Resolve_Studio_19": [
        {
            "name": "01_Media_Page_and_Cloning.png",
            "query": "davinci resolve 19 media page clone tool metadata smart bins screenshot",
            "yt_query": "davinci resolve 19 media page complete walkthrough",
            "yt_time": "00:03:00"
        },
        {
            "name": "02_Cut_Page_Dual_Timeline.png",
            "query": "davinci resolve 19 cut page dual timeline source tape screenshot",
            "yt_query": "davinci resolve 19 cut page fast editing tutorial",
            "yt_time": "00:02:50"
        },
        {
            "name": "03_Edit_Page_Timeline_Inspector.png",
            "query": "davinci resolve 19 edit page timeline inspector smart trim screenshot",
            "yt_query": "davinci resolve 19 edit page beginners walkthrough full interface",
            "yt_time": "00:04:30"
        },
        {
            "name": "04_Fusion_Page_Node_Compositing.png",
            "query": "davinci resolve 19 fusion page nodes node graph 3d workspace screenshot",
            "yt_query": "davinci resolve 19 fusion page node tutorial walkthrough",
            "yt_time": "00:03:15"
        },
        {
            "name": "05_Color_Page_HDR_Wheels_Curves.png",
            "query": "davinci resolve 19 color page node tree hdr color wheels curves screenshot",
            "yt_query": "davinci resolve 19 color grading page node tree tutorial",
            "yt_time": "00:05:10"
        },
        {
            "name": "06_Fairlight_Audio_Mixer_Console.png",
            "query": "davinci resolve 19 fairlight audio page mixer channel strips voice isolation screenshot",
            "yt_query": "davinci resolve 19 fairlight audio mixer tutorial",
            "yt_time": "00:03:40"
        },
        {
            "name": "07_Deliver_Page_Render_Queue.png",
            "query": "davinci resolve 19 deliver page render settings youtube tiktok format screenshot",
            "yt_query": "davinci resolve 19 deliver page best render settings tutorial",
            "yt_time": "00:02:25"
        },
        {
            "name": "08_AI_Neural_Engine_Magic_Mask.png",
            "query": "davinci resolve 19 magic mask ai depth map voice isolation ultra beauty screenshot",
            "yt_query": "davinci resolve 19 new ai features magic mask depth map",
            "yt_time": "00:02:45"
        }
    ],
    "04_Final_Cut_Pro_11": [
        {
            "name": "01_Magnetic_Timeline_Workspace.png",
            "query": "apple final cut pro 11 10.8 magnetic timeline workspace interface screenshot",
            "yt_query": "final cut pro 11 new features walkthrough magnetic timeline",
            "yt_time": "00:02:30"
        },
        {
            "name": "02_Video_Inspector_and_Transform.png",
            "query": "final cut pro video inspector transform crop stabilization blend modes screenshot",
            "yt_query": "final cut pro inspector window transform effects tutorial",
            "yt_time": "00:03:10"
        },
        {
            "name": "03_Color_Wheels_and_Curves.png",
            "query": "final cut pro color inspector color wheels curves hue saturation hdr screenshot",
            "yt_query": "final cut pro color grading wheels curves tutorial",
            "yt_time": "00:03:50"
        },
        {
            "name": "04_Audio_Enhancements_and_Voice_Isolation.png",
            "query": "final cut pro audio inspector voice isolation loudness eq audio meter screenshot",
            "yt_query": "final cut pro voice isolation audio enhancements tutorial",
            "yt_time": "00:02:10"
        },
        {
            "name": "05_Magnetic_Mask_AI_Features.png",
            "query": "final cut pro 11 magnetic mask ai object isolation transcribe to captions screenshot",
            "yt_query": "final cut pro 11 magnetic mask tutorial transcribe subtitles",
            "yt_time": "00:03:20"
        },
        {
            "name": "06_Share_and_Export_Settings.png",
            "query": "final cut pro share export destinations apple prores youtube settings screenshot",
            "yt_query": "final cut pro export settings 4k best quality tutorial",
            "yt_time": "00:02:15"
        }
    ],
    "05_Adobe_After_Effects_2025": [
        {
            "name": "01_Main_Composition_and_Timeline.png",
            "query": "adobe after effects 2024 2025 composition timeline layers graph editor screenshot",
            "yt_query": "after effects 2024 full interface walkthrough timeline composition",
            "yt_time": "00:03:30"
        },
        {
            "name": "02_Effect_Controls_and_Keyframing.png",
            "query": "after effects effect controls panel graph editor bezier easing keyframes screenshot",
            "yt_query": "after effects graph editor speed value curve tutorial",
            "yt_time": "00:02:40"
        },
        {
            "name": "03_Roto_Brush_3_AI_Cutout.png",
            "query": "after effects 2024 roto brush 3 ai separation propagating mask screenshot",
            "yt_query": "after effects roto brush 3 new ai tutorial 2024",
            "yt_time": "00:02:15"
        },
        {
            "name": "04_Render_Queue_and_Media_Encoder.png",
            "query": "after effects render queue output module format settings screenshot",
            "yt_query": "after effects render queue best export settings tutorial",
            "yt_time": "00:02:00"
        }
    ]
}

def run():
    total_downloaded = 0
    catalog_report = []

    for category, items in CATALOG.items():
        cat_dir = os.path.join(PICTURE_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)
        print(f"\n=======================================================")
        print(f"Processing Category: {category} ({len(items)} items)")
        print(f"=======================================================")

        for item in items:
            out_file = os.path.join(cat_dir, item["name"])
            print(f"\n[+] Target: {item['name']}")
            
            # Check if already exists and valid
            if os.path.exists(out_file) and os.path.getsize(out_file) > 100000:
                print(f"    Already exists and valid: {out_file} ({os.path.getsize(out_file):,} bytes)")
                total_downloaded += 1
                catalog_report.append((category, item["name"], "Existing", os.path.getsize(out_file)))
                continue

            # Try Bing Search Images first
            saved = False
            img_urls = search_bing_images(item["query"], max_results=12)
            print(f"    Found {len(img_urls)} potential images on web")
            
            for u in img_urls:
                img = download_and_validate(u)
                if img:
                    img.save(out_file, "PNG", optimize=True)
                    print(f"    SUCCESS: Saved {img.size[0]}x{img.size[1]} image from web!")
                    saved = True
                    total_downloaded += 1
                    catalog_report.append((category, item["name"], f"Web {img.size[0]}x{img.size[1]}", os.path.getsize(out_file)))
                    break
                else:
                    time.sleep(0.1)
            
            # If web search didn't yield a pristine HD screenshot, fallback to YouTube frame extraction
            if not saved:
                print("    Web search did not meet HD criteria, falling back to YouTube 1080p frame grab...")
                yt_success = extract_youtube_frame(item["yt_query"], item["yt_time"], out_file)
                if yt_success:
                    saved = True
                    total_downloaded += 1
                    catalog_report.append((category, item["name"], "YouTube 1080p Frame", os.path.getsize(out_file)))
                else:
                    print(f"    WARNING: Could not fetch image for {item['name']}")
            
            time.sleep(0.5)

    print(f"\nFinished collection! Total validated UI screenshots: {total_downloaded}")

if __name__ == "__main__":
    run()
