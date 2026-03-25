"""
generate_calendar.py
────────────────────
Reads a lessons CSV and writes an accessible HTML calendar.

Called by build_all.py — not normally run directly.

CSV format — two modes:

  MODE 1: Absolute dates (any common format)
    date,lesson,notes
    9/2/25,Introduction to Mechanics,
    9/5/25,NO CLASS,Labor Day

  MODE 2: Relative dates (reusable across years)
    date,lesson,notes
    week1 mon,Introduction to Mechanics,
    week1 wed,Vectors and Scalars,
    week2 fri,Newton's First Law,HW 1 due

NOTES COLUMN — bullet lists:
    Separate items with a semicolon ; for a bulleted list:
      "Quiz;HW due;Read ch. 4"
"""

import csv
import sys
import re
import argparse
import calendar
import html
from datetime import date, timedelta, datetime

DAY_ALIASES = {
    "sun": 6, "sunday":    6,
    "mon": 0, "monday":    0,
    "tue": 1, "tuesday":   1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday":  3,
    "fri": 4, "friday":    4,
    "sat": 5, "saturday":  5,
}

DAY_NAMES_FULL  = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
DAY_NAMES_SHORT = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]


# ── Date parsing ──────────────────────────────────────────────────────────────

def parse_date(raw):
    raw = raw.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", raw)
    if m:
        mo, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yr < 100:
            yr += 2000
        try:
            return date(yr, mo, day)
        except ValueError:
            pass
    for fmt in ("%b %d %Y","%B %d %Y","%B %d, %Y","%b %d, %Y","%d %b %Y","%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def parse_relative(raw, week1_monday):
    s = re.sub(r"[^a-z0-9]", " ", raw.strip().lower())
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"week\s*(\d+)\s+([a-z]+)", s) or re.match(r"week(\d+)([a-z]+)", s)
    if not m:
        return None
    week_num, day_name = int(m.group(1)), m.group(2)
    weekday_offset = DAY_ALIASES.get(day_name)
    if weekday_offset is None:
        for alias, offset in DAY_ALIASES.items():
            if len(day_name) >= 2 and (alias.startswith(day_name) or day_name.startswith(alias)):
                weekday_offset = offset
                break
    if weekday_offset is None:
        return None
    day_offset = -1 if weekday_offset == 6 else weekday_offset
    return week1_monday + timedelta(weeks=week_num - 1, days=day_offset)


# ── CSV loading ───────────────────────────────────────────────────────────────

def load_lessons(csv_path, week1_monday=None):
    lessons = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            raw = row.get("date", "").strip()
            if not raw:
                continue
            if week1_monday and re.match(r"week", raw.lower()):
                d = parse_relative(raw, week1_monday)
                if d is None:
                    print(f"  Warning: could not parse '{raw}', skipping.")
                    continue
            else:
                d = parse_date(raw)
                if d is None:
                    print(f"  Warning: could not parse '{raw}', skipping.")
                    continue
            lessons[d] = {
                "lesson": row.get("lesson", "").strip(),
                "notes":  row.get("notes",  "").strip(),
            }
    return lessons


def months_in_data(lessons):
    return sorted({(d.year, d.month) for d in lessons})


# ── Cell helpers ──────────────────────────────────────────────────────────────

def cell_class(t):
    u = t.upper()
    if any(k in u for k in ("NO CLASS","HOLIDAY","BREAK")):
        return "no-class"
    if any(k in u for k in ("QUIZ","TEST","FINAL")):
        return "exam"
    return "lesson" if t else ""

def cell_label(t):
    u = t.upper()
    if any(k in u for k in ("NO CLASS","HOLIDAY","BREAK")):
        return "No class"
    if any(k in u for k in ("QUIZ","TEST","FINAL")):
        return "Quiz or test"
    return ""

def render_notes_html(notes_raw):
    if not notes_raw:
        return ""
    items = [s.strip() for s in notes_raw.split(";") if s.strip()]
    if len(items) == 1:
        return f'<p class="notes">{html.escape(items[0])}</p>'
    lis = "\n".join(f"    <li>{html.escape(i)}</li>" for i in items)
    return f'<ul class="notes">\n{lis}\n</ul>'


