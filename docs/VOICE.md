# Voice: what Praxis does today, and what to build next

Written 2026-10-17 for the interview on Tue 2026-10-20. **Nothing in this document was built or paid for.** Spend in
this session: $0 on models and APIs. No installs, no model downloads, no changes under `prototype/` or `results/`. I read
code and logs, rendered existing spoken lines to audio files with the macOS `say` command (silent, free, run once
outside the sandbox because the speech service is blocked inside it), and read public documentation.

**Status (decided 2026-10-17).** Voice input in natural language is **confirmed for the final product and deliberately not built
before the interview**, to save time and tokens. The accurate way to describe it until it has run: *designed, confirmed for the
product, not yet built.*

**How to read the labels.** Every number or claim carries one:

| Tag | Meaning |
|---|---|
| **[M]** | Measured in this session, from the run logs in `runs/`, `sessions/`, or `results/`, or by running `say` |
| **[C]** | Read in the code or in this repo's docs. Not run |
| **[3P]** | Reported by someone else (a vendor, a blog, Meta's or Google's docs). Not checked by us |
| **[I]** | My inference. I say what would confirm it |
| **[P]** | Planned, designed or estimated. Does not exist yet |

Code state: `live.py`, `policy/policy.py`, `policy/user_model.py` and `flywheel/records.py` are unmodified since
commit `79b7add`. `engine.py`, `state_tracker.py` and the Studio files carry uncommitted edits from the praxis-build
session; I read the working tree as it stood on 2026-10-17 evening. Where that matters I say which.

## Summary

- **Praxis speaks and does not listen.** There is no microphone code, no speech-to-text tool on `PATH` or model in the Hugging Face
  cache, and no voice path into the engine [M: searched `prototype/`, `PATH` and the cache; macOS's own system recognizer
  was not checked]. (`sounddevice`, a
  microphone library, is in `uv.lock` only because mediapipe depends on it; nothing imports it.) It already asks three
  questions aloud that cannot be answered by voice: one is rhetorical, the others need a tap or typing (section 1.7).
- **Three audit findings that matter for a demo:**
  1. In all 7 recorded sessions where a task was recognized or described, Praxis logged "Looks like you're making X. Want me
     to walk you through it?" and the first instruction **at the same instant**. Through `live.py` those two `say`
     processes overlap for 2.6-3.6 s of speech in 6 of 7 sessions and 7.1 s in the seventh [M: computed from log times and
     measured durations; whether macOS mixes two `say` processes was not observed].
  2. **Default instructions are long.** 123 of 136 spoken instructions across the 48 eval clips used the long phrasing
     (standard 120 at 20.8 words, novice 3 at 18; about 5 s of speech). Only 13 used the 5.2-word expert phrasing
     (about 1.4 s). "Standard" users get the novice text [M, C].
  3. The "expanded detail" hint speaks **one short sentence, the first sub-step**. The other sub-steps (3.3 on average)
     and the "you'll need" parts line are logged and never spoken, on all 68 hints [M].
- **Delay.** Software from a logged decision to launching `say` is milliseconds (tick p50 7.5 ms, max 0.5 s) [M].
  The delays that matter are before it: a fast-tier "which step?" check lands at p50 0.26 s (n=17) and an escalated check
  at 2.6 s (n=2) [M], and over the 48 offline clips the next step was announced a median 4.3 s after the real
  step ended [M]. How long `say` itself takes to make its first sound was **not** measured; the nearest number I have is
  a 2.1-6.1 s range to render a line to a file, which includes start-up (section 1.5).
- **Voice input design** (section 2): the person never says a step number and doesn't need set phrases: a language model reads
  what they say with the task as context, and a short list of common commands has a fast path. Speech becomes a weighted likelihood in the
  existing tracker, the way a verifier verdict does, plus undo; every utterance becomes a typed label in a new
  `praxis.record/2`. Push-to-talk and a short listening window after Praxis asks something come first; a wake word and
  always-on listening do not. Spoken "skip" has to silence the engine's own "you skipped X" alert.
- **Options** (section 3): Apple's SpeechAnalyzer first for speech-to-text, rules plus a graph slot match for intents
  ($0 per utterance), AVSpeechSynthesizer for output control. Nothing in that table has been run on this M4.
- **Glasses** (section 4): Meta's documented microphone mode drops everything Praxis says to 8 kHz mono, and it has to
  be switched on before the camera stream starts, so it is on for the whole session. No documented way for an app to
  read a tap. Loud plants probably need audio on the technician's own headset and the card as the main channel.
- **Push-to-talk and headsets** (section 6): camera-only Meta glasses have no documented app-readable tap; the Display glasses'
  touchpad does reach an app, as a button on the card. For loud plants, put audio and the mic on the technician's own
  protection headset and make the card the main channel. Whether camera streaming survives a different audio route is
  undocumented, so it's the first hardware test.
- **Always-on AirPods with Praxis filtering for speech meant for it** (section 6.5): not the default. Default to push-to-talk
  plus a seven-second listening window after Praxis asks something; offer always-on as an opt-in for quiet places. I ran the
  real tracker on it and found my own earlier voice weights were too strong (one "done" would have advanced a step), so
  they are lowered. AirPods Pro hearing protection is not something to rely on at work.
- **Before Tuesday** (section 5.2): fix the announce-plus-instruct collision, and put push-to-talk in front of the typed
  paths Studio already has. Everything else waits for praxis-build to commit, and anything that changes the engine goes
  on a separate branch.

---

## 1. Audit: the voice output that exists

### 1.1 What exists

| | `live.py` (`say`) | Praxis Studio (browser) |
|---|---|---|
| Engine | macOS `say -r 190`, one `subprocess.Popen` per line, output discarded [C: `live.py:31`] | `speechSynthesis`, rate 1.05, the browser's default voice [C: `studio/static/app.js:310`] |
| Spoken kinds | `announce_task`, `instruct`, `mistake`, `view_request`, `hint`, `done` [C: `live.py:149`] | Those six at HEAD. The working tree adds `switch_task`, `retract_task`, `resume_task`, `leave_warning` [C: `hud.js`, uncommitted] |
| Silent kinds | `verified` (a pulse in the HUD, never spoken) | Same |
| Queue | None. Every line starts its own process the moment it is logged. Nothing waits for `say` to finish and nothing can stop it [C] | One voice. A line that arrives while one is speaking waits; a **third** non-urgent line is **dropped** (`speechSynthesis.pending`). A `mistake` or `view_request` calls `cancel()` and speaks at once [C: `app.js:306-316`] |
| Off switch | `--no-speak` | The "Speak the coaching" checkbox, on by default [C: `index.html:83`] |
| Also speaks | | "I don't recognize this task yet. What are you working on?" when the task stays unknown [C: `app.js:285`] |

`speak_new()` re-reads the whole run log from disk on every call and speaks whatever it hasn't spoken yet; it is called
after any frame that folded in a model answer and after every 1 s tick [C: `live.py:143-151, 165-170`].

### 1.2 What I measured, and from what

- **7 recorded live sessions with real action records:** four `live.py` replays (`runs/live_replay_async`,
  `live_replay_10_18_0`, `live_smoke`, `live_smoke_async`) and three Studio sessions in `sessions/`.
- **48 offline eval clips**, 234.1 minutes (`runs/fused_oracle/*.jsonl`): same policy, task given. Offline replays at 1 Hz
  ticks, so their line timing is the policy's, not a live loop's.
- **142 distinct lines** rendered with `say -r 190 -o <file>` and timed with `afinfo`: every distinct spoken line in
  those logs, plus six fixed lines from Studio, the engine and the acknowledgements proposed below. This gives each
  line's real spoken length with no audio played.

**What the logs cannot tell us.** The two named `live_replay_*` runs were started with `--no-speak` [C: `prototype/README.md`
lines 79-80]. No log records whether audio played, only which actions the engine decided. Everything about *sound* below
is computed from action times and rendered durations, not heard. Overlap and queueing results are therefore [M] for the
inputs and [I] for what a listener would have experienced.

### 1.3 What gets said, how often, how long [M]

| | Value |
|---|---|
| Spoken lines per minute of work, 48 clips, task given | 0.95 (222 lines in 234.1 min) |
| ...by kind | instruct 136, hint 68, mistake 17, view_request 1; no `announce_task` (task given) and no `done` in these clips |
| Words per line | instruct mean 19.3 (median 20, max 41); hint 7.5; mistake 13.7; view_request 12 |
| Spoken length per line, 222 lines | median 3.6 s, p90 6.1 s, max 10.5 s |
| Speaking rate of `say -r 190` | 0.24 s per word (about 250 words per minute by whitespace count), plus 0.16 s. The `-r` number is nominal |
| Share of session time spent talking, 48 clips | 5.8% (817 s of speech in 234 min) |
| Share of time talking, 7 short live sessions (25-150 s each) | 11.5-21.2%, because announce plus the first instruction come early |
| Time between consecutive spoken lines, 48 clips | median 30 s; 6 of 175 gaps under 3 s; 15 under 6 s |
| `live_replay_async`, 150 s | 6 spoken lines (announce 12 words, five instructions of 15-24 words) plus 1 silent `verified` |

Instruction length matters more than frequency. At the measured cooking pace Praxis talks 5.8% of the time; shorter
steps would raise that share in proportion [I: no maintenance footage exists, and CaptainCook4D step lengths are not a
plant's].

### 1.4 Overlap and pile-up

| Case | Result |
|---|---|
| Announce and first instruction | **Logged at the same timestamp in 7 of 7 sessions** that recognized or were told a task [M] |
| Through `live.py` | Two processes start together. The announce (2.6-6.7 s) overlaps the instruction for **2.6, 2.6, 3.6, 2.6, 3.4, 2.8 and 7.1 s** across the seven sessions [M: computed]. Whether macOS plays two `say` processes at once, as separate processes normally do, was not heard: [I] |
| 48 clips through `live.py` | 9 of 222 lines start before the previous one finished, in 8 of 48 clips; 13.6 s of overlapped speech out of 817 s [M: computed] |
| Same sessions replayed through Studio's rules | No overlap. The first instruction **waits 2.6-6.7 s** behind the announce. In the "garlic zucchini noodles" session a `mistake` at 26.3 s cuts off the first instruction after 1.3 s of ~4.3 s and the second instruction (23.0 s) is dropped, so the person hears the announce, a fragment, and then the correction [I: assumes the browser voice is about as fast as `say`; unmeasured] |
| 48 clips through Studio's rules | 0 lines dropped, 2 cut off, 7 waits (longest 4.0 s) [M: computed, same assumption] |
| A backlog in `live.py` | Not bounded. Three lines logged within a few seconds all start at once. This is rare when the task is known (gaps above) and certain at the start of an auto-recognized session [I] |

One more repeat, unrelated to overlap: in the first Studio session (`..._tomato-mozzarella-salad`) the identical
instruction for step `s125` was logged at 16.3 s and again at 24.0 s. The log shows why: at 24.0 s the engine committed
step `s121` on a `belief_switch` and its next step was `s125` again, so it announced the same step twice 7.7 s apart
[M: log; the session was a wrong-task guess, flagged by the person]. A listener hears the same sentence twice.

### 1.5 Delay from a decision to speech

| Stage | Value | |
|---|---|---|
| Action record written to `say` launched | Same loop iteration. The loop's tick took p50 **7.5 ms**, p95 25 ms, max **490 ms**; folding an async answer p50 0.15 ms [M: `results/live/live_replay_async.json`] | Software only |
| `say` launched to first sound | **Not measured.** Rendering a line to a file took **2.1-6.1 s** (p5-p95; median 2.9 s for lines shorter than 2 s of audio) while other jobs were running on this Mac [M]. That includes process start and finishing the file, so it is a ceiling on start-up, not the start-up. Phase 0 (section 5) measures it by ear | |
| Event to decision, fast tier | `step_choice` landed a median **0.26 s** after its frames (n=17); Jev image checks answered in a median 144 ms (381 calls) [M] | |
| Event to decision, escalated | `verdict` p50 **2.6 s**, slowest 4.8 s (an Opus mistake screen), n=2 in the async replay; Opus image verdicts p50 4.0 s, p95 6.9 s over 351 calls [M] | The slow one is the one that speaks a `mistake` |
| Real step end to Praxis saying so, over 48 offline clips | `verified` or `mistake` after the true end of that step: p50 **1.4 s** (n=64), p95 119 s. Next step announced (commit) after the true end: p50 **4.3 s** (n=114), p95 165 s [M: `results/runs/fused_oracle.json`] | Offline replays, signed, long tail from missed or late steps |

So the number a technician feels is mostly "how long after I finished did it notice", not "how long did `say` take".

### 1.6 How "adapt detail to time on step" shows up in the words

It shows up in two places, and only one changes much [C + M]:

1. **The user model picks phrasing.** `UserModel.skill` starts at 0.5, rises 0.08 on a step finished in under 0.6x the
   typical time, falls 0.08 above 1.6x, falls 0.1 per mistake. Above 0.7 the profile is "expert". **But `Policy.phrase()`
   returns the expert text only for "expert"; "novice" and "standard" both get the novice text** [C: `policy.py:65-67`].
   Across 136 instructions: standard 120 (20.8 words), novice 3 (18 words), expert 13 (5.2 words) [M]. So the words changed on
   about 10% of lines, and the default is the long form. Reaching "expert" takes at least three fast steps in a row.
2. **The hesitation hint.** When time on step passes 1.6x the typical duration (x0.8 for novices, x1.3 for experts), the
   policy says one hint per step. 68 hints in 234 minutes, median ratio at firing 1.9x (smallest 1.58) [M]. **Every
   one of the 68 spoke `substeps[0]` and nothing else**: mean 7.5 words, about 1.9 s. Each node had on average 3.3
   sub-steps and every hint carried a "You'll need ..." parts line in its detail; neither is spoken, because
   `say()` receives only `text` [M, C].

On CaptainCook4D, adaptive detail was **not** associated with annotated errors [C: `CLAIMS.md`], and there is no user
study. Today's wording change is therefore a design choice, not an effect we have shown.

### 1.7 Gaps in what Praxis says

1. **Questions it can't hear the answer to.** (a) "Want me to walk you through it?" is rhetorical: the first instruction is
   logged in the same tick. (b) Studio's "What are you working on?" is answered by typing. (c) The working tree's
   "Coming back to the pinwheels?" is answered by a tap or a typed reply [C: `MULTITASK.md`]. Speaking a question
   and requiring a keyboard is the clearest case for voice input.
2. **`live.py` doesn't speak the new multi-task lines** (`switch_task`, `resume_task`, `leave_warning`,
   `retract_task`): its speak list is the old six [C]. A "Coming back to ...?" question would be asked silently.
