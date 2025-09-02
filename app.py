import datetime
import os
from pathlib import Path

from flask import Flask, Response, jsonify, render_template_string, request, send_file

ROOT_CLIPS_PATH = Path("/mnt/hdd/.webcam/")

SUB_DIR_TEMPLATE = "%Y/%m/%d"

TODAYS_CLIPS = ROOT_CLIPS_PATH / datetime.datetime.now().strftime(SUB_DIR_TEMPLATE)

THUMB_DIR = (
    ROOT_CLIPS_PATH / datetime.datetime.now().strftime(SUB_DIR_TEMPLATE) / "thumbs"
)


app = Flask(__name__)

VIDEO_DIR = str(TODAYS_CLIPS)

THUMB_DIR = str(THUMB_DIR)


# --- Utility: list all clips sorted by newest ---
def get_clips():
    return sorted(
        [f for f in os.listdir(TODAYS_CLIPS) if f.endswith(".mp4")], reverse=True
    )


# --- Index page with infinite scroll ---
@app.route("/")
def index():
    clips = get_clips()
    return render_template_string(
        """
    <!doctype html>
    <html>
    <head>
        <title>Camera Clips</title>
        <style>
            body { font-family: sans-serif; background: #f9f9f9; }
            .clip { margin: 20px; display: inline-block; vertical-align: top; }
            video, img { width: 320px; height: auto; border-radius: 8px; }
            #loading { text-align: center; margin: 20px; font-size: 14px; color: #666; }
        </style>
    </head>
    <body>
        <h2>Clips from Today</h2>
        <div id="clips"></div>
        <div id="loading">Loading...</div>

        <script>
        let page = 1;
        const limit = 5;   // clips per batch
        let loading = false;

        async function loadClips() {
            if (loading) return;
            loading = true;
            const res = await fetch(`/api/clips?page=${page}&limit=${limit}`);
            const data = await res.json();

            const container = document.getElementById("clips");
            data.clips.forEach(clip => {
                const div = document.createElement("div");
                div.className = "clip";
                div.innerHTML = `
                    <video controls preload="none" poster="/thumb/${clip.replace('.mp4','.jpg')}">
                        <source src="/video/${clip}" type="video/mp4">
                    </video>
                    <p>${clip}</p>`;
                container.appendChild(div);
            });

            if (data.has_more) {
                page++;
                observer.observe(document.querySelector("#loading"));
            } else {
                document.getElementById("loading").innerText = "No more clips";
            }
            loading = false;
        }

        // IntersectionObserver to detect when #loading comes into view
        const observer = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting) {
                observer.unobserve(entries[0].target);
                loadClips();
            }
        }, { rootMargin: "100px" });

        // Start initial load
        loadClips();
        </script>
    </body>
    </html>
    """,
        clips=clips,
    )


# --- API for paginated clips ---
@app.route("/api/clips")
def api_clips():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 5))
    all_clips = get_clips()
    start = (page - 1) * limit
    end = start + limit
    clips = all_clips[start:end]
    return jsonify({"clips": clips, "has_more": end < len(all_clips)})


# --- Serve thumbnails ---
@app.route("/thumb/<path:filename>")
def thumb(filename):
    path = os.path.join(THUMB_DIR, filename)
    return send_file(path)


# --- Serve videos with range support ---
@app.route("/video/<path:filename>")
def video(filename):
    path = os.path.join(VIDEO_DIR, filename.strip("video"))
    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range", None)
    if not range_header:
        return send_file(path)

    byte1, byte2 = 0, None
    match = range_header.strip().split("=")[-1]
    if "-" in match:
        parts = match.split("-")
        if parts[0]:
            byte1 = int(parts[0])
        if parts[1]:
            byte2 = int(parts[1])

    byte2 = byte2 if byte2 is not None else file_size - 1
    length = byte2 - byte1 + 1

    with open(path, "rb") as f:
        f.seek(byte1)
        data = f.read(length)

    resp = Response(
        data, 206, mimetype="video/mp4", content_type="video/mp4", direct_passthrough=True
    )
    resp.headers.add("Content-Range", f"bytes {byte1}-{byte2}/{file_size}")
    resp.headers.add("Accept-Ranges", "bytes")
    resp.headers.add("Content-Length", str(length))
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
