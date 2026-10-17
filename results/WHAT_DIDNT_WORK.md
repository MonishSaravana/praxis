# What didn't work (engineering log, Oct 17–18)

Each item lists the symptom, the cause, and what changed. Numbers cite the files that hold them.

1. **IndustReal (toy-car assembly) labels were unreachable.**
   - Symptom: no assembly metric in this build.
   - Cause: IndustReal's only official host (data.4tu.nl) refused connections from this machine all
     weekend. It answered once, briefly, on Saturday morning during research.
   - What changed:
     - A Hugging Face mirror supplied 44 of the 84 videos, but without labels.
     - Assembly appears only in clearly labeled qualitative demos ("no ground truth on this clip").
     - A poller kept retrying the official labels.

2. **Every API call from Python took 30–40 s.**
   - Cause: IPv6 is black-holed on the development network (VPN). Python tries the AAAA address first
     and waits for a connect timeout. curl's happy-eyeballs hid the problem.
   - Fix: IPv4-first resolution in-process (`praxis/paths.py`). Calls dropped to ~1.3 s (Claude Haiku) and
     ~0.15 s (Jev).

3. **Hugging Face Hub update checks hung model loading.**
   - Symptom: processes sat at 0% CPU for minutes.
   - Fix: run offline from the local cache.

4. **The Mac was swap-bound.**
   - Symptom: 24 GB RAM with ~31 GB of swap in use from other apps. Feature extraction ran at ~0.5×
     real time when contended, versus ~3× uncontended (`results/l1/l1_speed.json`).
   - Response: serialized GPU jobs and limited decode threads.

5. **Verifiers said "in progress" for steps that were visibly done.**
   - Haiku, Sonnet and Opus all answered "in progress" ~90% of the time 1.5 s after an annotated step end.
   - Cause: the expected end state included quality criteria ("uniform slices, clean board"), so the models
     treated imperfect work as unfinished.
   - Fix: prompt v3 separates *whether* a step was done from *how well*; quality problems go to the mistake
     field.

6. **Three recent frames weren't enough evidence.**
   - Head-mounted frames at step ends are often motion-blurred as the person turns away.
   - Fix: sharpness-based keyframe selection plus a temporal span (one frame from ~8–6 s ago and the two
     sharpest of the last 3 s).
   - This raised Opus AUROC 0.775 → 0.864 and Sonnet 0.646 → 0.732, but did nothing for Jev or Haiku
     (`results/l5/framing_ablation.json`).

7. **Small verifiers judge step completion poorly.**
   - On 469 held-out checks, AUROC was Haiku 0.62, Jev 0.70 and Opus 0.84 (`results/l5/verifier_*.json`).
   - Single-moment completion from a few 360p egocentric frames is hard. This is why the state tracker, not
     the verifier, carries step tracking, and why ambiguity escalates to Opus.

8. **TAPNext++ was not usable live on this machine.**
   - At the engine's 4 fps on head-mounted video it lost the points within ~1.5 s.
   - At 10–15 fps it ran at ~0.7 s/frame on a loaded M4 (MPS), roughly 30–60 s per 2 s clip window.
   - Response: crops were computed offline for the crop experiment only. The live path is documented as
     future work (fewer points, CoreML/ANE, or tracking on a server).

9. **The first L2 event detector overfit.**
   - It chose its threshold on its own training data (thr = 0.9) and scored worse than the SSIM heuristic
     on held-out clips (F1 0.04 vs 0.12).
   - Fix: a validation split of train recordings for early stopping and threshold tuning.

10. **Zero-shot task recognition locked onto the wrong recipe within seconds.**
    - Cause: SigLIP2 frame vs. title text matching is too weak.
    - Fix: a typed Jev "which task is this?" check that feeds the recognizer. Praxis announces a task only
      when the latest check supports it.
    - Later, a recognizer trained on only 1–2 recordings per recipe was overconfident and drowned out the
      verifier. Fixed by tempering local evidence per second.

11. **Time on step does not predict errors on CaptainCook4D.**
    - Steps with annotated errors are not slower: median ratio 0.75 vs 0.81, p = 0.92
      (`results/l6/adaptive_detail.json`).
    - Most errors are measurement, order or preparation slips that don't slow people down. Technique,
      temperature and timing errors do show longer ratios.
    - The adaptive-detail logic is kept, because it addresses hesitation, not errors. We do not claim it
      detects mistakes.

