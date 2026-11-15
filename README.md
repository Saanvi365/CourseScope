# CourseScope

A UC Berkeley course schedule builder. Give it the classes you want to take and it finds conflict-free schedules, then ranks them so the best option is on top.

Built for the problem every Berkeley student hits each semester: lectures, discussions, and labs all come in multiple sections, most combinations overlap, and checking them by hand on CalCentral is slow.

## What it does

- Picks one section of every required part of each course (lecture + discussion + lab) so a schedule is actually enrollable, not just a list of classes that happen not to overlap.
- Rejects any schedule with a time conflict. Back-to-back classes are fine; overlapping ones are not.
- Enforces hard constraints: max units, nothing starting before a time you set, nothing ending after a time you set.
- Ranks the surviving schedules: fewer days on campus and shorter idle gaps score higher.

## Usage

```bash
# see what is in the catalog
python3 -m coursescope.cli list

# build schedule options
python3 -m coursescope.cli plan \
  --courses "COMPSCI 61A,DATA C8,MATH 54" \
  --max-units 14 \
  --no-before 9:00 \
  --top 3
```

Example output:

```
option 1  (days on campus: 5)
  COMPSCI 61A    LEC 001    M/W/F 10:00-11:00
  COMPSCI 61A    DIS 102    Th 15:30-17:00
  COMPSCI 61A    LAB 202    F 15:00-16:30
  DATA C8        LEC 001    M/W/F 11:00-12:00
  ...
  total units: 12
```

## How it works

- `coursescope/models.py` - courses, sections, and meetings, plus the overlap logic (two meetings conflict only when they share a day and their time ranges intersect).
- `coursescope/scheduler.py` - backtracking search. Each course expands into every legal combination of its sections, and the search prunes any partial schedule that already conflicts or exceeds the unit cap. Surviving full schedules get scored on days-on-campus and idle gaps.
- `coursescope/cli.py` - the `list` and `plan` commands.

## The catalog

`data/berkeley_courses.json` is an **illustrative sample**. The course codes, titles, and unit values follow real Berkeley offerings (COMPSCI 61A, DATA C8, MATH 54, ...), but every section id, day, and time is invented for development and testing. It is not live Schedule of Classes data - point `--catalog` at a real export before planning an actual semester with it.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Covers the overlap rules (including the back-to-back edge case), catalog loading, conflict-free guarantees, the unit cap, the no-earlier-than bound, and the ranking order.

## Requirements

Python 3.8+, standard library only. No installs.
