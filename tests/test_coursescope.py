"""Tests for CourseScope: time logic, conflicts, constraints, ranking."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coursescope.models import Meeting, Section, load_catalog, parse_time
from coursescope.scheduler import Preferences, build_schedules

CATALOG = os.path.join(os.path.dirname(__file__), "..", "data", "berkeley_courses.json")


def meeting(days, start, end):
    return Meeting(days=tuple(days), start=parse_time(start), end=parse_time(end))


class TestMeetingOverlap(unittest.TestCase):
    def test_overlap_same_day(self):
        a = meeting(["M"], "10:00", "11:00")
        b = meeting(["M", "W"], "10:30", "11:30")
        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

    def test_no_overlap_different_days(self):
        a = meeting(["M"], "10:00", "11:00")
        b = meeting(["Tu"], "10:00", "11:00")
        self.assertFalse(a.overlaps(b))

    def test_back_to_back_is_not_a_conflict(self):
        a = meeting(["M"], "10:00", "11:00")
        b = meeting(["M"], "11:00", "12:00")
        self.assertFalse(a.overlaps(b))


class TestCatalog(unittest.TestCase):
    def test_loads_all_courses(self):
        catalog = load_catalog(CATALOG)
        self.assertEqual(len(catalog), 6)
        cs61a = catalog["COMPSCI 61A"]
        self.assertEqual(cs61a.units, 4)
        self.assertIn("LEC", cs61a.groups)
        self.assertIn("DIS", cs61a.groups)
        self.assertIn("LAB", cs61a.groups)


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(CATALOG)

    def test_finds_conflict_free_schedule(self):
        courses = [self.catalog["COMPSCI 61A"], self.catalog["MATH 54"]]
        schedules = build_schedules(courses, limit=10)
        self.assertTrue(schedules)
        for sched in schedules:
            self.assertTrue(sched.is_conflict_free())
            # Full enrollment: every kind of section the course offers is picked.
            for course, kinds in sched.picks:
                self.assertEqual(set(kinds), set(course.group_kinds()))

    def test_max_units_is_enforced(self):
        courses = [self.catalog[c] for c in ("COMPSCI 61A", "MATH 54", "COMPSCI 70")]
        schedules = build_schedules(courses, max_units=8, limit=10)
        for sched in schedules:
            self.assertLessEqual(sched.units, 8)

    def test_no_before_bound(self):
        courses = [self.catalog["EECS 16A"]]
        prefs = Preferences(no_before=parse_time("12:00"))
        schedules = build_schedules(courses, prefs=prefs, limit=10)
        self.assertTrue(schedules)
        for sched in schedules:
            for sec in sched.sections:
                self.assertGreaterEqual(sec.earliest_start(), parse_time("12:00"))

    def test_impossible_combination_returns_empty(self):
        # A course forced against itself cannot fit under 0 units... but more
        # realistically: asking for a bound no section satisfies.
        a = meeting(["M"], "9:00", "17:00")
        sec_a = Section(section_id="X", kind="LEC", meetings=(a,))
        from coursescope.models import Course

        blocker = Course(code="BLOCK 1", title="All day", units=4,
                         groups={"LEC": [sec_a]})
        courses = [blocker, self.catalog["COMPSCI 61A"]]
        self.assertEqual(build_schedules(courses, limit=5), [])

    def test_ranking_prefers_fewer_days(self):
        courses = [self.catalog["COMPSCI 61A"], self.catalog["DATA C8"]]
        schedules = build_schedules(courses, limit=5)
        days = [len(s.days_used()) for s in schedules]
        self.assertEqual(days, sorted(days))


if __name__ == "__main__":
    unittest.main()
