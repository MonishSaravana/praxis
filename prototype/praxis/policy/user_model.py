"""L6 · User model (ours). Decides how much detail to give, automatically.

Main signal: time on step versus the typical time for that step (the task graph's duration prior, fit on
the dataset's train split). Mistakes and repeats also count. The output is a profile (novice / standard
/ expert) that picks the phrasing, plus the hesitation threshold for offering expanded detail.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UserModel:
    fixed_profile: str | None = None      # "novice" | "expert" forces a profile (policy demo); None = auto
    skill: float = 0.5                    # 0 = struggling novice, 1 = fast expert
    ratios: list[float] = field(default_factory=list)   # time_on_step / prior for completed steps
    mistakes: int = 0
    repeats: int = 0
    hints: int = 0

    def on_step_done(self, time_on_step: float, prior_s: float) -> None:
        r = time_on_step / max(prior_s, 1e-3)
        self.ratios.append(r)
        if r < 0.6:
            self.skill += 0.08
        elif r > 1.6:
            self.skill -= 0.08
        self._clip()

    def on_mistake(self) -> None:
        self.mistakes += 1
        self.skill -= 0.1
        self._clip()

    def on_repeat(self) -> None:
        self.repeats += 1
        self.skill -= 0.05
        self._clip()

    def _clip(self) -> None:
        self.skill = min(1.0, max(0.0, self.skill))

    @property
    def profile(self) -> str:
        if self.fixed_profile:
            return self.fixed_profile
        return "novice" if self.skill < 0.4 else "expert" if self.skill > 0.7 else "standard"

    def hesitation_threshold(self, base: float) -> float:
        """time-on-step / prior ratio above which we expand the explanation."""
        return {"novice": base * 0.8, "standard": base, "expert": base * 1.3}[self.profile]

    def state(self) -> dict:
        return {"profile": self.profile, "skill": round(self.skill, 3), "mistakes": self.mistakes,
                "repeats": self.repeats, "hints": self.hints,
                "median_ratio": sorted(self.ratios)[len(self.ratios) // 2] if self.ratios else None}