3. **`verified` is silent.** The person gets a card flash on a screen and nothing on a screenless pair of glasses.
4. **No cancel in `live.py`.** A `mistake` can't interrupt a sentence already playing and can speak on top of it.
5. **No spoken-fraction record.** If a line is cut off or repeated we can't tell how far it got.
6. **A silent gap while a plan drafts** (about 16 s for an unseen task [C: `CLAIMS.md`]).
7. **The same step announced twice** (section 1.4).

Suggested fixes, in order of value for a demo: merge announce and first instruction into one line (or drop the
rhetorical question); one voice at a time in `live.py`; use the expert length as the default for repeat steps;
speak sub-steps on request; add a `verified` earcon. These are changes for praxis-build, not made here.

### 1.8 What would confirm the inferences

- Two `say` processes overlapping: run two at once on the laptop speakers and listen (15 min, makes sound; Phase 0).
- `say` and Studio voice start-up: time first audio on the speakers, and on the iPhone's Safari (Phase 0).
- The Studio replay results: run a session with speech on and record the screen with audio.

---

## 2. Voice input: design (all [P], nothing here is built)

### 2.1 Principles

1. **No step numbers, no step list.** The person speaks about the work. The engine resolves references against the
   graph it already holds: "done" and "it" mean the step it believes they're on (the tracker's MAP step), "that"
   means the step it last announced, and "the belt" is matched against step names, parts and sub-steps.
2. **Speech is evidence, not truth.** An utterance enters the tracker the way a verifier verdict does: as a weighted
   likelihood. The camera can disagree once, politely. People say "done" early, and recognizers mishear.
3. **Natural language first, with fast paths.** The person talks the way they would to a coworker; they do not learn
   phrases. A language model reads what they said together with the task, and a short list of common commands ("done",
   "next", "repeat that", "stop") has a fast path so those answer instantly and offline. The fast path is a shortcut,
   not a limit on what can be said. (An earlier draft of this document had it the other way round.)
4. **Short in, short out.** Every recognized utterance gets a response in under a second: an earcon or at most
   three spoken words. Nobody should wonder whether they were heard.
5. **Never trap the person.** If the engine can't resolve an utterance it asks one question using step *names*
   ("The belt or the pulley?"), never numbers. If it looks like side talk, it stays silent. A false activation must
   cost nothing.
6. **Local by default.** Speech-to-text on the device. Store the text and the recognizer's confidence. Keep audio only
   through the same opt-in save Studio already has for video.

### 2.2 Pipeline

```
mic -> endpointer (VAD) -> STT (partials + final, confidence) -> Utterance{t0, t1, text, conf}
                                                                     |
        Intent router, language-model first, with fast paths:        v
          T0  fast path: a short list of common commands ("done", "repeat that", "stop")   $0, ~ms, offline
          T1  slot match against the live graph (step names, parts, substeps)              $0, ~ms
          T2/T3  a language model reads the words WITH the task as context and returns a
                 typed answer: Jev typed choice for simple cases, Claude Haiku, or Opus when
                 the answer states something about the work. This handles everything else.
          fall through: ask one question with names, or stay silent
                                                                     |
        Engine.on_utterance(t, intent, slots, conf)                  v
          tracker: observe_* evidence / mark_complete / undo
          policy:  speak / card / stay silent
          run log: `utterance` record -> session record `utterances[]` + `labels[]`
```

**What the language model sees and returns.** It gets the person's words; the task graph's step names, parts and
sub-steps; the tracker's best guess for the current step and its confidence; the last thing Praxis said; and the last few
utterances. It returns a typed answer (the repo already uses this pattern for verifier verdicts and for splitting a
procedure into steps): an `intent` (progress claim, skip, correction, question, plan change, part not found, preference, or
not for Praxis), the steps or parts it refers to, a confidence, and one sentence to say back. The evidence rules still apply
on top (section 6.5.2): the model's reading counts as capped, weighted evidence, because a language model can misread
as well as a recognizer can. This is what lets someone say "I don't want the tomatoes", "use the other knife", "wait, what
was the step before?" or "this seal looks cracked" without learning anything.

Three things already exist and are reused: the typed `describe` message in Studio (`studio/session.py:_describe` and
`_typed_answer`) takes free text and either starts a library task (`match_library`) or drafts a plan; the engine's
`answer_resume(via="tap"|"typed")` takes the "coming back / I'm done" answer; and Studio's `flag` message records "that's
wrong". Speech-to-text in front of those three paths is the smallest possible voice input, and it needs no engine change.

### 2.3 What each utterance does

"Tracker" names the call in `prototype/praxis/state_tracker.py`. The weights are **initial guesses**: there are no voice
sessions yet, so nothing has been fitted. Once there are labeled sessions, fit them with the existing `Calibrator`
(`verify/calibration.py`), the same way the verifier's confidence was calibrated.

**A. Naming the task**

| The person says | Resolves to | Tracker | Praxis says or shows | Label written |
|---|---|---|---|---|
| "I'm replacing the pump seal" / "doing the 500-hour service" | `name_task(text)`. T1 is the existing `match_library` (every content word of a title present, or similarity >= 0.8). No match: the existing drafter | Recognizer posterior bypassed: `start_task(how="described")`. Drafting takes about 16 s [C: CLAIMS.md, 7 of 8 unseen recipes] | "Got it, replacing the pump seal." then the first step. While drafting: "Give me a few seconds to put a plan together." (today there is a silent gap) | `task.how="described"`: a free task label for the clip window. Video alone named 0 of 7 unseen recipes, so these are the missing ground truth for L3b. Unmatched text is a list of procedures customers want |

**B. Progress**

| The person says | Resolves to | Tracker | Praxis says or shows | Label written |
|---|---|---|---|---|
| "done", "finished" | `claim_done(MAP step k)` | `observe_verdict(k, "complete", c=0.8)` at weight 0.5 times the directed-at-Praxis score q (likelihood ratio capped at about 2), **and queue an immediate fast check**; commit when the fused belief clears `verify_conf`. If the camera shows a deviation with p >= `mistake_conf`, object once. *Revised after the test in 6.5.2: the first draft used weight 3, which one utterance could use to advance a step* | Next step, as today | Soft label: person claimed step k complete at t, next to the visual p_complete at t. Fits c |
| "next" | `advance(k)` | Same cap, c=0.7, recorded as `advanced_by_user` | Same | Same, tagged weaker |
| "skip this" | `skip(k)` | No visual evidence. `mark_complete(k)` but recorded as *skipped*, not completed | "Skipping the gasket." (names what was skipped) | Hard label: step skipped. **Must also suppress the engine's own "you skipped X" alert for that step** (`_check_order`, `_order_flagged`), or Praxis argues with a decision the person just made |
| "I already did that" | `retro_done(announced step)` | `observe_verdict(x, "complete", 0.8)` at the same capped weight, plus a check. **Excluded from `UserModel.on_step_done`**: a retroactive claim has no meaningful time-on-step, and it would read as a very fast step and push the person toward terse "expert" phrasing | "Okay. Next: ..." | Label: step was done before it was announced. Counts how often the coach lags the work |

**C. Corrections**

| The person says | Resolves to | Tracker | Praxis says or shows | Label written |
|---|---|---|---|---|
| "No, I'm still on the belt" | `correct_position(X)`: T1 name match, accepted only if the best match clearly beats the second | `observe_step_choice({X: 0.9}, weight=0.5)` (likelihood ratio about 4 against the other steps; weight 4 would be about 100,000), times q, plus a check. If X was already committed or its successor announced, restore the tracker snapshot from before that commit (`state()/set_state()`, which the engine already keeps for task switches) and drop the stale announcement | "Okay, back on the belt." | **Hard label** (t, step X): ground truth for which step the person is on. Also marks the previous `verified` or `instruct` as `retracted_by_user`. Strongest signal in the system |
| "That's wrong" (no step named) | `flag(kind="wrong")` | None. Same as Studio's existing flag button (`flags.json`) | "Noted." | Marks the last spoken line as wrong |

**D. Questions and preferences**

| The person says | Resolves to | Tracker | Praxis says or shows | Label written |
|---|---|---|---|---|
| "Why?" | `ask_why(k)` | None (weak "engaged with k" evidence, c=0.6, weight 1) | One or two sentences. Best: a `why` field written at compile time, so it costs $0 at run time. Otherwise one model call with the step as context | `help_request(why, k)`: which steps people don't understand. Feeds the compiler |
| "What should it look like?" | `ask_endstate(k)` | None | Speak `node.end_state` (already in every graph node [C]); show a reference image on a display. **Zero model calls** | Same kind of label |
| "Repeat that" | `repeat()` | None. Calls `UserModel.on_repeat()`, which exists and is never called today [C] | Replays the last line verbatim from a buffer. A second repeat offers "Want more detail?" | Label: line L was unclear or too fast. Per-line repeat counts |
| "Slower", "faster", "louder" | `tts_rate`, `tts_gain` (+/-15% rate) | None | Applies and confirms with one word | Preference label |
| "More detail", "I've done this before, keep it short" | `set_profile("novice" or "expert")` via `UserModel.fixed_profile` | None | "Okay." Next lines use the other phrasing | **Explicit detail preference**: the first direct supervision for the adaptive-detail rule. Today that rule has no ground truth: it was not associated with annotated errors [C: CLAIMS.md] |
| "What's next?" | `peek_next()` | None | Name of the next step only. The graph stays hidden | None |
| "Quiet", "pause" | `mute(until PTT)` | None | Earcon only | Marks an interruption |

**E. "I can't find X"**

