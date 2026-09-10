"""Pytest plugin that turns test results into a per-day grade.

Every test carries its own metadata:

    @pytest.mark.day(1)      which workshop day it belongs to
    @pytest.mark.points(10)  what it is worth
    @pytest.mark.floor       required work (or .ceiling for stretch)

The plugin tallies those, prints a scorecard, writes a JSON report, and adds a
markdown summary to the GitHub Actions job page. Ceiling tests never fail the
build -- the exit code comes from floor tests alone.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

_ICON = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP", "error": "ERROR", "notrun": "-"}
_EMOJI = {"passed": "✅", "failed": "❌", "skipped": "⏭️", "error": "💥", "notrun": "▪️"}
_TIER = {"floor": "required", "ceiling": "stretch", "engagement": "notebook"}


def pytest_addoption(parser):
    group = parser.getgroup("grading")
    group.addoption("--grade-report", default=None, metavar="PATH",
                    help="write the machine-readable grade report to PATH (JSON)")
    group.addoption("--fail-on", default="floor", choices=("floor", "any", "never"),
                    help="which failures make the run exit non-zero (default: floor)")
    group.addoption("--grade-rubric", action="store_true", default=False,
                    help="print what every task is worth (pair with --collect-only)")


def pytest_configure(config):
    config.pluginmanager.register(Grader(config), "workshop-grader")


class Result:
    """One graded item."""

    def __init__(self, item, day, points, tier, doc):
        self.nodeid, self.name = item.nodeid, item.name
        self.day, self.points, self.tier, self.doc = day, points, tier, doc
        self.outcome = "notrun"
        self.message = ""

    @property
    def earned(self):
        return self.points if self.outcome == "passed" else 0

    @property
    def counts(self):
        """Skipped tests drop out of the denominator instead of costing points."""
        return self.outcome != "skipped"


class Grader:
    def __init__(self, config):
        self.config = config
        self.results = {}
        self.order = []
        self.had_error = False

    # -- collect ------------------------------------------------------------

    def pytest_collection_finish(self, session):
        # Registered here, not in collection_modifyitems, so anything deselected
        # by -m/-k is already gone and cannot score points.
        for item in session.items:
            day, points, tier = None, 1, "floor"
            for marker in item.iter_markers():
                if marker.name == "day" and marker.args:
                    day = marker.args[0]
                elif marker.name == "points" and marker.args:
                    points = marker.args[0]
                elif marker.name in ("floor", "ceiling", "engagement"):
                    tier = marker.name
            doc = getattr(getattr(item, "function", None), "__doc__", None)
            doc = doc.strip().splitlines()[0] if doc else item.name
            self.results[item.nodeid] = Result(item, day, points, tier, doc)
            self.order.append(item.nodeid)

        if not session.config.getoption("--grade-rubric"):
            return
        writer = session.config.pluginmanager.get_plugin("terminalreporter")
        for day, results in self._by_day():
            writer.write_line(f"\nDay {day}  ({sum(r.points for r in results)} points)")
            for result in results:
                writer.write_line(f"  {result.points:>3} pt  [{result.tier:<10}] {result.doc}")

    # -- record -------------------------------------------------------------

    def pytest_runtest_logreport(self, report):
        result = self.results.get(report.nodeid)
        if result is None:
            return
        if report.when == "call":
            result.outcome = report.outcome
        elif report.outcome == "failed":
            result.outcome = "error"  # blew up in setup/teardown, not a wrong answer
            self.had_error = True
        elif report.when == "setup" and report.outcome == "skipped":
            result.outcome = "skipped"
        if report.outcome in ("failed", "error") and report.longrepr is not None:
            text = str(report.longrepr)
            reason = next((l.strip()[2:].strip() for l in text.splitlines()
                           if l.strip().startswith("E ")), text.strip().splitlines()[-1])
            result.message = reason[:300]

    def pytest_collectreport(self, report):
        if report.outcome == "failed":
            self.had_error = True

    # -- score --------------------------------------------------------------

    def _by_day(self):
        grouped = defaultdict(list)
        for nodeid in self.order:
            grouped[self.results[nodeid].day].append(self.results[nodeid])
        return sorted(grouped.items(), key=lambda kv: str(kv[0]))

    def scorecard(self):
        days = []
        for day, results in self._by_day():
            graded = [r for r in results if r.counts]
            floor = [r for r in graded if r.tier == "floor"]
            possible = sum(r.points for r in floor)
            earned = sum(r.earned for r in floor)
            days.append({
                "day": day,
                "passed": bool(floor) and earned == possible,
                "required": f"{earned}/{possible}",
                "earned": sum(r.earned for r in graded),
                "possible": sum(r.points for r in graded),
                "tests": [{"description": r.doc, "tier": r.tier, "points": r.points,
                           "earned": r.earned, "outcome": r.outcome, "message": r.message}
                          for r in results],
            })
        earned = sum(d["earned"] for d in days)
        possible = sum(d["possible"] for d in days)
        return {"days": days, "earned": earned, "possible": possible,
                "percent": round(100 * earned / possible, 1) if possible else 0.0}

    # -- report -------------------------------------------------------------

    def pytest_terminal_summary(self, terminalreporter):
        if not self.results or self.config.getoption("--collect-only"):
            return
        card = self.scorecard()
        write = terminalreporter.write_line
        write("\n" + "=" * 72)
        write("GRADE REPORT".center(72))
        for day in card["days"]:
            write("=" * 72)
            verdict = "COMPLETE" if day["passed"] else "INCOMPLETE"
            write(f"Day {day['day']}  --  {verdict}   ({day['earned']}/{day['possible']} points)")
            write("-" * 72)
            for test in day["tests"]:
                tier = "" if test["tier"] == "floor" else f" [{test['tier']}]"
                write(f"  {_ICON.get(test['outcome'], '?'):<5} {test['earned']}/{test['points']}"
                      f"  {test['description']}{tier}")
                if test["message"]:
                    write(f"          -> {test['message']}")
        write("=" * 72)
        write(f"TOTAL: {card['earned']}/{card['possible']} points ({card['percent']}%)")
        write("=" * 72)

    def pytest_sessionfinish(self, session, exitstatus):
        if not self.results:
            return
        card = self.scorecard()

        path = self.config.getoption("--grade-report")
        if path:
            with open(path, "w") as handle:
                json.dump(card, handle, indent=2)

        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a") as handle:
                handle.write(render_markdown(card))

        floor_clean = not self.had_error and all(
            r.outcome == "passed" for r in self.results.values()
            if r.tier == "floor" and r.counts)
        fail_on = self.config.getoption("--fail-on")
        if fail_on == "never":
            session.exitstatus = 0
        elif fail_on == "floor" and exitstatus == 1 and floor_clean:
            session.exitstatus = 0  # only stretch goals outstanding -- the day still counts


def render_markdown(card):
    lines = ["", "## Grade report", ""]
    for day in card["days"]:
        lines += [f"### Day {day['day']} — {'✅ complete' if day['passed'] else '❌ incomplete'}",
                  "",
                  f"Required: **{day['required']}** · Total: **{day['earned']}/{day['possible']}**",
                  "", "| | Task | Type | Points |", "|---|---|---|---|"]
        for test in day["tests"]:
            lines.append(f"| {_EMOJI.get(test['outcome'], '❔')} | {test['description']} "
                         f"| {_TIER.get(test['tier'], test['tier'])} | {test['earned']}/{test['points']} |")
        failed = [t for t in day["tests"] if t["message"]]
        if failed:
            lines += [""] + [f"- **{t['description']}** — `{t['message']}`" for t in failed]
        lines.append("")
    lines += ["---", "", f"**Overall: {card['earned']}/{card['possible']} ({card['percent']}%)**", ""]
    return "\n".join(lines)
