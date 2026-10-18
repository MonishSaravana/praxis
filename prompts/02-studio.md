# Build brief: Praxis Studio (local test app)

## Why
Right now Monish can only watch pre-rendered clips. Monish wants to **use** Praxis: turn on a camera (Mac webcam, or iPhone through Continuity Camera, which is also the plan for the live interview demo) or upload a video, and watch the real engine coach in real time, with Jev + Claude behind it, and to save any session so Claude can review what went wrong. Interview is **Tuesday Oct 20**; target **usable by Sunday Oct 18 afternoon**.

## What to build
A local web app started with one command (e.g. `uv run praxis studio`), which opens `http://localhost:<port>`. It reads keys from `.env`.

**1. Choose input**
- **Camera:** browser `getUserMedia` with a device picker (Continuity Camera shows up as a camera).
- **Upload a video:** it plays at real-time speed through the **same live loop**. Not an offline batch; it should look and behave live.

**2. Tell it the task (optional)**
- **Auto-recognize** from the library (default).
- **"What are you doing?"** text box.
- **Paste instructions:** steps, recipe, or manual text, compiled to a task graph with the existing L3 compiler (Claude Opus 5.5, cached), with a progress indicator. This is the pitch's "instruction source → task graph" path, so make it first-class.
- **Pick from the library** dropdown.

**3. Run, live**
- Stream frames to the backend over a websocket at roughly 5–10 fps.
- Run the existing **async live engine**: Jev fast tier on the live path, Opus escalations in the background, never blocking the loop.
- Push events back. The browser draws the **user-view HUD** over the live video, in the same visual language as the renders and following the product rules: a small progress pill, a short instruction chip, a subtle check pulse, an amber mistake card, and a view-request card with an arrow. The step graph is never shown in this view.
- Optional spoken coaching via browser `speechSynthesis`, with a toggle.
- An **engineer panel** toggle: step belief over the graph, event-detector trace, verifier calls (model, latency, confidence), policy decisions, and running cost.

**4. Flag problems while it runs**
- A button plus a hotkey for **"That's wrong"**, and another for **"It missed something"**. Each drops a timestamped marker with an optional one-line note.

**5. Save (opt-in) or discard**
- At the end: **Save session** or **Discard**. Saving is never automatic.
- Save writes `sessions/<timestamp>_<task>/` containing: the recorded video (browser `MediaRecorder` upload or server-side frame recording), the run-log JSONL, the task graph used, flags and notes, config/models, and cost.
- Also render a HUD replay MP4 of the session with the existing renderer, from the log.
- `sessions/` must be **gitignored**: this is personal video.
- A **Sessions** page lists saved sessions with replay (video + HUD from the log) and the flags. Reuse the viewer where possible.
- Write a short `sessions/<id>/SUMMARY.md` (task, duration, alerts, flags, cost) so Claude can review a session quickly.

**6. Make it robust**
- Show connection and model status.
- If Jev or Claude errors or times out, degrade gracefully: keep tracking locally and show "verifier offline".
- Add a **per-session cost cap**, default $1, shown live.
- Port binding may need to happen outside the sandbox.

## Rules
- Same integrity rules as the main brief. Everything shown is real engine output, labeled `Praxis prototype v0`, with nothing scripted.
- Keep slow calls off the live path. Real-time feel is the top priority (see the speed/cost preferences: lead with Jev-only on the live path and Opus in the background; low spend; no Fable).
- There's no camera in the build environment. Test the camera path with a looped file or a fake MediaStream, test upload with a CaptainCook4D eval clip, and test paste-instructions with a short non-library task. In the summary, tell Monish exactly what to try with the real camera, and which kinds of tasks are likely to work live and which aren't, based on the measured results (e.g. unknown tasks work much better when you say or paste what you're doing).
- Commit per feature, push after each commit, tag `studio-v0` when usable, and add a "Try it" section to the README.