# ── HTML generation ───────────────────────────────────────────────────────────

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:16px;line-height:1.5;color:#1a1a2e;background:#f5f6fa;padding:1.5rem 1rem}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
header{background:#2c3e50;color:#fff;padding:1.25rem 1.5rem;border-radius:8px;margin-bottom:2rem}
header h1{font-size:1.6rem;font-weight:700}
header p{font-size:.9rem;opacity:.75;margin-top:.25rem}
.back-link{display:inline-block;margin-bottom:1.5rem;font-size:.9rem;color:#2980b9;text-decoration:none}
.back-link:hover{text-decoration:underline}
.legend{display:flex;flex-wrap:wrap;gap:1rem;margin-bottom:2rem;font-size:.85rem}
.legend-item{display:flex;align-items:center;gap:.4rem}
.legend-swatch{width:1rem;height:1rem;border-radius:3px;border:1px solid rgba(0,0,0,.15);flex-shrink:0}
section{background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:2.5rem;overflow:hidden}
section h2{background:#2c3e50;color:#fff;font-size:1.15rem;padding:.75rem 1.25rem}
table{width:100%;border-collapse:collapse;table-layout:fixed}
thead th{background:#5d6d7e;color:#fff;font-size:.8rem;font-weight:600;text-align:center;padding:.4rem 0;letter-spacing:.03em}
thead th abbr{text-decoration:none;cursor:default}
thead th.weekend-header{background:#4a5568}
td{vertical-align:top;border:1px solid #d1d5db;padding:.35rem .4rem;height:6rem;background:#fff}
td.empty{background:#eaecee}
td.weekend{background:#f7f8f9}
td.no-class{background:#fff0ee}
td.exam{background:#fff8ee}
.day-num{display:block;font-size:.8rem;font-weight:700;color:#2c3e50;margin-bottom:.2rem}
.lesson{font-size:.72rem;line-height:1.35;color:#1a252f;margin-bottom:.15rem}
p.notes{font-size:.65rem;color:#5d6d7e;font-style:italic;line-height:1.3}
ul.notes{font-size:.65rem;color:#5d6d7e;font-style:italic;line-height:1.35;padding-left:1rem;margin-top:.1rem}
td:focus,a:focus,button:focus{outline:3px solid #2980b9;outline-offset:2px}
@media(max-width:700px){td{height:auto;min-height:3.5rem}.lesson{font-size:.65rem}p.notes,ul.notes{font-size:.6rem}}
@media print{body{background:#fff;padding:0;font-size:11px}header{border-radius:0}section{box-shadow:none;page-break-after:always}td{height:5rem}}
"""

LEGEND_HTML = """
<nav aria-label="Calendar legend">
  <ul class="legend" role="list">
    <li class="legend-item">
      <span class="legend-swatch" style="background:#fff0ee" aria-hidden="true"></span>
      No class / Holiday / Break
    </li>
    <li class="legend-item">
      <span class="legend-swatch" style="background:#fff8ee" aria-hidden="true"></span>
      Quiz / Test / Final
    </li>
  </ul>
</nav>
"""


def build_month_html(year, month, lessons):
    month_name = calendar.month_name[month]
    month_id   = f"month-{year}-{month:02d}"
    cal        = calendar.Calendar(firstweekday=6)
    weeks      = cal.monthdayscalendar(year, month)

    header_cells = ""
    for i, (full, short) in enumerate(zip(DAY_NAMES_FULL, DAY_NAMES_SHORT)):
        cls = ' class="weekend-header"' if i in (0, 6) else ""
        header_cells += f'<th scope="col"{cls}><abbr title="{full}">{short}</abbr></th>\n'

    rows_html = ""
    for week in weeks:
        rows_html += "<tr>\n"
        for col_idx, day_num in enumerate(week):
            if day_num == 0:
                rows_html += '<td class="empty" aria-hidden="true"></td>\n'
                continue
            d      = date(year, month, day_num)
            entry  = lessons.get(d)
            lesson = entry["lesson"] if entry else ""
            notes  = entry["notes"]  if entry else ""

            classes = []
            if col_idx in (0, 6):
                classes.append("weekend")
            if entry:
                c = cell_class(lesson)
                if c:
                    classes.append(c)

            class_attr = f' class="{" ".join(classes)}"' if classes else ""
            aria_parts = [f"{DAY_NAMES_FULL[col_idx]}, {month_name} {day_num}, {year}"]
            lbl = cell_label(lesson)
            if lbl:
                aria_parts.append(lbl)
            aria_label = f' aria-label="{", ".join(aria_parts)}"'

            inner  = f'<span class="day-num" aria-hidden="true">{day_num}</span>\n'
            if lesson:
                inner += f'<p class="lesson">{html.escape(lesson)}</p>\n'
            if notes:
                inner += render_notes_html(notes) + "\n"

            rows_html += f"<td{class_attr}{aria_label}>\n{inner}</td>\n"
        rows_html += "</tr>\n"

    return f"""
<section aria-labelledby="{month_id}">
  <h2 id="{month_id}">{month_name} {year}</h2>
  <table role="grid" aria-labelledby="{month_id}">
    <caption class="sr-only">{month_name} {year} class schedule</caption>
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</section>
"""


def build_html(title, months_html, generated_on, back_link=True):
    back = '<a class="back-link" href="../">← All courses</a>' if back_link else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <a class="sr-only" href="#main-content">Skip to main content</a>
  <header role="banner">
    <h1>{html.escape(title)}</h1>
    <p>Updated {generated_on}</p>
  </header>
  {back}
  {LEGEND_HTML}
  <main id="main-content">
    {"".join(months_html)}
  </main>
</body>
</html>"""


def build_calendar(csv_path, out_path, title, week1_monday=None, back_link=True):
    lessons = load_lessons(csv_path, week1_monday)
    if not lessons:
        print(f"  No lessons found in {csv_path}")
        return False

    months     = months_in_data(lessons)
    today      = date.today()
    months_html = [build_month_html(yr, mo, lessons) for yr, mo in months]
    output     = build_html(title, months_html, today.strftime("%B %d, %Y"), back_link)

    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"  ✓ {title}  →  {out_path}")
    return True


# ── Standalone CLI (optional, for local testing) ──────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a single HTML calendar from a CSV.")
    parser.add_argument("csv",  nargs="?", default="lessons.csv")
    parser.add_argument("html", nargs="?", default="calendar.html")
    parser.add_argument("--title",  default="Course Schedule")
    parser.add_argument("--start",  default=None)
    parser.add_argument("--no-back-link", action="store_true")
    args = parser.parse_args()

    week1_monday = None
    if args.start:
        sd = parse_date(args.start)
        if sd is None:
            print(f"Error: cannot parse --start '{args.start}'")
            sys.exit(1)
        week1_monday = sd - timedelta(days=sd.weekday())

    build_calendar(args.csv, args.html, args.title, week1_monday,
                   back_link=not args.no_back_link)