| The person says | Resolves to | Tracker | Praxis says or shows | Label written |
|---|---|---|---|---|
| "I can't find the gasket", "where's the torque wrench?" | `find_part(X)`: T1 match against `parts` of the current and next two steps | `observe_verdict(k, "in_progress", 0.7)` with weight 1, and trigger the hesitation hint now instead of waiting for time on step | Speak `node.view_hint` or a description of the part. Then optionally "Hold it up so I can see it", which runs a localization check on X (SigLIP2 landmark scoring exists in `landmarks.py`; the OWLv2 and Grounding DINO weights in the local cache are not used by any current code) | `part_not_found(X, k)`: (1) vocabulary mismatch, when the shop calls the part something else, which gives synonyms for the compiler; (2) a hard negative for landmark matching, if the frame is kept (opt-in only) |

**G. Anything else, in the person's own words** (language-model path; this is the group the fixed phrases above can't cover)

| The person says | Resolves to | Tracker | Praxis says or shows | Label written |
|---|---|---|---|---|
| "I don't want the tomatoes", "I'm out of nutmeg, can I use cinnamon?" | `plan_change(omit X)` or `plan_change(swap X for Y)` | The steps that use X are marked skipped or changed and the open-step set updates. **New capability:** edit the task graph during a session (re-split only those steps) | "No tomatoes. I'll skip the slicing step." For a swap that isn't in the procedure, say so: "That's not in the procedure; your call." | `plan_change(task, step, item)`: where practice departs from the procedure, which belongs in the system-of-record view |
| "Use the other knife", "how tight should that be?", "what was the step before?" | `question` | None or weak "engaged" evidence | An answer taken from the procedure's own text, or "It doesn't say; check the manual" | Help-request label |
| "This seal looks cracked" | `observation` | None directly. A camera check looks for it; if confirmed it goes through the existing `mistake` path | "Let me look. Hold it up." | Observation label, with the frame if kept (opt-in) |
| A coworker's question, a radio call | `not_for_praxis` | None | Silence | Counts only |

The one limit: an answer that states a specification (a torque value, a clearance, a lockout step) must come from the
uploaded procedure and cite it, and when the procedure doesn't say, Praxis says so instead of answering from the model's
memory (`NEXT.md`, locked procedures). Small talk unrelated to the task is not handled.

### 2.4 Guard-rails on evidence

- **A claim never commits silently against strong visual evidence.** If the verifier says "deviation" at
  p >= `mistake_conf` (0.7) for the claimed step, Praxis says so once ("I still see the old seal on the shaft") and
  then follows the person. It does not repeat.
- **Cap what one utterance can do.** I ran the real tracker (section 6.5.2): at weight 3 one "done" advanced the step from every
  starting belief and switched off the engine's own uncertainty check; at a likelihood ratio of about 2 it can't advance a
  confident belief, and a fast check puts it right. So claims get a ratio of about 2 and corrections about 4, both times
  the directed-at-Praxis score, and every accepted utterance queues a check. These are still guesses, to be fitted.
- **Undo is explicit.** Every state change from speech writes `effect.undone_at` if the person reverses it within 20 s
  ("no, wait"). That reversal rate per intent is the quality metric for the router.
- **Skips and retro claims are tagged in the record**, so the system-of-record view (`MULTITASK.md`) can list steps
  "done", "skipped by the person" and "never done" separately.

### 2.5 Training labels: schema `praxis.record/2` (additive)

`flywheel/records.py` builds a record from the run log's `meta`, `task`, `fast`, `belief`, `verdict`, `event`,
`action`, `tracks` and `commit` kinds. Voice adds a log kind `utterance` and two record sections, and bumps the schema to
`/2`. Old readers ignore the new keys.

```json
"utterances": [{
  "t": 104.2, "t_end": 105.1, "text": "done",
  "asr": {"engine": "apple.speechanalyzer", "conf": 0.93, "latency_ms": 310},
  "intent": "claim_done", "tier": "T0", "slots": {"node": "n4"}, "resolved_by": "map_step",
  "belief_at_t": {"map": "n4", "map_p": 0.62, "p_complete_visual": 0.31},
  "effect": {"tracker": "observe_verdict(n4, complete, 0.85, w=3)", "committed": true, "undone_at": null},
  "talking_over": {"line": "a17", "spoken_frac": 0.4}
}],
"labels": [{"t": 104.2, "kind": "step_complete_claim", "node": "n4", "strength": "soft", "source": "utterance"}]
```

| Label kind | Strength | Trains or calibrates |
|---|---|---|
| `task_named` | hard | L3b task recognition; library gaps |
| `step_correction` | hard | L4 localization; marks the previous action `retracted_by_user` |
| `step_complete_claim` | soft | L5 calibration: P(truly complete given a claim and the visual state) |
| `step_skipped` | hard | Order-check suppression; `missing_steps` ground truth |
| `done_before_announced` | hard | Coach lag |
| `help_request(why / endstate / repeat)` | soft | Compile-time content gaps; line clarity |
| `part_not_found` | soft | Parts vocabulary; landmark negatives |
| `detail_preference` | hard | L6 user model: the missing supervision for adaptive detail |
| `interrupted_at(line, spoken_frac)` | soft | Verbosity: lines people cut off |

Privacy: the record holds text and confidence, not audio. Names heard in speech go through the same redaction pass as
the rest of the privacy plan (`NEXT.md` item 5). Nothing here has been collected from a real person.

How to know it works, before any claim: intent accuracy on a labeled script; right-step resolution accuracy;
reversal rate per intent; time to acknowledge; false activations per hour in the target noise; and, in simulation only,
the change in step accuracy when "done" and "skip" are injected into the 48 eval clips at the dataset's ground-truth
step ends (a simulation, not a user study).

### 2.6 Listening: push-to-talk, listening window, wake word, always on, tap

