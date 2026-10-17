# Praxis

**Instructions that can finally see how you're doing.** *AI guidance for the physical world.*

Praxis is a software layer for consumer smart glasses. It recognizes the task you're doing, coaches you step by
step without being asked, catches mistakes as they happen with a specific fix, and asks for a better view when
it isn't sure, instead of guessing.

This repo holds **prototype v0**: a layered, real-time task-state engine evaluated on public first-person
procedural video. Most layers are ours (event detector, task-graph compiler and library, Bayesian state tracker,
calibrated policy, training-ready logs, and a distilled local verifier). The frontier model is one swappable part
of the verifier, and it is called only when something happens.

## Try it: Praxis Studio

```bash
cd prototype
uv run praxis studio
```

This opens <http://127.0.0.1:8800> (keys come from `../.env`; the first start loads the models, about 20 s).

1. **Input.** Choose one:
   - Camera: the Mac webcam, or an iPhone through Continuity Camera, which shows up as a camera. Allow camera access when the browser asks.
   - Upload a video: it plays at real-time speed through the same live loop.
   - A test clip from this Mac.
2. **Task.** Choose one:
   - Auto-recognize: if it can't tell after about 30 s, it asks you what you're doing.
   - What are you doing?: type a short description.
   - Paste instructions: Claude Opus compiles them into a task graph, which takes about a minute and is cached.
   - Pick from the library.
3. **Run.** The video shows the user view (progress, instruction chip, check pulse, mistake and view-request cards), drawn live from the engine's own records.
   - Toggle the engineer panel to see step beliefs, the event detector, verifier calls and policy decisions.
   - Turn spoken coaching on or off.
   - Type in **Change task** if it recognized the wrong task.
4. **Flag** moments with <kbd>W</kbd> ("that's wrong") or <kbd>M</kbd> ("it missed something"), with an optional note.
5. **Stop, then Save or Discard.**
   - Save writes `sessions/<id>/`:
     - `camera.mp4`
     - the run log
     - flags
     - `SUMMARY.md`, with each flag in context, for review
     - a HUD replay MP4 rendered from the log
   - The **Sessions** page replays saved sessions. `sessions/` is gitignored; nothing is kept unless you press Save.

**What works best live**, based on the measured results (`results/RESULTS.md`):
- **One of the 8 library recipes, with a clear view of your hands.** Pinwheels is the easiest at a desk: tortilla, nut butter, jelly, a butter knife and dental floss. Picking the task from the library skips recognition; auto-recognition was right on 73% of held-out clips, with a median time of 40 s.
- **Expected accuracy.** On dataset video, Praxis is on the right step about half the time (54%). It lags a few seconds after you finish a step and sometimes sticks on a step. It catches only a few mistakes, mostly a wrong tool or wrong order for the step it thinks you're on. It asks for a better view when it can't see.
- **Tasks that aren't in the library.**
  - Say or paste what you're doing. From video alone, the draft named 0 of 7 unseen recipes; with a short description it named 5 of 7 (`results/open_set/`).
  - Pasted instructions give the most complete plan.
  - Tracking on these tasks is zero-shot, so expect it to be rougher.
- **Cost.**
  - About $0.12–0.27 per 15 minutes with Opus escalations, measured on the live replay and the evaluation runs. Unchecking Opus (Jev only) cuts it to about $0.02.
  - Each session has a cost cap (default $1). Past it, Studio stops calling models and keeps tracking locally.

## Where things are
| Path | What |
|---|---|
| [`results/RESULTS.md`](results/RESULTS.md) | Every measured result, generated from `results/**/*.json` (nothing typed by hand), plus failure analysis, what didn't work, and limitations |
| [`docs/CLAIMS.md`](docs/CLAIMS.md) | Exact sentences that are safe to say about this prototype, each linked to its source file, plus what **not** to claim |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layer diagram (ours / off-the-shelf / rented-and-swappable), the two-speed design, and the moat |
| [`docs/MODEL_ROADMAP.md`](docs/MODEL_ROADMAP.md) | Per layer: what runs today, what in-house model replaces it, and the data the flywheel already collects |
| [`docs/DATA.md`](docs/DATA.md) · [`docs/GLASSES.md`](docs/GLASSES.md) | Datasets, licenses and splits · what a smart-glasses adapter needs (not tested on hardware) |
| [`prototype/`](prototype/) | The engine (Python), with exact reproduce commands in [`prototype/README.md`](prototype/README.md) |
| [`results/figures/`](results/figures/) | Slide-ready charts generated from the results |
| [`renders/`](renders/) | Showcase clips in the user view and the engineer view, rendered **only from saved run logs** and badged "real model output" |
| `context/`, `prompts/` | The grant application and the build brief |

## See it
- **Renders.** `renders/showcase_*_user.mp4` (what a wearer would see) and `renders/*_engineer.mp4` (under the hood).
  Failure cases are labeled `FAILURE CASE`. The assembly clips (`renders/assembly_*`) are IndustReal toy-car
  assembly with **no ground truth**: qualitative only.
- **Also rendered from logs:** `renders/policy_demo_{novice,expert}_user.mp4` (same clip, two user profiles) and
  `renders/live_replay_user.mp4` (live mode on a recording replayed in real time). The clip, alert and selection
  rule behind every showcase are in `results/renders_index.json`.
- **Local viewer.** Run `cd prototype && uv run python -m praxis.viewer fused`, then
  `cd .. && python3 -m http.server 8765`, and open <http://localhost:8765/renders/viewer/>. The viewer shows the
  video, the synced belief over the task graph, the event log and per-clip metrics.
- **Public site: <https://praxis.monishsaravana.com>.** A static build of the landing page (numbers read from
  `results/metrics.json`), the showcase renders, the 48-clip viewer with its videos, and the saved Studio sessions
  as replays (test-clip sessions only, unless one is named with `--session`). It calls no model. Rebuild and
  publish with `cd prototype && uv run python -m praxis.site build && uv run python -m praxis.site deploy`
  (S3 bucket `praxis-monishsaravana-site` behind CloudFront `E2WTNW9W6MV1LC`; needs the AWS CLI signed in).

## Status and honesty notes
- Every number in the deck or the interview must come from `results/` (see `docs/CLAIMS.md`).
- Not tested on glasses. The input layer is camera-agnostic; `MetaGlassesSource` is a documented stub.
- Live mode was run on a recorded clip replayed at real-time speed, not on a webcam (no camera in this build).
- Open-set drafting (tasks outside the library) works in a first form; on unseen recipes it is much better when
  the person says what they are making (`results/open_set/`).
- Metrics come from CaptainCook4D (cooking). The assembly dataset's labels were unreachable this weekend.
