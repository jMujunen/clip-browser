import datetime
import os
from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory
from flask.wrappers import Response

app = Flask(__name__)
ROOT_CLIPS_PATH = Path("/mnt/hdd/.webcam/")
SUB_DIR_TEMPLATE = "%Y/%m/%d"


@app.route("/")
def index() -> str:
    """List all clips in the directory."""
    # Get current date and time
    now = datetime.datetime.now()
    # Create a path to the directory for the current date
    CLIPS_PATH_TODAY = ROOT_CLIPS_PATH / now.strftime(SUB_DIR_TEMPLATE)
    # List only .mp4 files
    try:
        clips = [f for f in os.listdir(CLIPS_PATH_TODAY) if f.endswith((".mp4", ".mkv"))]
        clips.sort(reverse=True)  # Newest first
    except FileNotFoundError:
        clips = []
    return render_template("index.html", clips=clips)


@app.route("/clips/<filename>")
def get_clip(filename: str) -> Response:
    """Get a clip by its filename.

    Args:
    ----
        filename (str): The name of the clip.
    """
    now = datetime.datetime.now()
    CLIPS_PATH_TODAY = ROOT_CLIPS_PATH / now.strftime(SUB_DIR_TEMPLATE)
    try:
        return send_from_directory(CLIPS_PATH_TODAY, filename)
    except FileNotFoundError:
        abort(404)


@app.route("/clips/<filename>/download")
def download_clip(filename: str) -> Response:
    """Download a clip by its filename."""
    now = datetime.datetime.now()
    CLIPS_PATH_TODAY = ROOT_CLIPS_PATH / now.strftime(SUB_DIR_TEMPLATE)
    try:
        return send_from_directory(CLIPS_PATH_TODAY, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