| Mode | How it starts | For | Against | Verdict |
|---|---|---|---|---|
| **Push-to-talk** | Key, on-screen button, earmuff or headset button | No false activation; works in noise (the person decides); clear for privacy; barge-in is trivial (button down = duck) | A free hand is needed; one more gesture | **First.** Laptop key and on-screen button in Studio, an earmuff button in the field |
| **Listening window** | Opens for ~7 s after any line that asks something ("Coming back to...?", "belt or pulley?", a view request) | Hands-free exactly when an answer is expected; grammar can be tiny (yes / no / done / skip / repeat) | Needs the recognizer awake at those moments; on Meta glasses that means the HFP microphone profile is open (section 4) | **First, alongside push-to-talk** |
| **Wake word** ("Praxis") | On-device keyword spotter | Hands-free, general | Continuous mic; false accepts in machine noise are unmeasured; on Meta glasses the mic stream must be open all session, so it would run on our side of the mic stream (the docs expose no wake word) [C]; see section 6.1 for Meta AI Connectors, an untested alternative | **Later, only if the pilot says push-to-talk is too much friction and a noise test passes** |
| **Always listening** (VAD + STT, no wake word) | Always | Maximum convenience | Worst for noise, privacy (a worker's mic live all shift), battery, and cloud cost if STT is cloud | **Not as the default.** An opt-in mode for quiet places, once false accepts and consent are dealt with (section 6.5) |
| **Tap on the glasses** | Touchpad | Natural | The Meta docs describe a tap as a session control (pause, resume, stop). I found no documented way for an app to read it as an event [3P: DAT docs via search; verify in the API reference]. A tap that pauses the camera stream is not a push-to-talk | **Do not plan on it.** On the Display model a tap on a card button does reach the app, and Neural Band gestures are unconfirmed (section 6.1) |

### 2.7 Barge-in and turn-taking

States: `IDLE`, `SPEAKING`, `DUCKED`, `LISTENING`, `THINKING`.

| What happens | Rule |
|---|---|
| The person starts talking, or presses the button, while Praxis speaks | Duck the voice about 18 dB within one audio buffer (target 20-50 ms [P]). If speech lasts >= 400 ms, or the recognizer returns a word, stop speaking and flush the queue. Pinned lines (see below) excepted |
| Praxis is cut off mid-line | Log `spoken_frac`. This needs word-boundary callbacks: AVSpeechSynthesizer and the browser's `onboundary` give them; `say` started with `Popen` does not (it can only be killed) |
| The interrupted line was a `mistake` or `view_request` | Don't resume the cut-off line (it is stale). After the exchange, allow the policy to say a shortened version once if the condition still holds. Today `Policy.flagged` blocks any repeat of the same mistake, so this needs a "re-flag after interruption" exception |
| Praxis wants to speak while the person is talking | Non-urgent lines wait for the end of speech plus 500 ms. A mistake shows its card at once and speaks at the first gap, at most 2 s later. Praxis never talks over a person for a non-urgent line |
| The utterance was "quiet" or "stop" | Mute until the next push-to-talk |
| Speech with no intent (side talk) | Duck, then resume the same line from the start of the current sentence. No response |
| Echo: open-ear speakers are audible to the mic | Don't count energy during TTS as speech unless echo cancellation is proven on that device. On the phone, iOS voice-processing mode provides it [I: standard behavior; not tested here]. On the Meta HFP route it is undocumented (section 4). Fallback: push-to-talk-only barge-in |
| Safety-pinned lines | A short list (a `mistake` that names a hazard, once the compiler tags it) that is never flushed by side talk, only by the person's own command |

Studio already cancels all queued speech when a `mistake` or `view_request` arrives (`speechSynthesis.cancel()`). That
is output-side priority, not barge-in: nothing listens.

### 2.8 Latency budget

| Stage | Target [P] | What we know |
|---|---|---|
| End of speech detected | 300-500 ms of silence | Unmeasured |
| Speech-to-text, final result | < 300 ms after the endpoint | Unmeasured. A third party reports on-device streaming returns partials while the person talks [3P] |
| T0 / T1 intent | < 10 ms | [I] string and fuzzy matching |
| T2 typed choice (Jev) | < 300 ms | Image checks: **p50 144 ms, 381 calls** [M, `runs/fused_oracle`]. Text-only calls: not tested |
| T3 Claude (Opus) | Only for questions, with "One moment." | Image verdicts: **p50 4.0 s, p95 6.9 s, 351 calls** [M]. A text-only call should be faster; not measured |
| Apply to engine | Immediately, not on the next 1 Hz tick | [C] tick runs once per second; commands should bypass it |
| First audio of the reply | Earcon <= 300 ms; spoken acknowledgement <= 800 ms after the end of speech | See section 1 for what `say` costs |

---

## 3. Options (free and on-device first)

Nothing in this section was run by us except where marked [M]. Third-party figures [3P] come from vendor or blog
benchmarks, mostly on other chips than the M4. They are for ranking, not for quoting.

### 3.1 Speech-to-text

| Option | Where it runs | Cost | Latency | Accuracy and noise | Blockers and notes | Status |
|---|---|---|---|---|---|---|
| **Apple SpeechAnalyzer / SpeechTranscriber** (macOS 26, iOS 26; this Mac runs 26.6.2) | On device, streaming, partial and final results | $0 | Reported ~3x faster than Whisper Small on an M2 Pro [3P]. Streaming partials | One vendor test (Inscribe, LibriSpeech read speech, M2 Pro): WER 2.12% clean, 4.56% on the harder "noisy" split, versus the older SFSpeechRecognizer at 9.02% and 16.25% [3P]. LibriSpeech noise is not machinery noise. Apple published no accuracy numbers. Whisper covers many more languages | Needs the speech-recognition permission once (a click); a ~60-line Swift file; the language model downloads on first use [I: general knowledge of the API, not checked this session] | **Not run.** Best first candidate for iPhone and Mac |
| **SFSpeechRecognizer** (older Apple API) | On device when `requiresOnDeviceRecognition` is set | $0 | n/a | Worse than the above on the same test [3P] | Superseded. Useful only below macOS 26 / iOS 26 | Not run |
| **Browser Web Speech API** (Studio) | Chrome sends audio to Google by default; Safari to Apple unless on-device | $0 | Fast, streaming | Unmeasured | Works in a page with no install, which is why it fits a demo. Needs network and sends audio to a third party, so **not for anything but the demo**. [I: from general knowledge, not checked this session] | Not run |
| **whisper.cpp** (+ Core ML encoder) | Local | $0 | Third-party figures for small models on M-series run from ~10x to ~100x real time; no reliable `small.en` figure on an M4 [3P] | Whisper Small in the same Inscribe test: 3.74% clean, 7.95% on the harder split, as quoted by one write-up; I did not read the original post in full [3P] | Install (brew or build) and a model file (`small.en` ~0.5 GB; `base.en` ~0.15 GB, sizes from memory, check at download). Chunked, so latency is seconds, not milliseconds, unless streamed | Not run. Estimate in section 5 |
| **mlx-whisper** | Local, MLX | $0 | One M4 Max benchmark reports ~98x real time for `whisper-small`; an M1 Max run of the same page shows ~10x, so treat as a range [3P] | Same models as above | `uv pip install mlx-whisper` plus a model download. Python, fits the prototype | Not run |
| **Parakeet TDT 0.6B v3** (`parakeet-mlx`, Core ML ports) | Local | $0 | Reported 32x to 117x real time on Apple chips; the two reports disagree [3P] | LibriSpeech clean WER ~2.3-2.4% (Core ML build, M5 Pro); 6.34% average on NVIDIA's harder leaderboard sets [3P] | Install and a model download of about a gigabyte or more. Not benchmarked as `parakeet-mlx` itself by anyone I found. English plus 24 European languages | Not run |
| **Moonshine** (streaming) | Local, small | $0 | Vendor reports 107 ms (Medium Streaming, MacBook Pro CPU) vs 11.3 s for Whisper Large v3 [3P] | Vendor reports 6.65% WER vs 7.44% for Whisper Large v3 [3P] | Install and a model download. Designed for edge devices, and the closest fit if STT must run on a phone or a glasses-side chip | Not run |
| **Android `SpeechRecognizer`** (on-device) | On the phone | $0 | n/a | n/a | Documented for Android XR glasses, works offline; no wake-word support on that page [3P: developer.android.com] | Not run |
| **Cloud STT** (any vendor) | Their servers | Paid per audio minute | Adds network | Often best in noise | Sends audio off the device, against the privacy stance in `NEXT.md` item 5. Not evaluated, price not checked | Not run |

**Recommendation.** Demo: the browser API behind a push-to-talk button with a typed fallback. First real
implementation: SpeechAnalyzer on iPhone and Mac, because it is $0, streaming, and already on the phone that sits
between Meta's toolkit and our engine. Benchmark one of whisper.cpp / mlx-whisper / Parakeet as the portable
fallback and the Android and server path. Decide with a noise test (section 5, Phase 3), not with this table.

### 3.2 Text-to-speech

| Option | Cost | Control | What we know | Status |
|---|---|---|---|---|
| **macOS `say -r 190`** (today in `live.py`) | $0 | Start and kill a process. No pause, no word callbacks, no ducking | Speaking rate, per-line durations and start overhead: section 1 [M] | In use |
| **AVSpeechSynthesizer** (Apple, in-process on iOS and macOS) | $0 | Pause, stop at a word boundary, **word-boundary callbacks** (for `spoken_frac`), render to a buffer for ducking and for routing to a specific Bluetooth device. Premium and enhanced voices are a download | Same voice family as `say` [I]; the right API for the phone app | Not run |
| **Browser `speechSynthesis`** (Studio today) | $0 | Cancel, `pending`, `onboundary` | Studio logic: section 1 [C] | In use |
| **Kokoro-82M** (MLX or Core ML) | $0 | Whatever we build | Core ML port self-reports 379 ms for a 30 s clip on an M2 Studio; no time-to-first-audio figure found; one report of silent or NaN output with a particular MLX build [3P] | Not run |
| **Piper** | $0 | Whatever we build | Sources disagree: 150-250 ms for a 10-word sentence in one test, ~1.5 s in a vendor benchmark on a PC CPU [3P] | Not run |
| **Cloud neural voice** (the OpenAI credits mentioned in `NEXT.md`, others) | Paid per character; price not checked here | Streaming, high quality | Not evaluated. Needs your approval and an itemized estimate | Not run |

**Recommendation.** The voice matters less than three behaviors we can fix without changing voices: one voice at a
time, shorter default lines, and a stop that works. After those, move the phone app to AVSpeechSynthesizer (word
callbacks, ducking, routing) and judge a neural voice by *time to first audio on 8 kHz*, since that is what Meta's
microphone mode leaves us (section 4).

### 3.3 Intent mapping: cost per utterance

Token assumption for the model rows: a prompt of ~500 input tokens (task title, up to 12 step names, the current step,
the last utterance and a typed schema) and ~60 output tokens. That is an assumption, not a measurement. Prices are the
table in `prototype/praxis/verify/common.py`.

| Tier | What it is | Cost per utterance | Latency | Accuracy | Status |
|---|---|---|---|---|---|
| **T0 phrase table + fuzzy** | A dozen commands and their variants | $0 | ~ms [I] | Unmeasured; fine for a closed set | Not built. `match_library` is the same idea for task names |
| **T1 slot match on the live graph** | Token overlap and similarity against step names, parts and sub-steps | $0 | ~ms [I] | Unmeasured. Step names are domain nouns, so lexical match probably beats embeddings; a test would show | Not built |
| **T1b embedding match with the SigLIP2 text tower** | `SigLIP.texts()` is already loaded for landmarks | $0, no download | ms | Untested for intent: it is an image-text model trained on short phrases, not sentence meaning | Not built |
| **T1c small sentence-embedding model** | e.g. a MiniLM-size model | $0 | ms | Unmeasured | Needs a download (estimate in section 5) |
| **Small local LLM** (1-3B class, MLX) | Typed JSON out | $0 | M4 tokens per second not measured by us | Unmeasured | Needs a download of 1-2 GB and a runtime |
| **T2 Jev typed choice, text only** | Same `/v1/systemone` choice question, no images | **~$0.00002** (500 tokens x $0.042 per M input; output free) [computed] | Image calls: **p50 144 ms** [M] | Text-only use is untested | Needs a few test calls and your approval |
| **Claude Haiku 5.5** | Structured output | **~$0.00008** ($0.10 / $0.50 per M) [computed] | Not measured | Not measured | Needs approval |
| **Claude Sonnet 5.5** | Same | **~$0.0016** ($2 / $10 per M) [computed] | Not measured | Not measured | Needs approval |
| **Claude Opus 5.5** | Same | **~$0.0032** ($4 / $20 per M) [computed]. For scale, measured image verdicts cost **$0.0115 each and took 4.0 s at p50** [M] | Seconds | Not measured | Needs approval |

A 10-minute session with 20 spoken commands costs $0 on T0/T1, about $0.002 on Haiku and about $0.06 on Opus if every
one went to it. For comparison, the engine's measured verifier spend is $0.018 per video minute, so a 10-minute
session is about $0.18. Voice is cheap whichever tier we pick. The reason to avoid Opus is latency, not cost.

**Recommendation (revised).** Language-model first, with fast paths. Cost per utterance is pennies even if *every* utterance
goes to a model (table above), so cost is not a reason to limit what people can say. The reasons for keeping a fast path are
speed (instant "Got it" for "done", "next", "repeat") and working offline. Start with a Claude Haiku-class model for the
typed answer and use Opus only when the answer states something about the work. Test Jev with text only as the cheapest
option (Phase 6, needs your yes). **Speech-to-speech "realtime" voice models**, which listen and talk in one step and handle
interruptions, are a third option I have not evaluated: they send audio to a vendor (workable only with push-to-talk, so audio
exists just while the button is held), their cost per minute is unknown to me, and we lose control of the exact wording of
safety-critical lines. Compare one later.
---

## 4. Hardware notes

### 4.1 Meta glasses (Device Access Toolkit): what the audio documentation says

Source: Meta's "Use device microphones and speakers" page in the toolkit docs, fetched 2026-10-17 [C]. Nothing below was
measured by us; no glasses have been connected to this project.

| | A2DP | HFP |
|---|---|---|
| Direction | Output only | Two-way (this is the microphone) |
| Quality | 44.1 / 48 kHz stereo | **8 kHz mono** |
| Use | Music, media, text-to-speech | Capturing the wearer's voice |

What follows for Praxis:

1. **They are mutually exclusive.** "Activating HFP switches the glasses away from A2DP." While the microphone is open,
   everything Praxis says comes out at 8 kHz mono: telephone quality, in the ear of someone who may be standing next to
   a machine.
2. **Order matters.** HFP must be fully configured *before* the camera stream starts. Starting the stream first "can
   cause the audio route to fail silently." So if we listen at all, HFP is open for the whole coaching session, not
   per utterance. A per-utterance toggle is also unrealistic: Meta's iOS sample waits about two seconds for the HFP
   route to come up.
3. **The microphone is beamformed toward the wearer.** In HFP the glasses isolate the wearer's voice and reduce
   ambient sound, which Meta describes as expected behavior. That helps speech in noise, and it means the stream
   is not a clean record of the room.
4. **An alternative exists, in beta.** Camera-stream audio keeps output on A2DP and delivers 16, 44.1 or 48 kHz PCM with
   timestamps that line up with video. It is not beamformed (ambient sound at natural level), it is only in development
   and beta release channels, and the page says it is not supported in production. That fits a pilot, not a launch.
5. **Not documented (see also section 6):** echo cancellation (does the mic hear the speakers?), microphone latency, and any app-readable
   tap. These decide barge-in and push-to-talk, so they are the first things to measure on hardware.

Three ways to wire it, to test in this order:

| Option | Audio in | Audio out | For | Against |
|---|---|---|---|---|
| **A. HFP all session** | Beamformed glasses mic | 8 kHz mono through the glasses | Production-supported; wearer's voice isolated | Telephone-quality coaching voice; echo and latency unknown |
| **B. Camera-stream audio (beta)** | Unbeamformed 16+ kHz PCM, timestamped | A2DP stereo through the glasses | Good voice out; synchronized with video | Beta and dev channels only; noisy mic |
| **C. Glasses for the camera only; audio on the technician's own headset** | Headset boom mic | Headset | Best in loud places; no HFP penalty on the glasses | Needs the headset; two Bluetooth devices on one phone (untested: whether the stream and a second audio route coexist) |

### 4.2 Loud plants and hearing protection

- **Why it matters.** NIOSH recommends an 85 dB(A) criterion level for hearing-loss prevention programs [3P: CDC / NIOSH
  documents]. Above it, people wear hearing protection. Electronic muffs typically cap what reaches the ear at 82 or
  85 dB(A) [3P]. [I] Open-ear glasses speakers are unlikely to compete with that, and a person wearing muffs over the
  glasses' arms may not hear them at all; no one has measured it here.
- **What I could and couldn't find.** Industrial Bluetooth muffs with noise-cancelling boom microphones exist (3M
  Peltor WS ALERT X, 3M Pro-Comms, Honeywell Howard Leight Sync), some with a push-to-talk button, and one vendor lists an
  NRR of 26 dB for a Pro-Comms model [3P: manufacturer and retailer listings]. I found **no study** of speech
  recognition accuracy through those headsets at 85 dB(A) or above, and **we have measured nothing**.
- **Design consequences.**
  1. In loud areas the screen carries the instruction. On camera-only glasses that means a phone or tablet, or a
     headset route (Option C above).
  2. Push-to-talk beats any always-on listening there, and a button on the headset is the natural trigger.
  3. Lines should be short and interruptible, so a missed one costs little. `repeat` must always work.
  4. Voice is never the only channel for something safety-critical (lockout, torque values). Those get a card and an
     explicit confirmation.
  5. Praxis never speaks over a person, and it should not talk during a loud transient it can't detect: the policy
     can't see danger, so it must not sound like it can.
- **The test that would settle it** (section 5, Phase 3): the same 40 scripted commands, recorded clean and then mixed
  with plant-like noise at 75, 85 and 95 dB(A)-equivalent levels, through each candidate recognizer and each
  microphone path. Free, but it needs downloads, so it waits for your approval.

### 4.3 Screenless glasses, display glasses, and what goes where

