"""IndustReal (Schoonbeek et al., WACV 2024): egocentric toy-car assembly with procedure-step labels
including execution errors ("Incorrectly installed front bracket"). Apache-2.0.

The official host (4TU.ResearchData) serves per-recording label CSVs only inside large split zips, so we
read just those members over HTTP range requests (no full download). Videos: per-recording mp4s from
`all_rgb_videos.zip` (4TU) or the unofficial HF mirror Zzitang/IndustReal (44 of 84 recordings, byte-identical).
"""
from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path

import httpx

from ..paths import DATA

RAW = DATA / "raw" / "industreal"
ARTICLE = "b008dd74-020d-4ea4-a8ba-7bb60769d224"
API = f"https://data.4tu.nl/v2/articles/{ARTICLE}/files"
LABEL_FILES = ("PSR_labels.csv", "PSR_labels_with_errors.csv", "PSR_labels_raw.csv", "AR_labels.csv")


class HttpRangeFile(io.RawIOBase):
    def __init__(self, url: str, client: httpx.Client):
        self.url, self.c, self.pos = url, client, 0
        r = self.c.head(url, follow_redirects=True)
        r.raise_for_status()
        self.size = int(r.headers["content-length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def readinto(self, b):
        n = len(b)
        if self.pos >= self.size or n == 0:
            return 0
        end = min(self.pos + n, self.size) - 1
        for attempt in range(6):
            try:
                r = self.c.get(self.url, headers={"Range": f"bytes={self.pos}-{end}"}, follow_redirects=True)
                data = r.content
                if len(data) == end - self.pos + 1:
                    break
            except httpx.HTTPError:
                time.sleep(2 * (attempt + 1))
        else:
            raise IOError("range read failed")
        b[:len(data)] = data
        self.pos += len(data)
        return len(data)


def fetch_labels(out: Path = RAW / "labels") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120) as c:
        files = c.get(API).json()
        (RAW / "4tu_files.json").write_text(json.dumps(files, indent=1))
        got = {}
        for f in files:
            name = f["name"]
            if not (name.startswith(("train_", "val_", "test_")) and name.endswith(".zip")):
                continue
            z = zipfile.ZipFile(io.BufferedReader(HttpRangeFile(f["download_url"], c), buffer_size=1 << 20))
            for info in z.infolist():
                base = info.filename.rsplit("/", 1)[-1]
                if base in LABEL_FILES:
                    rec = info.filename.strip("/").split("/")[-2]
                    (out / rec).mkdir(exist_ok=True)
                    (out / rec / base).write_bytes(z.read(info))
                    got.setdefault(rec, []).append(base)
            print(name, "recordings with labels so far:", len(got), flush=True)
        for f in files:
            if f["name"] == "action_recognition_labels.zip":
                (RAW / f["name"]).write_bytes(c.get(f["download_url"], follow_redirects=True).content)
    (RAW / "labels_index.json").write_text(json.dumps(got, indent=1))
    return got


def poll_and_fetch(every_s: int = 300, max_hours: float = 30) -> None:
    t0 = time.time()
    while time.time() - t0 < max_hours * 3600:
        try:
            httpx.head("https://data.4tu.nl/", timeout=20)
            print(time.strftime("%H:%M:%S"), "4TU reachable, fetching labels", flush=True)
            got = fetch_labels()
            print("LABELS_DONE", len(got), flush=True)
            return
        except Exception as e:  # noqa: BLE001
            print(time.strftime("%H:%M:%S"), "4TU not reachable:", type(e).__name__, flush=True)
            time.sleep(every_s)



# ------------------------------------------------------------------------------------------- demo clips
# Without the official labels we can still run the engine on IndustReal video for qualitative assembly
# demos (clearly labeled "no ground truth on this clip"); no IndustReal metric is reported from these.
PROCEDURE_INFO = RAW / "repo" / "PSR" / "procedure_info.json"
DEMO_RECORDINGS = ["08_assy_2_4", "07_assy_2_3", "04_assy_2_1", "08_assy_0_1", "22_assy_2_3"]


def procedure_steps(kind: str = "assy") -> list[dict]:
    """Install steps expected in the assembly ('assy') procedure, in the canonical state order."""
    info = json.loads(PROCEDURE_INFO.read_text())
    key = "expected_in_assy" if kind == "assy" else "expected_in_main"
    return [{"id": f"ir{d['id']}", "name": d["description"], "state_idx": d["state_idx"]}
            for d in info if d[key] and d["install"]]


def demo_clips() -> list[dict]:
    import cv2
    out = []
    for rec in DEMO_RECORDINGS:
        v = RAW / "videos" / f"{rec}.mp4"
        if not v.exists():
            continue
        cap = cv2.VideoCapture(str(v))
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 10.0)
        cap.release()
        out.append({"clip_id": f"ir_{rec}", "dataset": "IndustReal", "task_id": "industreal_assy", "recording": rec,
                    "video": str(v), "start": 0.0, "end": float(dur), "split": "demo_no_gt", "segments": [],
                    "missing_steps": [], "person": rec.split("_")[0]})
    return out


if __name__ == "__main__":
    poll_and_fetch()