12. **An invalid engine run, caught and re-run.**
    - In the first `fused_claude_fast` run (Claude Haiku as the fast tier), every typed "which step?" call raised a
      TypeError, because the Claude localizer didn't accept the mistake-screening argument. That run measured Haiku
      *without* localization.
    - It is kept in `results/invalid_runs/` and labeled. The fixed run replaces it.
    - Similarly, using the distilled student as the *only* fast tier removed localization entirely (the student has no
      localization head). It is reported as `fused_distilled_alone`, next to the intended configuration: the student
      on completion checks plus Jev localization.

13. **The crop experiment deadlocked on the first try.**
    - Two verifier threads shared one TAPNext++ tracker, so each overwrote the other's online tracking state. They
      made no progress for about 40 minutes.
    - Fix: compute crops sequentially with a single tracker and cache them, then run the verifier calls in parallel
      over the cached crops.

14. **Two design-selection processes wrote the same run logs.**
    - Symptom: train-split design-selection logs with interleaved records from two runs.
    - Cause: a `pkill` pattern didn't match the first process, so a restarted run and the old one wrote to the same
      files at once.
    - Fix: the affected runs were deleted and re-run in one process, and run logs are now written atomically
      (temporary file + rename). The re-runs reused cached model answers, so the deleted runs' original API cost is
      listed as untracked in `results/spend.json` rather than estimated.

15. **Point-tracked crops did not help the verifier enough to keep.**
    - On 120 fine-grained eval checks (orientation, alignment, quantity, part identity), Opus with tracked crops
      matched Opus with full frames on accuracy and gained only about 0.01 AUROC (`results/l5/crops_vs_full.json`).
    - TAPNext++ took several seconds per crop on this Mac, and on head-mounted video the points drift off the
      hands quickly.
    - Crops stay off by default. A faster tracker, or crops from hand boxes alone, would be the next thing to try.

16. **Live mode crashed on its first real-time run.**
    - Symptom: a Metal assertion ("A command encoder is already encoding to this command buffer") a few seconds
      in.
    - Cause: the V-JEPA 2 thread and the main loop's SigLIP2 call used the GPU (MPS) at the same time.
    - Fix: one lock around GPU calls. After that, a 151 s real-time replay ran end to end (`results/live/`).
    - Then: verifier calls ran inside the loop, so a frontier-model escalation blocked the fast path for a few
      seconds; frames were dropped and whole ticks skipped meanwhile.
    - Fixed: in live mode the slow path runs on worker threads (`EngineConfig.async_slow_path`). Each answer is
      folded in when it arrives and applied to the tracker at the tick its frames were taken. Before and after on
      the same recording: `results/live/live_replay_10_18_0.json` and `results/live/live_replay_async.json`
      (RESULTS.md, "Live mode").

17. **The first async version announced the task a tick late.**
    - Symptom: in a short smoke run, the recipe was announced one tick later than with model calls inline, although
      the "which task?" answer had come back within milliseconds.
    - Cause: that version applied "which task?" answers at the next tick rather than when they arrived.
    - Fix: every answer, including task checks and open-set drafts, is folded in on the first frame after it
      arrives (`Engine.poll`).

18. **A cached re-run could not show that the evaluation was unchanged.**
    - Symptom: re-running eval clips on the response caches, with no code change, gave different logs and
      different eval scores, and made new paid calls (`results/live/checks/replay_unchanged.json`,
      `cached_rerun_attempt`).
    - Cause: the Jev completion-check cache key included the random per-request ids of the image assets
      (`verify/jev.py`), so those checks never hit the cache, and Jev's answers vary from call to call.
    - What changed: the check (`praxis/eval/replay_check.py`) feeds the engine the answers recorded in the saved
      logs and verifies that it asks the same questions in the same order.
    - Fixed: the key is now built from a copy of the request with each image id replaced by its position, plus the
      image bytes. The request sent to Jev is unchanged (`prototype/tests/test_jev_cache_key.py`).
      - Answers cached under the old key stay unreachable, so the first re-run after the fix asks Jev again.
      - On one eval clip (17_43_0, run three times on the caches, `results/live/checks/cached_rerun.json`): the first
        run asked Jev all 8 of its checks ($0.0009). The second and third answered 8 of 8 from the cache and made
        no calls; before the fix, a cached re-run of this clip answered 0 of 8 from the cache.
      - The second run logged the same records as the first, except that its 8 Jev answers are marked cached at $0.
        The third matched the second record for record.