Screenless: Ray-Ban Meta, Oakley Meta, Viture Helix (whether outside apps run on it is undocumented), and the first
Samsung Android XR glasses (reported for November 2026, no display) [C: `POSITIONING.md`]. Display: Meta Ray-Ban Display
(a 600x600 display in the right lens; the phone sends a full layout over Bluetooth on every update, and big images
can lag [C: `POSITIONING.md`]). Whether camera streaming and the display can run at the same time is **not documented**
[C: `POSITIONING.md`; my search found nothing either].

Rules for the card: only the Display model has one; the card never shows a step number or the step list; a new card is
sent only on a change (step change, mistake, view request) because every update resends the whole layout; at most
about 12 words plus the step chip. "Fallback" is what a screenless wearer or a loud plant gets instead.

| Action | Spoken (all devices) | Card (Display glasses) | Screenless fallback | Loud-plant fallback |
|---|---|---|---|---|
| `announce_task` | "Looks like you're servicing the pump. Want me to walk you through it?" Shorten to one line, and make the question answerable by voice | Task name chip | Voice only | Chip on phone |
| `instruct` | The step, in the profile's phrasing | Step chip (name, not number) | Voice only | The chip is the instruction. Optional reference image (<= 600x600) |
| `verified` | Silent today. Add a half-second earcon so the person knows the step registered | Brief check pulse | Earcon | Pulse |
| `hint` | Today only the first sub-step. Speak the next sub-step on request ("more detail") | Sub-step list, on request | Voice on request | Card on request |
| `mistake` | The correction, one sentence, interrupts | **Red card** with the fix | Voice only, repeated once if unacknowledged | Card plus a phone vibration |
| `view_request` | "Can you show me the underside?" | Arrow and a few words | Voice only | Card |
| `done` | "All steps complete. Nice work." | Card with the task name | Voice | Card |
| `switch_task`, `resume_task`, `retract_task`, `leave_warning` (working tree, `MULTITASK.md`) | One short line each. `leave_warning` ends in a question the person can answer by voice | Muted chip; two buttons on a phone | Voice | Chip |
| `ask_task` ("What are you working on?") | Spoken, then the **listening window opens** | Prompt chip | Voice | Prompt chip |
| *New:* `ack` | One word or an earcon after every recognized command | None | Earcon | Earcon |
| *New:* `clarify` | "The belt or the pulley?" with names | Two chips | Voice | Chips |
| *New:* `answer` (why, end state, repeat) | `end_state` or the compiled explanation, 1-2 sentences | End-state image or text | Voice | Card |

### 4.4 Other platforms

- **Android XR glasses (Jetpack Projected).** The phone app can use the built-in on-device `SpeechRecognizer`, which
  works offline. Two microphone routes are documented: Bluetooth HFP (single mic) and `AudioRecord` through a projected
  context, which gives the glasses' multiple microphones with denoising and wearer-versus-bystander separation but
  needs permissions scoped to the projected device [3P: developer.android.com]. The ASR page documents no wake-word
  support. Gemini is built in, which is the competitor risk already noted in `POSITIONING.md`.
- **RealWear and similar headsets.** Voice control is their native input [C: `POSITIONING.md`]. Praxis would be an
  ordinary Android app there; its voice input would sit next to the device's own command grammar. Not evaluated.
- **Tablet at the bench.** Earbuds or Bluetooth muffs for audio, a stand mic or the muff boom mic for input, and a full
  screen, so a card is always available. The easiest first environment for voice testing.

---

## 5. Build plan

Hours are for one person working with an AI pair. Cost is paid model/API spend plus hardware. **$0 means no paid call.**
Items that need a download, an install or a paid call are listed with their estimate and wait for your approval; none has
been run.

### 5.1 Phases

| Phase | What | Hours | Cost | Needs your approval | Branch |
|---|---|---|---|---|---|
| **0. Measure what we can for free** | (a) Play `say` lines on the laptop speakers and time first audio; check whether two overlap (15 min, makes sound). (b) Time the browser voice, including on the iPhone's Safari, with a standalone test page (not a Studio session, so no model calls) (30 min). (c) A throwaway Swift file that runs SpeechAnalyzer on a recording, after one permission click (2 h) | 3 | $0 | Only the (a) sound and (c) click | None; scripts outside the repo |
| **1. Fix the output** | One voice at a time; announce and first instruct as one utterance; default line length; a stop; word-boundary callbacks; earcon for `verified`; `live.py` to speak the same kinds as Studio | 5-6 | $0 | No | Can go on `main` after praxis-build commits |
| **2. Voice in, smallest version** | Push-to-talk (key and on-screen button) with the browser recognizer, text into the existing `describe` and `answer` paths; typed fallback stays. Task naming, "I'm done / coming back", "repeat that", "what should it look like" (reads `end_state`) | 6-8 | $0 | No | Separate branch `voice-in` after Phase 1 |
| **3. Intent router and tracker evidence** | T0/T1 router; `observe_utterance`, undo from snapshot, skip tagged and suppressing the order alert, `UserModel.on_repeat`; `utterance` log kind; `praxis.record/2`; tests with scripted utterances | 14-16 | $0 | No | Separate branch `voice-engine`; touches `engine.py`, `state_tracker.py`, `records.py`, which praxis-build is editing |
| **3b. Plan changes by voice** | "I don't want the tomatoes", swaps: edit the task graph during a session by re-splitting only the affected steps; mark them skipped or changed in the record | 6-8 | $0 to build; a few model calls per change at run time, not yet priced | No | `voice-engine` |
| **4. Simulated lift** | Inject "done", "skip" and "already did that" into the 48 eval clips at ground-truth step ends (with delays and a share of wrong claims) and re-run. Measures what voice could add to step accuracy, as a simulation | 4 | Up to **$4.20** if every verifier call misses the cache (234 video minutes x the measured $0.018 per minute [M]); less if the content-keyed cache hits, since evidence injection changes which steps get verified | **Yes: itemized above** | `voice-engine` |
| **5. STT bake-off** | Record 40 scripted commands (15 min of your time), mix with plant noise at 3-4 levels, run Apple SpeechAnalyzer, whisper.cpp `small.en`, mlx-whisper `small.en`, Parakeet, Moonshine. Report word error rate, command accuracy and latency | 8-10 | $0 paid. Downloads: whisper `small.en` ~0.5 GB, `base.en` ~0.15 GB, Parakeet v3 ~1 GB or more, Moonshine small, a noise set such as DEMAND or MUSAN of a few hundred MB, and installs of whisper.cpp, mlx-whisper and parakeet-mlx. **Sizes are from memory; check when downloading** | **Yes: downloads and installs** | `voice-stt` |
| **6. Intent tiers** | Test T2 (Jev, text only) and T3 (Haiku, Opus) on 200 natural-language utterances, including messy ones ("uh, skip the tomato part") | 3 | Haiku ~$0.02, Jev ~$0.004, Sonnet ~$0.32, Opus ~$0.64 for 200 calls [computed from the price table at 500 in / 60 out tokens]. **Propose a $2 hard cap** | **Yes** | `voice-engine` |
| **7. Glasses audio** | A Swift companion for Meta's toolkit: HFP all session vs camera-stream audio vs headset; echo, latency, 8 kHz speech intelligibility, tap availability, stream-plus-HFP ordering, and the six pass/fail tests in section 6.4 (headset route while streaming, headset button, Display "Talk" button, Neural Band, clicker) | 16-24 | Hardware only: Ray-Ban Meta Gen 3 or Oakley (the `POSITIONING.md` price range is $379-499), Ray-Ban Display $799. The application's $2,500 hardware line covers it [C: `POSITIONING.md`] | Hardware purchase | `glasses` |
| **8. Neural voice and AVSpeechSynthesizer** | Phone app on AVSpeechSynthesizer; try Kokoro; measure time to first audio at 8 kHz | 6 | $0 (download size not checked) | Download | `voice-tts` |
| **9. Loud-plant field test** | Scripted commands, push-to-talk and cards in a real plant or a recorded one, with the headsets from section 4.2 | 16+ | Headset prices not checked; plant access | Yes | None |

Order: 0, 1, 2 before Tuesday only if praxis-build is done with Studio (section 5.2). Then 3, 5 and 7 in parallel, 4 once 3
exists, and 6 and 8 whenever. 9 waits for a real site.

### 5.2 Before Tuesday 2026-10-20, and after

Today is Saturday 2026-10-17. praxis-build is editing `prototype/` now, so every code item below waits for that session
to commit, or goes to it as a spec. **Nothing here is claimed until it has run on the demo machine.**

**Safe for the demo (small, $0, reversible):**

1. **Speak less at once.** Make announce and the first instruct one utterance, and keep Studio's one-voice behavior.
   The collision in section 1 is certain; the fix is a few lines. (Phase 1.)
2. **Push-to-talk into the existing typed paths.** A button plus the browser recognizer in front of `describe`: "I'm
   making a pour-over coffee" names the task, and "I'm done" / "coming back" answers a pause. The engine is not
   touched; the typed box stays as a fallback. About 3-4 hours, and the one voice-in feature that is also easy to
   show. Test it on the demo network, because Chrome's recognizer normally needs one [I]. (Phase 2, first half.)
3. **Say less about what hasn't run.** Until item 2 has run live, do not say "Praxis listens". `POSITIONING.md` already
   lists "no voice input yet" as something investors will probe, which is true today.

**After Tuesday:** the intent router, tracker evidence, undo, skip, records `/2`, barge-in, local STT, glasses audio,
neural voice, plant testing.

**Needs a separate branch** (it changes the engine and the training record, and praxis-build is in those files):
Phases 3 and 4; plus 5, 7 and 8 as separate branches because they add dependencies. Merge order: `voice-engine` first.

**Do not put in a live demo:** always-listening, a wake word, barge-in through a microphone that hears its own speaker,
anything on glasses, and any "the person said done, so we advanced" before the evidence path has been tested against
the 48 clips.

### 5.3 Decisions I need from you

1. **Go-ahead for Phase 0(a):** it plays sound on this laptop for about 15 minutes.
2. **Demo surface:** Studio in the browser on the laptop, Studio on the iPhone, or `live.py`? It decides whether Phase 1's
   output fix is for Studio, `live.py`, or both.
3. **Phase 4 cap:** up to $4.20, or a lower hard cap? Say which.
4. **Downloads for Phase 5:** about 2-3 GB of models and a noise set, plus three installs. Approve all, some, or none.
5. **Phase 6 cap:** $2, as proposed?
6. **Push-to-talk first, wake word later:** agreed? (`NEXT.md` recommends the same.)
7. **Default trigger:** push-to-talk plus a listening window (recommended in section 6.5), with always-on filtering as an
   opt-in later? Or do you want always-on first for quiet sites?

---

## 6. Push-to-talk and audio routing: what the docs allow, and the setup I'd use

Added 2026-10-17 after follow-up rounds of reading (6.5 covers always-on AirPods). Same rules as the rest of this document: $0, no installs, no hardware,
nothing run. Every claim carries a tag. **[C]** is something Meta's or Google's documentation says (I read the page or a
summary of it); **[3P]** is a forum thread, news report, vendor sheet or retailer listing; **[I]** is my inference.

### 6.1 What the documentation says

