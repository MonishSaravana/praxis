# Deck storyline (draft for sign-off, 2026-10-18)

The deck tells one story: **new technicians learn by shadowing for a year; Praxis is the coach that watches the work;
it already works, better and cheaper than a frontier model; the timing is now; we start with businesses because
that's where the money and the repeat data are; and every session builds the data robots will need.**

The structure follows the Sequoia / YC outline. Every headline is an assertion, there's one takeaway per slide, and
the appendix answers the obvious objections.

**Talk track (about 4 min):** slides 1, 2, 4, 5, 6, 9, 10, 14, 15. The rest are there for the pre-read and Q&A.

| # | Headline (the assertion) | What's on it | Evidence |
|---|---|---|---|
| 1 | *Instructions that can finally see how you're doing* | HUD photo cover (concept mock) | n/a |
| 2 | A new maintenance technician takes about a year to work alone | >1 yr training · 9–14 mo to profitable · $44/h of senior-tech time · 51,900 openings/yr | BLS, ARSA, BLS ECEC |
| 3 | Every tool today shows the steps. None of them watches the work | The status quo, compared: shadowing, manuals and videos, procedure apps (MaintainX), fixed cameras. What each misses | `COMPETITORS.md` |
| 4 | Praxis turns the manuals a shop already has into a coach that sees | 3-step workflow (load procedures → coach on a phone or glasses → verify and record) + the 4 HUD states (step, verified, mistake, better view) | Concept mocks, labeled |
| 5 | Coaching is a tracking problem, not a seeing problem | The architecture diagram (ours / open / rented) | `RESULTS.md` |
| 6 | Same frontier model: 13% more accurate at a fifth of the cost | Relative-accuracy and cost bars; never confidently wrong on bad views | `CLAIMS.md` |
| 7 | 2026 is the first year this can be sold | Three shifts: glasses opened their cameras to apps (Meta toolkit 1.0, Android XR); event-triggered vision checks got cheap enough ($0.018/min); Microsoft ends Dynamics 365 Guides on Dec 31, 2026, so its customers are choosing a replacement now | `POSITIONING.md` |
| 8 | We sell to businesses first, because that's where the budget and the repeat data are | Consumer vs maintenance, compared on: who pays · does the task repeat · who owns distribution · works without glasses · fits what we've measured. Consumer is where we end up | `USE_CASES.md`, Frontdoor $99→$25 |
| 9 | A $1.8B first market inside a $9B one | TAM / SAM / SOM, bottom-up (below) | BLS OEWS May 2025 |
| 10 | It pays for itself if it saves a senior tech an hour a week | Model: a subscription per trainee + setup per procedure, after a paid pilot. GTM: first 10 → 100 → 1,000 customers | `POSITIONING.md` |
| 11 | The closest competitors are hardware-led. We're software on what shops already own | 2×2: watches the work vs shows the steps × follows the person vs fixed station. Where Viture, Strivr, Tulip, Retrocausal and Meta AI sit | `COMPETITORS.md` |
| 12 | Our moat is data that gets better with every session | Learning curves (31%→51%, 63%→72.5%) + the flywheel: customers pay us to collect step-labeled video | `learning_curve.json` |
| 13 | Why me: I've built real-time vision on messy video before, and I built this in a week | 7 years of competitive robotics (mentoring without seeing what they see) · LipTrac (real-time lip reading, provisional patent) · this engine, eval and live app built solo (first commit Oct 17) | Application, git log |
| 14 | Today we coach the people. Next, the robots | Staircase: coach → system of record → own models → data and checker for robots → robot intelligence (option) | `VISION.md` |
| 15 | $10k turns a working prototype into a paid maintenance pilot | Use of funds + what becomes true by April: measured on maintenance footage, running on glasses, a first paid pilot | Application |
| 16 | Close | Lockup + contact | |
| A1–A6 | Appendix | Training data stated plainly · market math and assumptions · unit economics and pricing risk · risks and how we handle them · glasses and voice (built vs designed) · competitor detail | |

## Market sizing (US, per year, bottom-up)

| | Who | Math | Size |
|---|---|---|---|
| **TAM** | Everyone in the US who does hands-on work from written procedures: installation, maintenance and repair (6.09M), electricians (0.76M), production (8.57M) = **15.4M workers** | 15.4M × $50 a month × 12 | **≈ $9.2B** |
| **SAM** | US maintenance and repair techs: general maintenance, machinery mechanics and millwrights, HVAC = **2.47M workers, about 255k openings a year** | New-tech coaching: 255k × $200 × 6 months = $306M. Plus verified records for the whole workforce: 2.47M × $50 × 12 = $1.48B | **≈ $1.8B** |
| **SOM (year 3 target)** | 1% of new US maintenance techs a year: about 2,550 trainees, roughly 100 mid-size maintenance teams | 2,550 × $200 × 6 months | **≈ $3M ARR** |

- **Assumptions to say out loud.** $200 a month for coaching and $50 a month for every-worker records are our
  pricing hypotheses. Openings include people changing jobs. The SOM is a goal, not a forecast.
- **Not counted.** Other countries, field service outside these groups, aviation, and the robotics upside.
- **Sources.** BLS OEWS national tables, May 2025 (49-0000: 6,086,190; 47-2111: 757,220; 51-0000: 8,565,760).
  The three maintenance groups are from the BLS Occupational Outlook Handbook ([`PITCH_QA.md`](PITCH_QA.md), Part 7).

## Go-to-market (slide 10)

1. **First 10 customers: founder-led paid pilots.**
   - Who: Boston-area facilities teams, HVAC and equipment-service shops, technical training programs, and Dynamics
     365 Guides customers who need a replacement by Dec 31.
   - Outreach: 70 emails to maintenance teams and programs this week (14 sent Oct 17, 56 scheduled for Oct 19).
2. **Next 100: case studies and integrations.**
   - Case studies from pilots with a metric agreed up front.
   - Read procedures straight out of the CMMS and procedure apps shops already use (MaintainX-style).
   - Training programs as a channel: their students carry it to their employers.
3. **Then 1,000: partners.**
   - Industrial distributors and glasses makers.
   - Land and expand: from a site to every site, from new techs to the whole workforce (records).

## Decisions for Monish

- **Slide 13 "built this in a week":** the first commit was Oct 17. Is that how you want to say it?
- **Slide 15 "a first paid pilot by April":** keep it, or soften it to "pilots running"?
- **Concept-mock photos stay labeled.** No cooking footage on any slide (brand deck rule).
