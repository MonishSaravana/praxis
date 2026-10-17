# Data

All ground truth comes from public dataset annotations; nothing was labeled by us. Raw video, extracted
features and checkpoints stay under `data/` (gitignored). The committed per-clip manifest, with clip windows
and GT counts, is `results/data/eval_manifest_summary.json`.

## What we used

### CaptainCook4D (primary; all metrics)
- **What it is.** Egocentric (head-mounted GoPro) recordings of people following recipes, with step
  segments (start/end in seconds) and per-step error labels. Error categories are Preparation,
  Measurement, Order, Timing, Technique, Temperature, Missing Step and Other, each with a free-text
  description. Each recipe also has a task graph (ordering constraints between steps).
- **Access.** Public; no form or login.
  - Videos: GoPro 360p mp4 per recording, via the official downloader's Box static links
    (`CaptainCook4D/downloader/metadata/download_links.json`).
  - Annotations: GitHub `CaptainCook4D/annotations`.
- **License.**
  - Dataset: Apache-2.0 (stated in the dataset README).
  - Annotations repository: MIT. **Neither is non-commercial.**
  - Collection was IRB-approved (per the README).
- **Citation.** Peddi et al., *CaptainCook4D: A dataset for understanding errors in procedural activities*,
  arXiv:2312.14556 (2023).
- **Subset.**
  - **Eval: 48 clips from 8 recipes (procedure types), 234.9 min.**
    - Recipes: Tomato Mozzarella Salad, Spiced Hot Chocolate, Breakfast Burritos, Microwave Egg Sandwich,
      Pinwheels, Microwave Mug Pizza, Herb Omelet with Fried Tomatoes, Cucumber Raita. These are the
      shortest recipes that each have ≥4 official test recordings.
    - Six recordings per recipe come from the official *test + val* recordings (combined recording split).
      Selection is seeded: at least one recording without a timed error, the rest with errors.
    - Each clip is ≤5 min. When the recording has a timed error, the window starts 75 s before the first one
      (or at 0 if that is earlier than 45 s); otherwise it starts at 0.
    - The clips contain 302 annotated step segments and 170 timed step errors. 33 of the 48 clips contain at
      least one error.
    - "Missing Step" errors have no time and are excluded from timed mistake metrics (see limitations in
      `results/RESULTS.md`).
  - **Train: official train-split recordings of the same 8 recipes** (full length). Used for the L2 event
    detector, the L4 step probes, the L3b task recognizer, duration priors, mistake hints for the compiler,
    verifier calibration and student distillation. The exact recordings used are logged in the
    `results/` JSON files.
  - **Held-out procedure types: 2 recordings each of Coffee, Mug Cake, Zoodles, Ramen.** These were never
    used to train anything; they test whether L2 generalizes to procedures it has not seen.
- **Train/test hygiene.** Train-split recordings and eval recordings never overlap. Everything learned (L2,
  probes, recognizer, calibration, student, policy thresholds, duration priors, compiler mistake hints)
  sees train-split data only.

### IndustReal (assembly; showcase target, blocked this weekend)
- **What it is.** Toy-car assembly and maintenance on a HoloLens 2: RGB 1280×720 at 10 fps, 84 recordings,
  27 participants. It has procedure-step labels including execution errors ("Incorrectly installed front
  bracket"), plus fine-grained action labels. This is the closest public match to the drone concept video.
- **Access.**
  - Official host: 4TU.ResearchData, no form or login
    (https://data.4tu.nl/datasets/b008dd74-020d-4ea4-a8ba-7bb60769d224).
  - **Status:** data.4tu.nl refused connections from this machine all of Saturday 2026-10-17 (it worked
    briefly that morning for a research probe). A poller (`praxis/data/industreal.py`) keeps retrying and
    fetches only the label CSVs over HTTP range requests when the host is back.
  - An unofficial Hugging Face mirror (`Zzitang/IndustReal`, 44 of 84 videos, byte-identical sizes) has the
    videos but **no labels**. We downloaded it.
  - **We report no IndustReal metric unless the official labels were fetched.** See `results/RESULTS.md` for
    what happened.
- **License.** Apache-2.0.
- **Citation.** Schoonbeek et al., *IndustReal: A Dataset for Procedure Step Recognition Handling Execution
  Errors in Egocentric Videos in an Industrial-Like Setting*, WACV 2024.

## Considered and not used this weekend

| Dataset | Why not now | License |
|---|---|---|
| Assembly101 (+ mistake labels) | Videos need a Hugging Face click-through (auto-approved) and the egocentric views are monochrome; the mistake labels are public on GitHub. A good next step for assembly. | CC BY-NC 4.0 (**non-commercial**) |
| HoloAssist | Public, RGB, assembly-like tasks, but mistakes are sparse in long sessions and videos come inside a 198 GB tar (single sessions are extractable by byte range) | CDLA-Permissive-2.0 |
| EPIC-Tent | Tent assembly with error labels, but 5.6 GB single files and the file server did not answer | UK Non-Commercial Government Licence (**non-commercial**) |
| EgoPER | Requires an email request (OneDrive link, 2-week expiry) | not stated |
| Ego4D / Ego-Exo4D | License approval takes days (excluded by the brief) | |

## Models (frozen, off-the-shelf)
| Model | Use | License |
|---|---|---|
| `google/siglip2-base-patch16-224` | per-frame image + text embeddings | Apache-2.0 |
| `facebook/dinov2-small` | per-frame features (backbone comparison) | Apache-2.0 |
| `facebook/vjepa2-vitl-fpc64-256` | per-window motion-aware clip embedding | MIT |
| MediaPipe HandLandmarker (`hand_landmarker.task`) | hand presence/position/motion | Apache-2.0 |
| TAPNext++ (`google-deepmind/tapnet`, `tapnextpp_ckpt.pt`) | point tracking / ROI crops | Apache-2.0 (code); see repo for weights |
