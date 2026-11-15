"""Command line interface for CourseScope."""

import argparse
import sys

from .models import load_catalog, parse_time
from .scheduler import Preferences, build_schedules


def cmd_plan(args):
    catalog = load_catalog(args.catalog)

    wanted = [code.strip().upper() for code in args.courses.split(",") if code.strip()]
    courses = []
    for code in wanted:
        if code not in catalog:
            known = ", ".join(sorted(catalog))
            print(f"error: {code} not in catalog. available: {known}", file=sys.stderr)
            return 1
        courses.append(catalog[code])

    prefs = Preferences(
        no_before=parse_time(args.no_before) if args.no_before else None,
        no_after=parse_time(args.no_after) if args.no_after else None,
    )

    schedules = build_schedules(
        courses, max_units=args.max_units, prefs=prefs, limit=args.top
    )
    if not schedules:
        print(
            "no conflict-free schedule found for that combination "
            "within the given constraints.",
            file=sys.stderr,
        )
        return 1

    for i, sched in enumerate(schedules, 1):
        print(f"option {i}  (days on campus: {len(sched.days_used())})")
        print(sched.render())
        print()
    return 0


def cmd_list(args):
    catalog = load_catalog(args.catalog)
    for code in sorted(catalog):
        course = catalog[code]
        kinds = ", ".join(
            f"{kind} x{len(course.groups[kind])}" for kind in course.group_kinds()
        )
        print(f"{code:<14} {course.units:g}u  {course.title}  [{kinds}]")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="coursescope",
        description="Build conflict-free UC Berkeley course schedules.",
    )
    parser.add_argument(
        "--catalog",
        default="data/berkeley_courses.json",
        help="path to the course catalog JSON (default: %(default)s)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list courses in the catalog")
    p_list.set_defaults(func=cmd_list)

    p_plan = sub.add_parser("plan", help="build ranked schedule options")
    p_plan.add_argument(
        "--courses",
        required=True,
        help='comma-separated course codes, e.g. "COMPSCI 61A,DATA C8,MATH 54"',
    )
    p_plan.add_argument("--max-units", type=float, default=None)
    p_plan.add_argument(
        "--no-before", metavar="H:MM", help="no classes starting before this time"
    )
    p_plan.add_argument(
        "--no-after", metavar="H:MM", help="no classes ending after this time"
    )
    p_plan.add_argument("--top", type=int, default=5, help="how many options to show")
    p_plan.set_defaults(func=cmd_plan)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
