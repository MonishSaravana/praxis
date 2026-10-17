### What the failure examples show (from inspecting the frame strips under `results/figures/failures/`)

These notes come from looking at the example frames listed above, from the task-given run (`fused_oracle`). The counts come from `results/failures.json`.

1. **Visually identical or invisible steps make the belief stick.**
   - In the longest stuck stretches, the step that is happening looks the same as the one Praxis believes.
   - One example is "microwave milk for 1 minute" vs "heat for 1 minute and serve": both are just waiting at the microwave.
   - Another is a step that runs off-camera. The person walks away while the microwave runs, and nothing visible says the step changed.
   - The duration prior eventually moves the belief forward, but slowly.
   - Fix direction: use the timer and appliance state when a step is "wait for X", and let a step end when the camera leaves the work area for a long time.
2. **Joining partway through a recording causes false order alarms.**
   - Clip `12_51_63` starts 63 s into its recording. The person had already rinsed the tomato before the clip began, so when they started slicing, Praxis said "rinse the tomato first".
   - The order check assumes the first step it sees confidently is the first one done. That is right at the true start, wrong when joining mid-task.
   - Fix direction (not applied, since the eval set was already run): when the first confident localization is not a start step, mark its graph ancestors as done before enabling order checks. `assume_done_before` already exists.
3. **Plausible-looking but wrong mistake calls.**
   - A mug with a decorative rim was flagged as "has metal on it, can't go in the microwave". The dataset has no such error.
   - The strong verifier sees something that could be a problem and the mistake library offers it a matching entry.
   - Precision-first thresholds keep these rare. The measured false-alarm rate is in the tables above, generated from
     `results/runs/*.json`.
4. **Fine-grained technique errors are missed at 360p with head motion.**
   - "Cut into chunks instead of slicing" needs a clear look at the cut pieces.
   - Head-mounted 360p frames are small and often blurred at exactly that moment.
   - The ROI-crop experiment (`results/l5/crops_vs_full.json`) tests whether zoomed evidence helps.
5. **Most annotated errors are not visible at all.**
   - Measurement errors (1 tbsp vs ½ tbsp), temperature (hot vs cool water) and preparation substitutions (whole vs skimmed milk) can't be seen from a few frames.
   - They make up most of the missed mistakes by type.
   - Order errors are the type Praxis catches most, through the stateful order check.
