"""Backtracking schedule search with constraints and preference scoring."""

from itertools import product

from .models import DAY_ORDER


class Preferences:
    """Soft preferences used to rank conflict-free schedules.

    no_before: earliest acceptable class start, minutes since midnight (or None)
    no_after: latest acceptable class end, minutes since midnight (or None)
    prefer_compact_days: reward schedules that use fewer distinct days
    prefer_mornings / prefer_afternoons: nudge scoring by average start time
    """

    def __init__(self, no_before=None, no_after=None, prefer_compact_days=True):
        self.no_before = no_before
        self.no_after = no_after
        self.prefer_compact_days = prefer_compact_days


class Schedule:
    """One chosen section per group kind, across all requested courses."""

    def __init__(self, picks):
        # picks: list of (course, {kind: Section})
        self.picks = picks
        self.sections = [sec for _, kinds in picks for sec in kinds.values()]
        self.units = sum(course.units for course, _ in picks)

    def is_conflict_free(self):
        secs = self.sections
        for i in range(len(secs)):
            for j in range(i + 1, len(secs)):
                if secs[i].conflicts_with(secs[j]):
                    return False
        return True

    def days_used(self):
        days = set()
        for sec in self.sections:
            days.update(sec.meeting_days())
        return days

    def score(self, prefs):
        """Higher is better. Returns None if a hard bound is violated."""
        if not self.is_conflict_free():
            return None
        score = 100.0
        for sec in self.sections:
            if prefs.no_before is not None and sec.earliest_start() < prefs.no_before:
                return None  # hard bound: nothing may start before no_before
            if prefs.no_after is not None and sec.latest_end() > prefs.no_after:
                return None  # hard bound: nothing may end after no_after
        if prefs.prefer_compact_days:
            score -= 8 * len(self.days_used())
        # Penalize long idle gaps within a day.
        for day in DAY_ORDER:
            todays = sorted(
                (m.start, m.end)
                for sec in self.sections
                for m in sec.meetings
                if day in m.days
            )
            for (s1, e1), (s2, e2) in zip(todays, todays[1:]):
                gap = s2 - e1
                if gap > 0:
                    score -= gap / 60.0  # one point per idle hour
        return score

    def render(self):
        lines = []
        for course, kinds in self.picks:
            for kind in sorted(kinds):
                sec = kinds[kind]
                meetings = "; ".join(m.describe() for m in sec.meetings)
                lines.append(
                    f"  {course.code:<14} {kind} {sec.section_id:<6} {meetings}"
                )
        lines.append(f"  total units: {self.units:g}")
        return "\n".join(lines)


def _section_combos(course):
    """All ways to pick one section per kind for a course."""
    kinds = course.group_kinds()
    if not kinds:
        return [{}]
    lists = [course.groups[k] for k in kinds]
    combos = []
    for choice in product(*lists):
        combos.append(dict(zip(kinds, choice)))
    return combos


def build_schedules(courses, max_units=None, prefs=None, limit=5):
    """Backtracking search over all requested courses.

    courses: list[Course] to enroll in simultaneously.
    Returns up to `limit` Schedule objects, best score first.
    """
    prefs = prefs or Preferences()
    combos_per_course = [(c, _section_combos(c)) for c in courses]
    # Search the most constrained course first: fewer combos prune faster.
    combos_per_course.sort(key=lambda pair: len(pair[1]))

    results = []
    chosen = []

    def violates_units():
        if max_units is None:
            return False
        return sum(c.units for c, _ in chosen) > max_units

    def partial_conflicts(new_kinds):
        new_secs = list(new_kinds.values())
        for _, kinds in chosen:
            for sec in kinds.values():
                for new_sec in new_secs:
                    if sec.conflicts_with(new_sec):
                        return True
        return False

    def backtrack(i):
        if i == len(combos_per_course):
            sched = Schedule(list(chosen))
            s = sched.score(prefs)
            if s is not None:
                results.append((s, sched))
            return
        course, combos = combos_per_course[i]
        for combo in combos:
            if partial_conflicts(combo):
                continue
            chosen.append((course, combo))
            if not violates_units():
                backtrack(i + 1)
            chosen.pop()

    backtrack(0)
    results.sort(key=lambda pair: pair[0], reverse=True)
    return [sched for _, sched in results[:limit]]
