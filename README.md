# Praxis

**Instructions that can finally see how you're doing.** *AI guidance for the physical world.*

Praxis is a software layer for consumer smart glasses. It recognizes the task you're doing, coaches you step by
step without being asked, catches mistakes as they happen with a specific fix, and asks for a better view when
it isn't sure, instead of guessing.

This repo holds **prototype v0**: a layered, real-time task-state engine evaluated on public first-person
procedural video. Most layers are ours (event detector, task-graph compiler and library, Bayesian state tracker,
calibrated policy, training-ready logs, and a distilled local verifier). The frontier model is one swappable part
of the verifier, and it is called only when something happens.

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

## Status and honesty notes
- Every number in the deck or the interview must come from `results/` (see `docs/CLAIMS.md`).
- Not tested on glasses. The input layer is camera-agnostic; `MetaGlassesSource` is a documented stub.
- Live mode was run on a recorded clip replayed at real-time speed, not on a webcam (no camera in this build).
- Open-set drafting (tasks outside the library) works in a first form; on unseen recipes it is much better when
  the person says what they are making (`results/open_set/`).
- Metrics come from CaptainCook4D (cooking). The assembly dataset's labels were unreachable this weekend.