**Is the glasses microphone always on during a camera session, or can the app open and close it?**
The documentation doesn't say. What it does say: microphone input is HFP, streamed to the app as 8 kHz mono, and the
app asks the iOS or Android permission itself [C: Meta, Integration overview and "Use device microphones and speakers"].
Meta's iOS sample starts capture by setting an audio session to `.playAndRecord` with `.allowBluetoothHFP` and an audio-engine
tap, and stops by removing the tap, stopping the engine and deactivating the session [C]. So **our app starts and stops
capture**, but two things are fixed: HFP has to be set up *before* the camera stream starts (otherwise "the audio route
can fail silently") [C], and while HFP is up, the glasses' speakers stay at 8 kHz mono whether or not we're recording
[C: "activating HFP switches the glasses away from A2DP"]. **[I]** Gating capture with push-to-talk protects privacy and
avoids false triggers. It does not give back speaker quality.

**What can trigger push-to-talk?**

| Trigger | What's documented | Verdict |
|---|---|---|
| **Tap on camera-only glasses** (Ray-Ban Meta Gen 3, Oakley) | A tap pauses, resumes or stops the *session* [C: Meta Integration overview]. No raw touchpad or button event for the camera toolkit appears in the overview, the FAQ, or the part of the full docs I read (the first 100,000 of 1.7 million characters) | **No.** A tap that pauses the camera is not push-to-talk |
| **Touchpad on Meta Ray-Ban Display** | "Touchpad interactions are abstracted as tap events and delivered to your app through callbacks"; buttons in the layout have tap handlers [C: Display access overview] | **Yes, as a button on the card.** A "Talk" button; its handler is our phone code, so starting capture is ours to do [I: the docs don't say a handler may open the microphone]. Needs an active display session, and whether the display, camera stream and HFP can all run at once is undocumented [C] |
| **Neural Band gestures** | "The system translates these inputs into actions delivered to your app", with no detail on which gestures [C: Display access overview]. A developer asked on GitHub whether tap and click gestures are exposed and I found no official answer [3P: meta-wearables-dat-android discussion #95]. The web-app path does get Neural Band navigation and selection [C: Meta FAQ], but that is not the camera toolkit | **Unknown.** Ask Meta, then test. Do not plan on it |
| **A button on the phone screen** | n/a | Works on any device; the phone is usually in a pocket. A fallback and the simplest pilot trigger [I] |
| **A cheap Bluetooth clicker** | iOS HID access is "fairly well locked down" outside Apple's accessory program [3P: Apple Developer Forums reply] | **Likely works** if the clicker presents itself as a keyboard or a media remote, which iOS passes to apps through its normal channels [I: general knowledge, not checked]. A $10-30 test |
| **AirPods or headset button through `MPRemoteCommandCenter`** | Events go to the app the system treats as "now playing" [3P: forum threads]. One thread reports that with the `.allowBluetooth` category the headset button stopped reaching the app and with `.allowBluetoothA2DP` it arrived, but then without the headset mic; another reports a change in iOS 17; a third reports that once an app captured the mic, CarPlay re-assigned its transport buttons to call control [3P: Apple Developer Forums] | **Unreliable exactly when we need it**, which is while a Bluetooth headset mic is in use. Test on the target iOS |
| **Android XR glasses** | The camera button arrives at the app as a `TOGGLE_APP_CAMERA` input event; the touchpad arrives as generic motion events (`ACTION_DOWN`, `MOVE`, `UP`). The system keeps some gestures (touch-and-hold launches Gemini; swipe back is "Back") [C: developer.android.com, Developer Preview 4, updated 2026-09-22]. A summary of Google's design guide lists camera-button double-press as available to apps [3P] | **Candidate:** camera button or touchpad tap. Preview API, subject to change |

**Can the iPhone use a separate Bluetooth headset for mic and speaker while the glasses keep streaming the camera?**
Meta's pages say nothing about other Bluetooth audio devices, route conflicts, or which audio features are
unavailable while a session is active ("certain features are unavailable while your session is active", unspecified) [C:
Meta Integration overview, FAQ]. From iOS: the `allowBluetooth` option makes hands-free (HFP) devices available as
inputs; a developer who set a Bluetooth HFP headset as the preferred input saw that same headset reported as both input
and output; another saw the play-and-record category drop A2DP output and fall back to the built-in receiver [3P: Apple
Developer Forums]. **[I]** So a headset whose mic we use will also be where our speech comes out. In a loud plant that
is what we want. It would also mean the glasses are not the audio device at all.

- **Does it avoid the 8 kHz glasses problem?** **[I]** Yes for the glasses' speakers, because they're no longer in the
  audio path. But HFP over the headset has limits of its own. The basic HFP codec is 8 kHz, and many headsets also
  support a 16 kHz wideband mode [I: general knowledge, check per headset]. Pages that are not Apple documentation say iOS 26
  adds a higher-quality Bluetooth recording option for AirPods [3P: unverified]. Expect "telephone to wideband", not hi-fi.
- **Unknown, and the first hardware test:** whether DAT camera streaming runs normally while the iPhone's audio route is a
  different headset. Meta warns that starting the stream before HFP is ready "can cause the audio route to fail silently"
  [C], which suggests the stream is sensitive to the audio route. Nothing documents it either way.
- **Headsets to try.** 3M Peltor WS ProTac XPI: Bluetooth with two-device multipoint, a noise-cancelling boom mic rated
  IP68, a push-to-listen feature for talking to people without removing it, level-dependent listening, and, on the
  "-111" models, a push-to-talk button on the earcup and a radio port. Listings give 26 dB SNR, 30 dB NRR and 32 dB SLC80 for
  different configurations (so check the exact model); one Canadian retailer lists one at CAD 972 [3P: retailer and 3M
  listings]; other prices not checked. Sensear's speech-enhancement headsets are described by a buyer's guide as the strongest choice for very high
  noise and as costing noticeably more; I found no specifications [3P: reliamag buyer's guide]. AirPods Pro for quiet
  places: nothing checked here beyond the iOS routing above.

**Loud environments.**
- OSHA's action level is 85 dBA as an 8-hour average; at that level an employer must run a hearing conservation program
  that includes monitoring, audiograms, **employer-provided hearing protection** and training. The enforceable limit is
  90 dBA, and exposure is computed *without* counting the protector's attenuation [3P: 29 CFR 1910.95 and university
  summaries of it]. On *when it must be worn* (read on the OSHA page, 1910.95(i)): protectors must be made available at no cost from 85 dBA;
  they must be worn by employees who need PPE because exposure exceeds the 90 dBA table limit after controls, and by
  employees at 85 dBA or more who have no baseline audiogram or have had a standard threshold shift [3P: OSHA].
- Typical levels: an old regional survey of 56 Korean factories found 84.5 to 95.6 dBA by sector (shipbuilding loudest),
  and one review puts chemical plants at 85 to 115 dBA [3P: dated and regional, so treat as a rough range].
- What technicians wear: I did not find a survey of maintenance technicians. The evidence I did find is from mining:
  workers "often remove their hearing protectors" because they fear it interferes with communication [3P: NIOSH-linked
  studies], and communication headsets (Peltor, Sensear and similar) exist to prevent that [3P: vendor and buyer's-guide
  pages]. A patent document in the same search notes that workers often lack a free hand for a switch [3P: weak
  source], which argues for a button that can be pressed without letting go of the work, such as an earcup button.

| | Open-ear glasses speakers | Earbuds (AirPods-class) | Hearing-protection comms headset |
|---|---|---|---|
| Quiet bench | Fine for short lines [I] | Fine; best voice quality | Unnecessary |
| Under 85 dBA, no protection required | Audible but easy to miss, and a beamformed glasses mic is the only mic [I] | Good | Overkill |
| 85 dBA and above | **Likely inaudible, and not hearing protection** [I] | **Not hearing protection**; under muffs the seal breaks, and adding sound inside a protector is a safety question for the site [I] | **The right place for audio**: meant to be worn, limits level at the ear, boom mic close to the mouth [3P] |
| Cost, hardware | Included in the glasses | Already owned | CAD 972 for one model at one retailer [3P]; others not checked |

**Android XR and RealWear.**
- Android XR: the built-in on-device `SpeechRecognizer` works offline, and the documented route for the glasses' multiple
  microphones is `AudioRecord` through a projected context with denoising and separation of the wearer from bystanders
  [C: developer.android.com]. Input events: table above. The wearer can turn the display off, so apps must work in
  audio-only mode [3P: summary of Google's docs].
- RealWear Navigator 520: four digital microphones with active noise cancellation, and the maker states voice recognition
  "up to 100 dBA", with the same figure repeated by resellers and a review. Its internal loudspeaker is listed at 94
  dBA. All of that is vendor material; **I found no independent test** of recognition at that level [3P]. Built-in voice
  commands are its normal input [C: `POSITIONING.md`].

### 6.2 Recommended setup, by environment

| | Quiet bench or training lab | Shop floor under 85 dBA | Loud plant, 85 dBA and above |
|---|---|---|---|
| **Audio out** | Earbuds or the tablet's speaker. On Meta camera glasses, the A2DP route (camera-stream audio, beta) for pilots | Earbuds, or open-ear glasses for short lines | **The technician's own protection headset**, connected to the phone. Glasses carry the camera only |
| **Microphone** | The earbuds' mic or the phone/tablet mic | Earbud or glasses mic (beamformed HFP) | **The headset's boom mic** (the closest to the mouth, built for noise) |
| **Trigger** | On-screen button and a listening window after Praxis asks something. Wake word later, only if wanted | Push-to-talk on a button or the Display's "Talk" tap; listening window | **Push-to-talk on the headset's earcup button** (or a Display "Talk" tap). No wake word, no always-on |
| **Screen** | Full tablet screen, or a card | Card on Display glasses; phone otherwise | **The card is the main channel**; voice repeats it. Camera-only glasses are weak here, because nothing can be shown |
| **Line length** | Normal | Short | Eight words or fewer by default; "repeat that" always works; safety-critical steps get a card and a spoken confirmation |
| **Biggest unknowns** | None blocking | Whether the glasses mic is good enough without a headset | Recognition accuracy at 85-95 dBA; whether DAT streaming survives a different audio route; whether the headset's push-to-talk button reaches the app |

### 6.3 Recommended setup, by device

| Device | Setup | Why, and the catch |
|---|---|---|
| **Ray-Ban Meta Gen 3, Oakley Meta** (camera only) | Glasses for the camera; **headset or earbuds for audio** (Option C in section 4.1); trigger on the phone, a clicker, or the headset button | No documented app-readable tap, and the glasses' own mic profile costs speaker quality for the whole session. Use Option A (HFP all session, 8 kHz speech) or B (beta in-stream audio) only when no headset is wanted |
| **Meta Ray-Ban Display** | Same audio setup as above, plus the card; a **"Talk" button on the card** as push-to-talk | The one Meta device where a tap reaches the app. Display, camera and HFP at once is undocumented; every card update resends the whole layout |
| **Android XR audio glasses** (first Samsung pair, reported Nov 2026) | Built-in `SpeechRecognizer` or projected `AudioRecord`; trigger on the camera button or touchpad tap | Preview API. No display, so voice and a phone screen only |
| **Android XR display glasses** (2027) | Same, plus a card | Not shipping |
| **RealWear Navigator 520** | Its own mics and voice commands; Praxis as an Android app | Best on paper for loud plants (vendor 100 dBA claim, display included), about $2,900-3,150 [C: `POSITIONING.md`]; no independent test |
| **Tablet or phone at a bench** | Earbuds or muffs for audio, screen as the card, on-screen push-to-talk | Easiest place to run the first voice tests |
| **Viture Helix** | Not decided | Whether outside apps run on it is undocumented [C: `POSITIONING.md`] |

### 6.4 What this adds to the plan

Add to Phase 7 (section 5.1), each a pass/fail on real hardware:
1. DAT camera streaming with the iPhone's audio route set to a Bluetooth headset (AirPods Pro, then a Peltor-class headset).
2. Whether a headset or earbud button reaches the app while its mic is capturing, under each audio-session category.
3. A "Talk" button on the Display glasses: does a tap start capture, and do display, camera and HFP run together.
4. Whether a Neural Band gesture reaches a DAT app at all.
5. A Bluetooth clicker as push-to-talk.
6. Time to first audio and intelligibility of coaching speech over HFP on the headset, against the glasses' 8 kHz route.
7. With AirPods: can our app force Voice Isolation or read "the wearer is speaking"; does camera streaming keep running (also item 1).
8. A full-shift battery test with the AirPods microphone open.
9. The false-accept test in section 6.5.6: an hour of shop chatter and radio plus scripted commands, through the real filter.

**One correction to section 2.6.** An earlier line said Meta doesn't let apps add their own phrases to its assistant, citing the FAQ
through a search summary. I then read the FAQ page itself: it says nothing about custom voice commands or wake words
[C], so that claim was unsupported and has been removed. The same page does describe "Meta AI Connectors" (you define
actions and Meta AI calls them) and WebMCP for Ray-Ban Display web apps, both in preview and neither stated to work with
the camera toolkit [C]. They are a possible way for "Hey Meta" to reach Praxis, with Meta's wake word and servers in
the path. Unknown, not planned.

### 6.5 AirPods with the microphone always on, and Praxis deciding when it's being spoken to

Monish's idea: no boom-mic headset for everyone; wear AirPods, leave the microphone on, and have the phone work out which
speech is meant for Praxis. Evaluated here as a candidate **default**, not a later option. Tags as above, plus **[M]** for
the one thing I ran this time (read-only, no model calls).

**Plain recommendation.** Do **not** make it the default. Default to **push-to-talk plus a seven-second listening window right
after Praxis asks something**. Offer the always-on filtered mode later as an **opt-in "hands-free" setting for quiet places
and AirPods-class earbuds**, once four things are shown (section 6.5.6). The router and the evidence rules are the same
either way; the trigger is just a setting (`button`, `window`, `gated always-on`), so nothing built for push-to-talk is
wasted. Where the idea is right: most people won't own a boom-mic headset, and in a quiet shop or lab AirPods are the
cheapest good microphone there is.

#### 6.5.1 How Praxis would tell that speech is for it

Every utterance gets a score q between 0 and 1: how likely it is to be meant for Praxis. It would come from these signals.

| Signal | What it tells us | Status |
|---|---|---|
| **Own voice vs. a bystander** | AirPods Pro list dual beamforming microphones, an inward-facing microphone and a speech-detecting accelerometer [3P: Apple's AirPods Pro 3 spec page]. Voice Isolation, a system microphone mode, "prioritises your voice and blocks ambient noises"; for recording apps it needs iOS 26 and is chosen per app in Control Center [3P: Apple support, "Voice Isolation, Wide Spectrum or Automatic Mic Mode"] | Whether our app can force Voice Isolation, or read "the wearer is speaking", is **not documented in what I found**; first AirPods test. **Do not build speaker identification**: a voiceprint is a biometric identifier under Illinois BIPA (written notice and release; $1,000 to $5,000 per violation) [3P: law-firm summaries] |
| **Acoustic and prosody classifier** | Research says speech aimed at a device sounds different (pitch, energy, speaking rate) and reads differently (short, imperative). Reported equal-error rates: about 5.2% for an Amazon classifier combining acoustics and recognizer features, about 4% for an Apple model on button-initiated audio [3P: arXiv 1808.02504; Interspeech 2022] | Home-assistant data, not plant noise. We have **no data of our own**; Phase 3's `utterances[]` would be the first |
| **Recognizer and intent confidence** | The speech-to-text confidence, and how well the text matches a command (T0) or a step name (T1) | Needs the router (Phase 3) |
| **Does it fit the current step?** | "Done" is plausible only if the step has run a while, the belief isn't confident the person has just started, and the camera doesn't disagree. "Skip the gasket" is plausible only if a gasket step is open. This comes from the tracker, not from audio | Free; uses existing state |
| **Listening window** | For ~7 s after Praxis asks something ("Coming back to...?", "belt or pulley?"), anything short and on-topic is accepted | Free |
| **"Praxis, ..."** | An optional spoken name for requests outside the grammar ("Praxis, why?") | Accuracy in noise unmeasured |
| **Length** | Commands are one to four words. A twelve-word sentence is chatter unless the window is open or the name was said | Free |

Rule of thumb: accept when q clears a threshold; the evidence weight is the base weight times q, and the per-utterance
likelihood ratio is capped (next section). A phrase like "done", "next" or "okay" is the dangerous case, because it is
common in shop talk and radio traffic [I]. That is where push-to-talk wins.

#### 6.5.2 How much does "speech is only weighted evidence" protect us? [M]

I took the real `StateTracker` (read-only, as it stands in the working tree) on a real task graph (`cc4d_pinwheels`, the
person on the 4th step) and applied one spoken "done" with the weights I proposed earlier. Script:
`voice-audit/claim_sensitivity.py` in the shared notes folder. "LR" is the likelihood ratio the utterance applies against
"still on this step".

| Belief before | Weights (c, weight → LR) | P(still on step) after one "done" | Most likely step after | Engine's own uncertainty check still fires? | After one calibrated verifier answer "still working on it" |
|---|---|---|---|---|---|
| 0.79 | **0.85, 3 → 182** (my earlier proposal) | **0.02** | **next step** | **No** (entropy 0.04 < 0.15) | 0.84 |
| 0.79 | 0.85, 1 → 5.7 | 0.40 | next step | Yes | 0.99 |
| 0.79 | 0.80, 1 → 4.0 | 0.48 | next step (barely) | Yes | 1.00 |
| 0.79 | 0.70, 1 → 2.3 | 0.62 | same step | Yes | 1.00 |
| 0.79 | **0.80, 0.5 → 2.0** | **0.65** | same step | Yes | 1.00 |
| 0.95 | 0.85, 3 → 182 | 0.10 | next step | No | 0.96 |
| 0.95 | 0.80, 0.5 → 2.0 | 0.91 | same step | No | 1.00 |
| 0.62 (step has run long) | 0.80, 0.5 → 2.0 | 0.45 | next step | Yes | 1.00 |

What this says, plainly:

1. **My earlier weights were too strong, and I'm withdrawing them.** With a weight of 3, one utterance moved the belief
   to "next step" from every starting point, and from a typical mid-step belief it left the tracker so sure that the
   engine's own "uncertain, go check" rule would not fire. One misheard "done" would have advanced the step, silenced the
   self-check, and taken a verifier answer to repair only partly (0.84). Sections 2.3 and 2.4 now use the lower numbers.
2. **With a capped likelihood ratio (about 2), a single utterance can't advance a step the engine is confident about.**
   It bends the belief (0.79 → 0.65), keeps entropy above the engine's check threshold so a verification fires, and one
   fast check puts it back. The protection is *relative*: a stray "done" is absorbed when the engine thinks you're still
   mid-step, and it tips the balance when the step has run long and the belief is already uncertain (the last row). That is
   the behavior we want, because "done" is more likely true when the step has run long.
3. **Every accepted claim should trigger an immediate fast check.** A Jev check answers in a median 144 ms and costs about
   $0.0001 [M: `runs/fused_oracle`], so a wrong claim costs a fraction of a cent and a true one is confirmed in well
   under a second, or in 2.6-4.8 s when the check escalates [M]. The person hears an earcon at once and the next
   instruction after the check.
4. **The limit of this protection.** It bounds the damage of a false accept; it does nothing about *how often* they happen,
   and a "done" that is true but too weak to advance alone makes Praxis feel slow when the camera is also unsure. Both
   are tuned with data we don't have yet. One illustrative number, with an assumption I made up: if 200 bystander
   utterances an hour passed near the wearer and 1% got through as commands, that's two stray nudges an hour, each one
   bounded as above. The 1% is unmeasured.

This test is a one-step toy: no visual evidence streaming in, no policy rules. It shows sensitivity, not a rate.

#### 6.5.3 AirPods specifics

| Question | What I found |
|---|---|
| **Microphone quality in noise** | Hardware: dual beamforming microphones, an inward-facing microphone, a speech-detecting accelerometer; features: Voice Isolation, "Studio-quality audio recording", Conversation Awareness [3P: Apple AirPods Pro 3 specs]. The page gives **no codec or profile information**, only Bluetooth 5.3. I found **no independent measurement** of speech recognition through AirPods in noise. The basic hands-free profile is narrowband (8 kHz) and wideband (16 kHz) is common [I: general knowledge, check]. Pages that aren't Apple's say iOS 26 adds a higher-quality Bluetooth recording option [3P: unverified] |
| **Battery with the microphone on** | AirPods Pro 2: about **4.5 h of talk time** per charge, about 24 h with the case, and 5 minutes in the case gives about an hour of talk [3P: Apple's regional spec pages, via search]. AirPods Pro 3: Apple lists 8 h of *listening* with noise cancelling on and gives no talk-time figure [3P: Apple's spec page]. Always-on voice is "talk" use [I]. So it does not obviously cover an 8-hour shift without a charging break. I found no figure for a microphone that is open but mostly silent |
| **Does the iPhone keep the Meta camera stream running with AirPods as the audio device?** | **Not documented** by Meta, and I found no developer report. A user report says Ray-Ban Meta glasses take over the phone's audio output when connected and redirecting it takes a manual choice [3P: AppleVis forum]. First hardware test |
| **Do AirPods Pro's hearing-protection features count as workplace hearing protection?** | **Unclear. I would not rely on it.** Apple says Hearing Protection can "help protect your hearing in loud environments", with live sports and fitness classes as examples. It is "not suitable for protection against extremely loud impulse sounds" (gunfire, fireworks, jackhammers) or sustained sounds above 110 dBA. Attenuation depends on fit, is estimated using ANSI/ASA S12.68-2007, and the page gives no figure. It never mentions work, workplaces or ear defenders. Availability is limited by country [3P: Apple support page 120850; the October 2024 data sheet is a PDF I couldn't read as text, and the country limit (US and Canada) comes from a search summary of it] |

OSHA 1910.95, read on the OSHA site: protectors must be made available at no cost from an 8-hour average of 85 dBA, and must
be worn by employees required to use PPE under (b)(1) (exposure above the Table G-16 limit, 90 dBA for 8 hours, after
controls) and by employees at 85 dBA or more who have no baseline audiogram or have had a standard threshold shift. The
employer must "evaluate hearing protector attenuation for the specific noise environments in which the protector will be
used" with an Appendix B method, and employees choose from a variety of suitable protectors [C: 29 CFR 1910.95(b), (i), (j)].
Apple makes no occupational claim and gives the employer no attenuation figure to evaluate, so whether a site could accept
AirPods Pro is **the site safety officer's decision**, and nothing here suggests they would. Treat AirPods as unprotected
ears in a plant (section 6.2 stands), and don't wear earbuds under muffs [I].

#### 6.5.4 Privacy and workplace consent

What the design would do:
- **Everything on the device.** Voice detection, speech-to-text and the filter run on the phone, on an on-device
  recognizer. The browser's speech API may send audio to a server and is not acceptable for an always-on mode [I].
- **Keep only accepted intents.** Store the intent, the text of the accepted command and the confidence, as in the
  record sketch in section 2.5. Hold a rolling pre-roll of about three seconds in memory so the start of a command isn't
  clipped. Drop everything else at once: no transcripts of rejected speech, no audio files, nothing sent anywhere. Log
  only counts (rejected utterances per hour) for tuning.
- **No voiceprints.** See 6.5.1.

Why this does not make the consent question go away. I'm not a lawyer and none of this is legal advice:
- **US.** Federal law sets a one-party consent floor, and roughly a dozen states require everyone's consent (one list:
  California, Connecticut, Florida, Illinois, Maryland, Massachusetts, Michigan, Montana, Nevada, New Hampshire,
  Pennsylvania, Washington; lists differ and the Reporters Committee guide I found is the 2012 edition) [3P]. An always-on
  microphone worn by one employee hears coworkers who haven't agreed to anything. Whether on-device processing that records
  nothing counts as "interception" is a legal question I can't answer [I].
- **EU and UK.** Audio of an identifiable employee is personal data, and in Germany works councils have a co-determination
  right over technical systems able to monitor behavior (BetrVG section 87(1) no. 6). A works agreement can't override the
  GDPR [3P: CMS and Mayer Brown summaries; vendor pages discounted]. I did not find anything specific to microphones.
- **Why push-to-talk is easier.** "It listens only while you hold the button, or for a few seconds after it asks you a
  question" is easy to explain, is easy to put in writing, and avoids most of the questions above. Always-on needs written
  notice, legal review and, in unionized or works-council sites, their agreement before any pilot.

#### 6.5.5 Verdict by trigger

| | Push-to-talk + window (**recommended default**) | Gated always-on (opt-in later) |
|---|---|---|
| False accepts | Near zero: the person decides | Unmeasured; "done", "next", "okay" are common words [I] |
| Loud plant | Works with a headset button; the person chooses the moment | Not recommended: no data, and the plant needs the headset route anyway |
| Hands needed | One press; or none inside the window | None |
| Battery on earbuds | Microphone open only briefly if the audio session can be released between windows (unmeasured) | Talk-time drain: about 4.5 h on AirPods Pro 2 [3P] |
| Consent and privacy | Simple to explain | Needs legal and consent work first |
| Hardware | Whatever the person wears plus a button | AirPods-class earbuds, quiet places |
| Needs the router and tracker rules | Yes | Yes, plus the filter and its data |

#### 6.5.6 What would move "gated always-on" from opt-in to default

1. **False accepts per hour measured below a target** in a recorded test: an hour of shop chatter and radio plus the
   wearer's own scripted commands, through the real filter. $0, 3-4 hours, but it needs the Phase 5 downloads, so it waits for your yes.
2. **A site's written consent and legal sign-off.**
3. **Battery:** a full-shift test with the microphone open.
4. **Camera streaming works with AirPods as the audio device** (the first hardware test).

Until then, hands-free is a setting for a quiet bench, not the thing the product depends on.

### 6.6 Glasses for the camera, headset for the voice: the phone is the hub

The setup Monish asked about: the glasses are camera only, a separate headset (AirPods or a protection headset) carries
the voice, and the person presses a button, or toggles, to talk.

```
Meta glasses --(Meta's toolkit over Bluetooth: camera frames)--> iPhone app --(network)--> Praxis engine
                                                                    |   ^                    (laptop or server)
                                      (ordinary Bluetooth audio)    v   |
                                                                 AirPods or protection headset
                                                                 (speech out, microphone in)
```

**Is it possible to build? Yes, and nothing has to be built *between* the glasses and the headset.** They never talk to each
other. The phone talks to each of them. No code of ours runs on the glasses [C: `GLASSES.md`], so there is no way to make
them relay anything anyway. What we build is one iPhone app that:

1. opens the glasses' camera session with Meta's toolkit (documented, version 1.0.1) [C];
2. sets the audio session so the microphone and speaker are the headset (standard iOS; forum threads describe the routing
   calls) [3P: Apple Developer Forums];
3. turns speech into text, sends the text and the camera frames to the engine, and plays the engine's lines to the headset.

Each piece is documented on its own. **The combination is not**: whether camera streaming keeps running while the phone's
audio goes to a different Bluetooth device. The glasses also appear to the phone as an audio device, and a user report says
the phone's audio then goes to them by default, so the app has to choose the headset explicitly [3P: AppleVis]. That is the
first thing to test with real glasses and it is a pass/fail test.

**What can be done before there are glasses.**
- Meta's Mock Device Kit simulates the glasses and streams a camera feed from a file [C: `POSITIONING.md`], so the camera
  half can be built and tested without hardware. What the mock can't show is real Bluetooth coexistence.
- The audio half (headset in, speech to text, speech out) can be built and tried today with AirPods and the phone.
- A rough stand-in for the whole setup before Tuesday: Studio on the Mac with the iPhone as the camera (Continuity Camera)
  and AirPods as the Mac's microphone and speaker [I: system audio settings need checking, since Continuity Camera can
  also offer the phone's microphone]. That shows the voice side, not the glasses.

**Toggle-to-talk.** Press once to start listening; Praxis plays a short tone; the app ends the turn when the person stops
talking (voice-activity endpointing), so there is no second press. Pressing again cancels. The listening window after a
question stays as well. Ways to press, easiest first:

| Press | Notes |
|---|---|
| A button on the phone screen | Works, but the phone is in a pocket |
| **AirPods stem press** | Arrives as a play/pause media command that an app can treat as the toggle [I: general knowledge]. Forum reports say headset buttons stop reaching the app in some microphone modes [3P], so test it |
| A cheap Bluetooth clicker | About $10-30, untested; on a finger or a glove |
| A button on the card (Display glasses only) | A tap on the card reaches the app [C] |
| A button on the protection headset's earcup | For the loud-plant setup; whether it reaches the app is unknown |

**Effort.** The app is Phase 7 in section 5.1 (16-24 hours with hardware). Phase 2 (a browser version on the Mac) is 6-8 hours
and needs no glasses.

---

## Appendix A. Method and what to re-run

All measurements in section 1 come from two throwaway scripts that live outside the repo (copies are in the shared notes
folder under `voice-audit/`):

1. `say_durations.py` reads every `action` record whose kind is one of the six spoken kinds from the seven live logs and
   the 48 `runs/fused_oracle` logs, adds six fixed lines, runs `say -r 190 -o <file> "<text>"` for each distinct text, and
   reads the spoken length with `afinfo`. The wall time of each `say` run is saved too. Output: `say_durations.json`.
2. `analyze.py` replays each log's spoken lines under two output policies using those durations:
   - *`live.py`*: every line starts its own process at its logged time; overlap is the sum of line lengths minus their
     union.
   - *Studio*: one voice; a line that arrives while one speaks waits; a second waiting non-urgent line is dropped;
     a `mistake` or `view_request` cancels everything and speaks now.
   Output: `analysis.json`.

A third script, `claim_sensitivity.py` (section 6.5.2), imports the repo's `StateTracker` read-only, builds a mid-task belief on
`cc4d_pinwheels`, and applies one spoken "done" at several weights; no model calls.

Other numbers are read straight from existing files: `results/live/live_replay_async.json` (tick and answer timing),
`results/runs/fused_oracle.json` (feedback and progress latency, verifier latency), and a pass over the 48
`runs/fused_oracle` logs for line counts, words, profiles and hints, with sub-step and parts-line counts taken from
`prototype/taskgraphs/*.json`.

Limits: the Studio replay assumes the browser voice speaks about as fast as `say -r 190` (unmeasured); the `say`
render times were taken while other sessions were using the machine; the 48-clip results are offline replays; and the
seven live sessions are short (25-150 s) and mostly the same 10_18_0 pinwheels recording.

## Appendix B. Sources for [3P] and documentation claims (all read 2026-10-17)

- Meta, device microphones and speakers (A2DP / HFP, order of setup, camera-stream audio beta):
  <https://wearables.developer.meta.com/docs/develop/dat/microphones-and-speakers/>
- Meta, Device Access Toolkit FAQ and integration overview (session controls by tap, hinge and wear detection; the FAQ does not mention custom voice commands):
  <https://developers.meta.com/wearables/faq> and <https://wearables.developer.meta.com/docs/develop/dat/build-overview/>
  (both read as fetched summaries, not as raw pages)
- Meta Ray-Ban Display opened to developers, two SDK paths, Neural Band input:
  <https://ppc.land/meta-opens-display-glasses-to-developers-with-two-sdk-paths/> (a news report)
- Google, ASR on audio glasses and display glasses; projected context:
  <https://developer.android.com/develop/xr/jetpack-xr-sdk/asr> and
  <https://developer.android.com/develop/xr/jetpack-xr-sdk/access-hardware-projected-context>
- SpeechAnalyzer vs Whisper vs SFSpeechRecognizer (Inscribe test, M2 Pro, LibriSpeech): discussed at
  <https://mjtsai.com/blog/2026/07/22/whisper-and-speechanalyzer/>, which links the original post; I did not read the
  original. Apple's own page <https://developer.apple.com/documentation/speech/speechanalyzer> did not load as text.
- Parakeet and Whisper real-time factors on Apple chips: <https://soniqo.audio/benchmarks>,
  <https://vllm-mlx.is-a.dev/benchmarks/audio/>, <https://github.com/anvanvan/mac-whisper-speedtest>. They disagree with
  each other.
- Moonshine vs Whisper (vendor): <https://moonshine-voice.readthedocs.io/en/latest/moonshine-vs-whisper/>
- Kokoro on Core ML (author's benchmark): <https://huggingface.co/mattmireles/kokoro-coreml>; Piper latency:
  <https://mustafa.net/2026/08/31/piper-review-after-6-months-running-local-tts-in-production/> and
  <https://picovoice.ai/blog/on-device-tts/> (a competitor's benchmark)
- Hearing protection and speech: NIOSH criterion level and electronic hearing protector studies at
  <https://stacks.cdc.gov/view/cdc/161340/cdc_161340_DS1.pdf>; Bluetooth muffs and push-to-talk:
  <https://3m.com/3M/en_US/p/d/v101238225> and
  <https://grouptalk.com/our-solution/latest-news/hearing-protection-with-external-ptt-button>
- Section 6 sources, read 2026-10-17: Meta display access overview
  <https://wearables.developer.meta.com/docs/develop/dat/display-overview/>; Meta integration overview
  <https://wearables.developer.meta.com/docs/develop/dat/build-overview/>; Meta FAQ <https://developers.meta.com/wearables/faq>
  (Connectors and WebMCP); Meta full docs <https://wearables.developer.meta.com/llms.txt?full=true> (first 100,000 of 1.7M
  characters); GitHub discussion <https://github.com/facebook/meta-wearables-dat-android/discussions/95>; Android XR
  physical input <https://developer.android.com/develop/xr/jetpack-xr-sdk/glasses/physical-input>; Apple Developer Forums on
  Bluetooth routing and headset buttons <https://developer.apple.com/forums/thread/62954>,
  <https://developer.apple.com/forums/thread/688838>, <https://developer.apple.com/forums/thread/825736>; OSHA
  <https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95>; noise survey
  <https://search.bvsalud.org/gim/resource/en/wpr-44025> and review <https://agris.fao.org/search/en/records/6759ad2a0ce2cede71ca3031>;
  NIOSH-linked mining studies <https://stacks.cdc.gov/view/cdc/227400>; 3M Peltor WS ProTac XPI listings
  <https://www.dovecom.co.nz/model/ws-protac-xpi-headset/>; Sensear buyer's guide
  <https://reliamag.com/guides/best-industrial-communication-headsets/>; RealWear Navigator 520
  <https://shop.realwear.com/pages/realwear-navigator-520-specifications>.
- Section 6.5 sources, read 2026-10-17: Apple, Hearing Protection on AirPods Pro 2 and 3
  <https://support.apple.com/en-en/120850>; Apple, AirPods Pro 3 specifications <https://www.apple.com/ca/airpods-pro/specs>;
  Apple, Voice Isolation and mic modes <https://support.apple.com/en-my/101993>; Apple's October 2024 Hearing Protection data
  sheet <https://images.apple.com/airpods-pro/pdf/Hearing_Protection_data_sheet_October_2024.pdf> (could not be read as text);
  AirPods Pro 2 talk time from Apple's regional spec pages via search; OSHA 1910.95
  <https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95>; device-directed speech detection:
  <https://arxiv.org/pdf/1808.02504> and <https://machinelearning.apple.com/research/device-directed-speech>; recording-consent
  overview <https://www.rcfp.org/introduction-to-reporters-recording-guide/> (2012 edition); Illinois BIPA and voiceprints
  <https://www.mondaq.com/unitedstates/employee-rights-labour-relations/1811384/the-voiceprint-you-didnt-mean-to-create-what-delgado-v-meta-means-for-employers>;
  German works councils and the GDPR <https://cms.law/en/deu/legal-updates/european-court-of-justice-no-deviation-from-gdpr-standards-via-works-agreements>
  and <https://www.mayerbrown.com/en/insights/publications/2026/10/internal-investigations-role-and-rights-of-employee-representatives>;
  AppleVis thread on Ray-Ban Meta audio routing <https://applevis.com/comment/188901>.
- In this repo: `docs/POSITIONING.md` ("What a technician actually wears", "Voice and screen"), `docs/GLASSES.md`,
  `docs/CLAIMS.md`, `docs/NEXT.md` (item 1), `docs/MULTITASK.md`.

## Appendix C. Claims this document does and doesn't support

**Supports:** Praxis today speaks and does not listen; what it says, how long, how often, and how it adapts, as measured
above; that the announce and first instruction collide in the logs; the design in section 2 as a *design*.

**Not safe to say in the interview, because it hasn't been built or run:** that Praxis listens, understands speech, or handles
voice commands. "It's one prompt away" describes how hard the build is, not what exists; the honest line is "designed and confirmed,
not built yet, by choice".

**Does not support:** "Praxis listens", "Praxis handles voice commands", any accuracy, latency or noise figure for any
recognizer, or anything about Meta glasses audio beyond what Meta documents. `docs/CLAIMS.md` has no voice line today
(`POSITIONING.md` says "there's no voice input yet"). Add "Praxis listens" to the do-not-claim list in its generator,
`prototype/praxis/write_results.py`, until Phase 2 has run live on the demo machine.
