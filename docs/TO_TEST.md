# Tests queued for later

Tests the founder has put off. Each one needs their yes before any download and, after an itemized estimate with a hard
cap, before any paid run. Nothing here can be claimed until it has been run.

## 1. Look-alike re-check on repair footage ("Did you switch to ...?")

Added 2026-10-18. The founder said: "we don't need it right now". Nothing has been downloaded and $0 has been spent.
The feature is `EngineConfig.lookalike_recheck_s` (default off). Its design and the free checks are in `MULTITASK.md`
section 16.

- **Question:** on near-identical repair jobs, does the periodic "which task?" check notice a silent switch to another
  job? And how often does it ask "Did you switch?" when nothing changed?
- **Why it waits:** the feature isn't in the pitch. The checker named the right repair job on only 7 of 13 checks
  (section 12). With 4 splices, one splice moves the result by 25 points.
- **Data:** ENIGMA-51 Train videos only. Never use the test videos 141, 107, 144 and 53. Videos are picked by a fixed
  rule that doesn't look at outcomes: for each procedure, the shortest Train video of at least 20 min with clean labels
  (no more than 2 interactions with the other board, and no more than 2 with the other screwdriver) that handles its own
  board and screwdriver within 150 s. Sets 2 and 3 are the next videos by the same rule. The cut is the first derived
  step end at or after 360 s.

  | Set | hv manual | hv electric | lv electric | lv manual | Download |
  |---|---|---|---|---|---|
  | 1 | 91 (cut 520 s) | 126 (456 s) | 154 (423 s) | 157 (433 s) | 5.46 GB (zip index) |
  | 2 | 74 (590 s) | 104 (516 s) | 105 (450 s) | 146 (365 s) | about 6.0 GB (from duration) |
  | 3 | 58 (592 s) | 55 (412 s) | 83 (476 s) | 92 (457 s) | about 6.5 GB (from duration) |

- **Run, per set:** four single-task jobs (the first 20 min, job given) and four resume splices built like section
  12's: job A up to the cut, then 150 s of job B, then 300 s more of A. The order is hv manual → hv electric → lv
  electric → lv manual → hv manual. Flag on (60 s). Label the results SYNTHETIC splices + PROXY labels.
- **Options:**

  | Splices | Sets | Download | Video-minutes | Estimate | Cap |
  |---|---|---|---|---|---|
  | 4 | 1 | 5.46 GB | 140.5 | about $0.90 | $1.20 |
  | 8 (recommended) | 1–2 | about 11.5 GB | 282.5 | about $1.80 | $2.40 |
  | 12 | 1–3 | about 18 GB | 424.8 | about $2.70 | $3.60 |

  Breakdown for 4 splices: Jev about $0.22; Sol look-alike checks about $0.61, at the $0.0043 per check measured in
  section 12; poor-fit checks about $0.05–0.10. The larger options scale this by video-minutes.
- **Rule, fixed before the run:** keep the defaults if wrong questions on the single-task jobs are at most 2 per hour,
  and the other job is asked about during its 150 s in at least 2 of 4 splices. For 8 or 12 splices the proposal is "at
  least half" (4 of 8, 6 of 12). The founder hasn't approved that scaling yet.
- **Work still to do (free):**
  - Fetch the videos into `data/raw/enigma51/videos_train/`, using the same 6-way ranged download from the dataset zip
    that fetched the test videos.
  - Make `eval/enigma_eval.video_path` look in that folder.
  - Extract features on the local GPU, outside the sandbox: about 1 h per set. Only the first 20 min of each video is
    used.
  - In `eval/enigma_switch.py`, give `_segs` a task-id argument (it currently looks up the test videos only), and add
    a single-task scorer and a train variant of the run.
- **Results:** go in `results/enigma51/` and replace the Status paragraph in section 16.
