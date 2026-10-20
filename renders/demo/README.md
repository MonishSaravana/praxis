# Repair demo reel

Two cuts of the same ~49 s reel, built by `python -m praxis.render.reel` (from `prototype/`):

- `praxis_repair_demo_user.mp4`: what the technician sees through the glasses.
- `praxis_repair_demo_engineer.mp4`: the same frames with the engine underneath (P(step), model calls with real latencies, a timeline of the layers).

**Source.** One live Studio session (`sessions/20261018_152645_high-voltage-board-repair-with-screwdriv`): ENIGMA-51
video 141, a real first-person high-voltage board repair, with Jev 1.14 as the fast tier and Claude Opus 5.5 as the
escalation. The procedure was compiled from the lab's written instructions; the models were never trained on this task.
All cards, beliefs and calls are drawn from that session's `live.jsonl`, at their logged times. The cut only picks
stretches of session time, and each frame shows its session time code.

| Beat | Session time | What the log shows | Checked against the footage |
|---|---|---|---|
| Starts the job | 0:00–0:05 | work order set, first instruction | yes |
| Watches the panel | 0:21–0:30 | Jev flags "presses only one green button" (0.84) at 0:26 | both buttons are lit at 0:27, so Jev was wrong |
| Opus clears it | 0:36.5–0:39.5 | Opus answers "in progress 0.70" (applied 0:38.25); no alert sent | correct: no false alarm |
| Iron overshoot | 2:47–3:03 | instruction + safety flag 2:50; Opus reads "about 215 °C" at 2:52; alert at 2:58 | display reads SET 221 at 2:50, 215 at 2:52. **By 2:57 the tech had already pressed DOWN back to 200**, so the alert came late |
| Follows the resolder | 3:34–3:43 | resolder instruction at 3:37 | the tech is already soldering at 3:33, so the instruction follows rather than leads |

**What to say out loud.** These are selected moments. Across the whole 16:40 session, the engine confirmed 1 of 19
steps and agreed with proxy step labels 29% of the time (`results/backend/enigma_live_141.json`). The second mistake
alert in the session (4:39.8, "Use the UP button") was a false alarm: the tech was correctly cooling the iron, so it is
left out of the reel.

## Short cut for the deck (15 s, engineer view)

`praxis_repair_short_engineer.mp4` is built by `python -m praxis.render.reel --view engineer --cut short` from the
same session and log. It has no title or end card. It has three beats, `BEATS_SHORT` in `praxis/render/reel.py`:

| Beat | Session time | What the log shows |
|---|---|---|
| Next step | 2:48.5–2:52.5 | instruction for s6 at 2:50: turn on the iron, press UP until the display shows 200 |
| Mistake caught | 2:56–3:00.5 | alert at 2:58: "You've gone past 200. Press DOWN to get back to 200 degrees." |
| Can't see | 4:26–4:33 | the fast tier's 4:25 verdict marks the view insufficient ("Show me The soldering station display"). The Opus escalation is answered at 4:30.75: "Look closely at the soldering station display, upper right." |

In the third beat the request appears in the model-call panel; the policy didn't put a card on the glasses for it.
The renderer now prints any verdict whose `visibility` is `insufficient` as "can't see clearly" in blue, with the
logged `view_request` as its note.
