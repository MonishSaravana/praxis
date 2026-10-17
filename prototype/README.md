# Praxis prototype v0

**Instructions that can finally see how you're doing.** *AI guidance for the physical world.*

A layered, real-time task-state engine for first-person procedural coaching. See `../docs/ARCHITECTURE.md`
for the layer diagram and `../results/RESULTS.md` for measured results.

## Setup

```bash
cd prototype
uv sync
uv pip install --no-deps "tapnet @ git+https://github.com/google-deepmind/tapnet.git"
```

- **Keys** go in `../.env`, which is gitignored: `ANTHROPIC_API_KEY=...` and `JEV_API_KEY=...` (or
  `TYPESAFE_API_KEY`).
- **Model weights** download once to `../cache/`:
  - SigLIP2, DINOv2 and V-JEPA 2 from Hugging Face. Hub access is then forced offline in `praxis/paths.py`.
  - MediaPipe `hand_landmarker.task` and TAPNext++ `tapnextpp_ckpt.pt` go to `../cache/models/`. The URLs are
    in `../docs/DATA.md`.
- **Mac notes.**
  - MPS (Metal) is unavailable inside the Claude Code sandbox, so GPU commands ran outside it.
  - `praxis/paths.py` forces IPv4-first DNS. On the development network IPv6 was black-holed, which added
    30–40 s to every API call from Python.

## Reproduce

Each command writes JSON under `../results/`. Every number in `RESULTS.md` and `CLAIMS.md` comes from those
files, and `results/metrics.json` lists the source file for each one.

```bash
# M1: data, L1 features, task graphs
uv run python -m praxis.cli manifest                         # 48 eval clips / train / held-out types (data/cc4d/manifest.json)
uv run python -m praxis.cli download --split eval            # GoPro 360p videos (also: --split train / heldout_type)
uv run python -m praxis.perception.bench                     # L1 speed on this Mac -> results/l1/l1_speed.json
uv run python -m praxis.cli features --split train --per-task 3
uv run python -m praxis.cli features --split eval
uv run python -m praxis.cli features --split heldout_type --per-task 2
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.tasks.build_library import build; build()"   # L3 compile
#   new procedures compile with Claude Opus 5.5 by default; the committed graphs were compiled with Fable 5.1
#   (pass model="claude-fable-5-1" to reproduce them exactly; existing graphs are skipped unless overwrite=True)
uv run python -m praxis.smoke                                 # Jev image-input probe -> results/l5/jev_image_probe.json

# Fast layers (train split only)
uv run python -m praxis.experiments l2                        # L2 event detector -> results/l2/
uv run python -m praxis.experiments probes                    # L4 step probes + L3b recognizer + backbone quality -> results/l1/
uv run python -m praxis.experiments tune                      # L4 tracker temperatures (leave-one-recording-out) -> results/l4/

# Verifier checks (GT-labeled), calibration, Jev vs Claude, framing, crops, uncertainty, distillation
uv run python -c "from praxis.experiments import build_check_sets; build_check_sets()"
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.experiments import run_checks; [run_checks(k, s) for k in ('jev','claude_fast','claude_strong') for s in ('train','eval')]"
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.experiments import framing_ablation; framing_ablation()"
uv run python -c "from praxis.eval.report_l5 import main; main()"           # calibration + comparisons -> results/l5/
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.experiments import crops_vs_full; crops_vs_full()"
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.experiments import visual_uncertainty; visual_uncertainty()"
uv run python -c "from praxis.experiments import distill; distill()"        # L7 -> results/l7/distill.json

# Design selection (train split only; results/dev/design_selection_*.json, final_design.json)
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.experiments import dev_eval; dev_eval()"

# Engine runs (each writes runs/<variant>/<clip>.jsonl and results/runs/<variant>.json)
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.eval.run_all import run_variant; run_variant('fused')"
#   variants: fused, fused_oracle, fused_heuristic_gate, fused_claude_fast, local_only, verifier_only,
#             fused_distilled, fused_distilled_alone, fused_no_escalation
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.eval.run_all import run_baseline; run_baseline()"
uv run python -m praxis.eval.semantic_match fused_oracle fused baseline_stateless fused_no_escalation fused_claude_fast fused_distilled
#   strict mistake scoring: an Opus judge checks each time-matched alert -> results/l6/mistake_semantic_<run>.json
uv run python -c "from praxis.experiments import adaptive_detail; adaptive_detail('fused')"
uv run python -c "from praxis.experiments import recognition_summary; recognition_summary('fused')"
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.experiments import join_mid_task; join_mid_task()"
uv run python -m praxis.failures fused_oracle                 # failure analysis -> results/failures.json + example frames

# Demos (qualitative; each writes results/<demo>.json and renders/*.mp4)
uv run python -m praxis.industreal_demo                       # assembly, no ground truth
uv run python -c "from praxis.paths import load_env; load_env(); from praxis.personalization_demo import main; main('10_18_0', t0=80, t1=135)"

# Live mode: a camera, or a recording replayed at wall-clock speed (frames the loop can't keep up with are dropped)
uv run python -m praxis.live --source webcam:0 --seconds 120
uv run python -m praxis.live --source replay:../data/raw/cc4d/videos/10_18_360p.mp4@0 --seconds 150 --name live_replay_10_18_0 --no-speak
uv run python -c "from praxis.live import render_replay; render_replay('live_replay_10_18_0', '10_18_0', 16, 112)"
#   -> results/live/<name>.json (loop timing, dropped frames, what Praxis said) and renders/live_replay_user.mp4

# Report, figures, renders, viewer
uv run python -m praxis.spend                                 # results/spend.json (recorded costs only)
uv run python -m praxis.report                                # results/metrics.json
uv run python -m praxis.make_figures                          # results/figures/*.png
uv run python -m praxis.write_results                         # results/RESULTS.md and docs/CLAIMS.md
uv run python -m praxis.make_renders                          # renders/*.mp4 (from run logs only) + results/renders_index.json
uv run python -m praxis.viewer fused                          # renders/viewer/*.html
cd .. && python3 -m http.server 8765                          # open http://localhost:8765/renders/viewer/ (needs the videos locally)
```

## Layout
- `praxis/io` (L0)
- `praxis/perception` (L1)
- `praxis/events` (L2)
- `praxis/tasks` (L3 compiler, L3b recognizer, schema)
- `praxis/state_tracker.py` (L4) and `praxis/evidence.py` (L4 local evidence)
- `praxis/verify` (L5)
- `praxis/policy` (L6)
- `praxis/flywheel` (L7)
- `praxis/engine.py` (wiring), `praxis/runlog.py`, `praxis/render`, `praxis/eval`, `praxis/live.py`
