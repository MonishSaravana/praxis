# Picking the first market: new technicians, older adults, or everyone?

> **Status: a decision memo, not results.** Market facts are cited in [Sources](#sources). Product numbers come from
> [`CLAIMS.md`](CLAIMS.md). The competitive picture comes from [`COMPETITORS.md`](COMPETITORS.md) and
> [`POSITIONING.md`](POSITIONING.md). The long-term plan these fit into is [`VISION.md`](VISION.md).
> **Decided 2026-10-17:** new technicians on maintenance and repair is the wedge.

## The short answer

- **Lead with new technicians learning maintenance and repair.** That's the version of "training new workers"
  where a coach that follows the person matters most. Maintenance work moves around the machine, so a camera bolted
  to a workstation can't follow it.
- **Older adults with dementia is the mission market.** We enter it later, once the models run on the device and
  the glasses are lighter.
- **General consumer is the endgame.**

Investors care less about *which* market than about seeing that you chose deliberately, and that you know what the
grant money will prove. Pitching all three at once reads as unfocused. Pitching one, with the others as the next
steps, reads as vision.

## What these reviewers care about

- **The grant funds experiments by founders who execute.**
  - The grant is funded by Xfund. Xfund says it backs people who think laterally across disciplines and can
    execute [X1].
  - Xfund's similar grant at Stanford gives up to $10k "to support early experimentation and company formation"
    [X2].
  - So the money question is "what will this let you learn?" The execution question is already answered: you built
    a working, measured prototype in a weekend.
- **The market questions any investor asks:**
  1. Does someone already pay for this?
  2. Is the pain frequent?
  3. Can you reach the buyer?
  4. Does your tech work for it now?
  5. Who else is there?
  6. What could sink it (regulation, privacy)?
  7. Where does it lead?
- **The red flag:** "it works for everyone." The cure: one first customer they can picture, and a reason for the
  order of everything after it.

## Scorecard

| Question | New technicians (maintenance and repair) | Older adults with dementia | General consumer |
|---|---|---|---|
| **Someone already pays** | **Strong.** Autodesk is buying MaintainX, a phone app for maintenance procedures, for $3.6B ([VISION D19](VISION.md#sources)). Tulip lists $100–250 per station per month ([VISION D3](VISION.md#sources)) | **Unclear.** Families, care operators or insurers could pay, but each channel is slow. Operators do pay for AI video for fall safety (SafelyYou) [E4] | **Weak.** Frontdoor's expert-video plan fell from $99 to $25 a year ([VISION D15](VISION.md#sources)) |
| **Same task repeats** (data, ROI) | **Strong.** The same checklist runs on every machine every month, and building blocks (lockout, filters, belts, fasteners) repeat across procedures | **Strong per person** (tea, pills, dressing, every day), small population per site | **Weak.** A long tail; most tasks happen a few times a year (cooking is the exception) |
| **Works without glasses today** | **Yes.** A tablet at the bench. On the move, maintenance teams already buy head-mounted displays (RealWear) | **Partly.** A fixed kitchen camera works (COACH used one [E2]). Older adults raise concerns about wearing glasses [E5] | **Barely.** A propped-up phone; app-store publishing on glasses isn't confirmed |
| **Fits what we've measured** | **Medium.** Written procedures suit the compiler, but every metric is from cooking, not maintenance | **Medium.** Simple daily tasks suit the tracker. But "look down and to the right" asks a lot of someone with dementia | **Weak.** Needs open-set tasks, our weakest area: 0 of 7 recipes named from video alone |
| **Competition** | **Thinner than around assembly.** Fixed-camera tools (Retrocausal and others) are built for production stations. Procedure apps (MaintainX, Augmentir) don't watch the work. First-person entrants (Strivr, Viture+NVIDIA) are early ([`COMPETITORS.md`](COMPETITORS.md), [`POSITIONING.md`](POSITIONING.md)) | **A funded first mover.** CrossSense won the £1M Longitude Prize on Dementia for AI glasses that coach daily tasks [E3] | **The platforms themselves.** Meta's and Google's own assistants |
| **Risk** (privacy, consent, regulation, liability) | **Medium.** Technicians may see it as surveillance. Safety-critical steps (lockout) need care: Praxis prompts and records them, and never approves them | **High.** Consent capacity, health-data rules, and medical claims could bring FDA oversight. A wrong prompt about pills is a safety issue | **Low to medium** |
| **Time to a first pilot** (solo student) | **Medium.** A facilities maintenance team, an equipment-service shop, or a technical training program | **Slow.** Care partners, ethics review, family consent | **Fast to launch, slow to monetize** |
| **Where it leads** ([`VISION.md`](VISION.md)) | **Straight up the staircase.** Plant floors are where robots land, and those robots will need maintaining too | **Home robots.** Elder care is the classic home-robot job, but the data is the hardest to use | **The endgame,** once glasses are everywhere |
| **Pitch resonance** | Solid. "Shadowing one senior tech for weeks" is a pain anyone gets | **Highest** | Easiest to understand |

**The result.** New maintenance technicians win on the questions investors weigh most: who pays, how often the task
repeats, and whether it works without glasses. It's also where our first-person edge matters, because fixed cameras
can't follow the work. Dementia wins on meaning but loses on
who pays, consent, and hardware. Consumer is the biggest prize but the worst place to start.

---

## Each option, honestly

### New technicians on maintenance and repair (the chosen beachhead)

**For it:**
- **The budget already exists.** Autodesk is buying MaintainX for $3.6B, and the procedures already live on
  technicians' phones.
- **New technicians keep coming.** BLS projects about 51,900 openings a year for maintenance mechanics, and about
  40,600 for HVAC ([VISION D20, D21](VISION.md#sources)).
- **Know-how walks out the door.** 47% of maintenance teams lost knowledge they couldn't recover when someone left
  ([VISION D16](VISION.md#sources)).
- **Procedures are written down and repeated,** so the models improve fast.
- **It doesn't need consumer glasses to take off.** A tablet works at the bench, and industrial teams already buy
  head-mounted displays for the work on the move.
- **It leads to the plant floors where robots go next.**

**Against it:**
- First-person entrants (Strivr, Viture) could go here too. They're early, and neither publishes accuracy.
- Our edge is a design difference that hasn't been measured on maintenance. Every metric is from cooking.
- **What we can say:** first-person; set up from the existing procedure with no footage of it; asks for a better view
  when unsure.
- **What we can't say:** "we're the only ones verifying by camera" (see [`COMPETITORS.md`](COMPETITORS.md)).

**Why maintenance and not assembly stations.** Retrocausal's own docs say success depends on placing the camera to
see every step, with parts picked from fixed locations, and its setup takes "a couple hours." Assembly stations fit
that, so fixed cameras already serve them. Maintenance doesn't fit it:
- The work moves around the machine.
- Every asset is a little different.
- New technicians learn by shadowing one senior tech.

Assembly lines stay on the list as a later expansion ([`VISION.md`](VISION.md) Phase 2).

### Older adults and dementia (the mission market, later)

**Why it matters:**
- 7.2M Americans aged 65+ live with Alzheimer's.
- About 12M unpaid caregivers gave 19.2B hours of care, valued at about $413B [E1].
- Memory care alone needs about 1M more direct-care workers by 2031 [E6].

**There's real evidence the idea works.**
- COACH (University of Toronto, 2008–2010) used an overhead camera and a probabilistic tracker of handwashing
  steps, with graded audio prompts. That is the same shape as Praxis.
- With COACH, people with moderate dementia completed 11% more steps on their own and needed 60% fewer interactions
  with a caregiver. The study had only 6 participants [E2].
- COACH needed every task built by hand. Praxis compiles tasks from text, and that's exactly what changed.

**Why not first:**
1. **Who pays is unclear and slow** (families, operators, insurers).
2. **Consent.** People with dementia may not be able to consent to their data being used for training. That limits
   the data flywheel and the robotics path.
3. **Hardware.** A 2025 review found older adults worry about distraction and how conspicuous glasses are, and
   want better glasses first [E5].
4. **Safety and regulation.** Prompts about medication or the stove carry real liability, and medical claims could
   bring FDA oversight.
5. **A funded first mover.** CrossSense won £1M in March 2026 and plans a phone version by the end of 2026, glasses
   in early 2027, and a subscription [E3].

**When:** once routine checks run on the device (Phase 3 in `VISION.md`) and glasses are lighter. There's also a
bridge that uses the Phase 1 business model: **coaching new caregivers** in memory care, where turnover is high
and operators already pay for AI cameras.

**One thing that would change this:** a personal reason, such as someone in your family. That's real founder-market
fit, and it would be worth saying out loud.

### General consumer (the endgame)

**For it:**
- It's the biggest market.
- It's the simplest story.
- It's the obvious killer app for camera glasses.

**Against it:**
- **Weak willingness to pay.** Frontdoor's price drop is the clearest data point we have.
- **No distribution yet.** Glasses app-store publishing isn't confirmed.
- **The long tail of tasks hits our weakest numbers.** From video alone, we named 0 of 7 unseen recipes. Even when
  the person said what they were making, the drafted plans tracked their step only 36% of the time.
- **The competitor is Meta's own assistant,** on Meta's own glasses.
- It becomes the right move once mass-market glasses are open to developers and checks cost almost nothing on the
  device (Phase 5).

---

## How to say it in the interview (under a minute)

> "The engine isn't tied to one task, so I had to pick where to start. I compared three markets: training new
> technicians, helping older adults with dementia, and general consumers. I asked who already pays, how often the
> same task repeats, and whether it works without glasses. New maintenance technicians win all three. Autodesk is
> paying $3.6 billion for a phone app that holds maintenance procedures, the same checklist runs on every machine
> every month, and maintenance teams already buy head-mounted displays. It's also work a fixed camera can't follow, which is where
> our approach matters. Dementia care is the one I find most meaningful. In a small 2008 study, a camera-based
> handwashing coach cut the help people needed from a caregiver by 60%. But the buyer, consent and hardware problems
> make it a later step, not the first one. Consumer is where this ends up, once glasses are everywhere."

## If they push back

- **"Dementia is more meaningful. Why not start there?"**
  - Agree that it matters.
  - Then name the three blockers: who pays, consent for the data, and wearing glasses.
  - Say when it becomes the right move: on-device models plus lighter glasses.
  - Mention the bridge: coaching new caregivers.
- **"Workplace training is crowded."**
  - Around assembly stations, yes, and that's the proof the budget exists.
  - That's why we start in maintenance: fixed cameras can't follow the work, and procedure apps don't watch it.
  - Our bet is narrower than "camera checks": first-person, set up from the existing procedure with no footage, and
    asking for a better view when unsure.
  - The grant tests whether that edge matters to a buyer.
- **"What about Viture and NVIDIA?"**
  - NVIDIA's XR AI is an open-source toolkit, not a product. NVIDIA wins when apps like ours exist.
  - Viture sells $600+ safety glasses with AI coaching built in. They ship in Q1 2027, starting with labs and
    pharma. That's a real competitor, and proof the category is real.
  - We run now, on a phone a shop already owns, and we'd rather also run on their glasses than fight them.
  - Details: [`POSITIONING.md`](POSITIONING.md).
- **"Glasses are booming. Why not consumer?"**
  - Booming hardware doesn't mean open distribution. App-store publishing on Meta's glasses isn't confirmed.
  - Consumers have shown they won't pay much for remote expert help.
  - We'd be competing with Meta's own assistant on Meta's own glasses.

## What the grant money tests

This fits the application's budget line ($2,000 for collecting and evaluating real task demonstrations) and its
six-month goal of finding "the initial task category where adaptive guidance creates the largest measurable
improvement."

1. **Customer discovery.**
   - Ten conversations with maintenance managers, service-shop owners and technical instructors.
   - Five with memory-care staff or family caregivers, to keep the mission option honest.
2. **First real maintenance data.**
   - One or two friendly sites: record real procedures, label them, and run the engine. This is the first
     non-cooking metric.
   - The public IndustReal dataset (toy-car assembly *and maintenance*) is the fallback if its labels become
     reachable.
3. **A pilot with a metric agreed in advance:** time until the new technician works alone, senior-technician hours
   spent shadowing, or repeat work.
4. **The kill rule.** If buyers say the first-person edge doesn't matter to them, switch to the next category on
   the list, not to a new product.

**Before Tuesday, if possible:** even two short conversations with a maintenance manager or service-shop owner turn
"I think they would pay" into "a maintenance manager told me X." That's the strongest single upgrade to the pitch.
Ask about the past ("walk me through the last time you onboarded a technician"), not about the idea. The full list
of questions is in [`POSITIONING.md`](POSITIONING.md).

## Sources

All checked 2026-10-17.
- [X1] Xfund's thesis (multidisciplinary founders who can execute): https://www.vcaonline.com/news/2020090321/xfund-3-raises-oversubscribed-fund-to-back-university-based-innovation/ · Harvard Magazine: https://www.harvardmagazine.com/node/75437
- [X2] Xfund Experiment Grants (Stanford pilot): https://www.xfund.com/experiment-grants
- [E1] Alzheimer's Association, 2025 Facts and Figures, executive summary: https://www.alz.org/getmedia/c05f7ba4-9aea-4cb0-8898-5e8bff3f0930/executive-summary-2025-alzheimers-disease-facts-and-figures.pdf
- [E2] Mihailidis et al., "The COACH prompting system to assist older adults with dementia through handwashing: an efficacy study," BMC Geriatrics 2008: https://link.springer.com/doi/10.1186/1471-2318-8-28 · Hoey et al., CVIU 2010: https://cs.uwaterloo.ca/~ppoupart/publications/handwashing/handwashing-cviu09.pdf
- [E3] Nesta / Challenge Works, Longitude Prize on Dementia winner, Mar 2026: https://www.nesta.org.uk/blog/ai-smart-glasses-companion-winner-of-longitude-prize-on-dementia/ · TechRadar: https://www.techradar.com/pro/a-dream-come-true-revolutionary-ai-smart-glasses-win-usd1-4-million-nobel-prize-to-combat-dementia
- [E4] SafelyYou (AI video for falls in memory care): Series A release https://www.prnewswire.com/news-releases/safelyyou-accelerates-growth-by-closing-19-5-million-series-a-funding-round-301378733.html · NIA spotlight https://www.nia.nih.gov/news/nia-funded-small-business-spotlight-safelyyou-trains-ai-improve-care-older-adults (total raised about $100M per aggregators only; unverified)
- [E5] "Smart Glasses for Older Adults With Cognitive Impairment: A Scoping Review," JAMDA 2025: https://www.jamda.com/article/S1525-8610(25)00348-2/fulltext
- [E6] Senior Housing News on the Alzheimer's Association 2024 report: https://seniorhousingnews.com/2024/03/27/memory-care-sector-needs-1-million-more-direct-care-workers-by-2031/
