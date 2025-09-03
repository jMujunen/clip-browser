import datetime
import os
import subprocess
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

ROOT_CLIPS_PATH = Path("/mnt/hdd/.webcam/")
TODAYS_CLIPS_TEMPLATE = "%Y/%m/%d"

app = Flask(__name__)


def ensure_thumbnail(video_path: Path, thumb_path: Path):
    """Generate thumbnail if missing using ffmpeg."""
    if not os.path.exists(thumb_path):
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                f"file:{video_path}",
                "-ss",
                "00:00:01",  # grab a frame at 1s
                "-vframes",
                "1",
                "-vf",
                "scale=320:-1",
                "-n",
                f"file:{thumb_path}",
            ],
            check=False,
        )


def get_clips():
    """List all clips in the directory."""
    # Get current date and time
    now = datetime.datetime.now()
    # Create a path to the directory for the current date
    todays_clips = ROOT_CLIPS_PATH / now.strftime(TODAYS_CLIPS_TEMPLATE)
    try:
        clips = [f for f in os.listdir(todays_clips) if f.endswith((".mp4", ".mkv"))]
        clips.sort(reverse=True)  # Newest first
    except FileNotFoundError:
        clips = []

    for clip in clips:
        full_path = todays_clips / clip
        ensure_thumbnail(
            full_path, Path(todays_clips / "thumbs" / clip.replace(".mp4", ".jpg"))
        )
    return clips


@app.route("/")
def index() -> str:
    # List only .mp4 files
    clips = get_clips()
    return render_template(
        "index.html", date=datetime.datetime.now().strftime("%A %B %d"), clips=clips
    )


# --- API for paginated clips ---
@app.route("/api/clips")
def api_clips():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 3))
    all_clips = get_clips()
    start = (page - 1) * limit
    end = start + limit
    clips = all_clips[start:end]
    return jsonify({"clips": clips, "has_more": end < len(all_clips)})


# --- Serve thumbnails ---
@app.route("/thumb/<path:filename>")
def thumb(filename):
    THUMB_DIR = (
        ROOT_CLIPS_PATH
        / datetime.datetime.now().strftime(TODAYS_CLIPS_TEMPLATE)
        / "thumbs"
    )

    path = os.path.join(THUMB_DIR, filename)
    return send_file(path)


# --- Serve videos with range support ---
@app.route("/video/<path:filename>")
def video(filename):
    now = datetime.datetime.now()
    todays_clips = ROOT_CLIPS_PATH / now.strftime(TODAYS_CLIPS_TEMPLATE)
    path = os.path.join(todays_clips, filename.strip(".video"))
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
