"""Core data model: courses, sections, meetings, and time-conflict logic."""

from dataclasses import dataclass, field

DAY_ORDER = ["M", "Tu", "W", "Th", "F"]


def parse_time(text):
    """'9:30' or '14:05' -> minutes since midnight."""
    hours, minutes = text.strip().split(":")
    return int(hours) * 60 + int(minutes)


def fmt_time(minutes):
    return f"{minutes // 60}:{minutes % 60:02d}"


@dataclass(frozen=True)
class Meeting:
    """One recurring class meeting: which days, when."""

    days: tuple  # subset of DAY_ORDER
    start: int   # minutes since midnight
    end: int

    def overlaps(self, other):
        if not set(self.days) & set(other.days):
            return False
        return self.start < other.end and other.start < self.end

    def describe(self):
        return f"{'/'.join(self.days)} {fmt_time(self.start)}-{fmt_time(self.end)}"


@dataclass(frozen=True)
class Section:
    """A concrete enrollable piece of a course (lecture + optional discussion/lab)."""

    section_id: str
    kind: str  # 'LEC', 'DIS', 'LAB', ...
    meetings: tuple

    def conflicts_with(self, other):
        return any(m.overlaps(n) for m in self.meetings for n in other.meetings)

    def earliest_start(self):
        return min(m.start for m in self.meetings)

    def latest_end(self):
        return max(m.end for m in self.meetings)

    def meeting_days(self):
        days = set()
        for m in self.meetings:
            days.update(m.days)
        return days


@dataclass
class Course:
    """A course with its sections grouped by kind.

    A full enrollment picks exactly one section of each kind the course offers
    (e.g. one LEC and one DIS).
    """

    code: str          # 'COMPSCI 61A'
    title: str
    units: float
    groups: dict = field(default_factory=dict)  # kind -> list[Section]

    def group_kinds(self):
        return sorted(self.groups)


def load_catalog(path):
    """Load the JSON course catalog into Course objects."""
    import json

    with open(path) as f:
        raw = json.load(f)

    courses = {}
    for entry in raw["courses"]:
        groups = {}
        for sec in entry["sections"]:
            meetings = tuple(
                Meeting(
                    days=tuple(m["days"]),
                    start=parse_time(m["start"]),
                    end=parse_time(m["end"]),
                )
                for m in sec["meetings"]
            )
            section = Section(section_id=sec["id"], kind=sec["kind"], meetings=meetings)
            groups.setdefault(sec["kind"], []).append(section)
        courses[entry["code"]] = Course(
            code=entry["code"],
            title=entry["title"],
            units=entry["units"],
            groups=groups,
        )
    return courses
