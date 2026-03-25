"""
build_all.py
────────────
Reads courses.yaml, generates an HTML calendar for every course,
and builds an index page that links to all of them.

Run locally:   python build_all.py
GitHub Actions runs this automatically on every push.

Output layout:
  docs/
    index.html              ← course listing page
    physics101/
      index.html            ← Physics 101 calendar
    thermodynamics/
      index.html            ← Thermodynamics calendar
    ...
"""

import os
import sys
import html
import yaml
from datetime import date, timedelta
from pathlib import Path

# Allow importing generate_calendar from the scripts/ folder
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from generate_calendar import build_calendar, parse_date

ROOT      = Path(__file__).parent          # repo root
COURSES   = ROOT / "courses.yaml"
COURSES_DIR = ROOT / "courses"             # CSV files live here
OUT_DIR   = ROOT / "docs"                  # GitHub Pages serves from docs/


# ── Index page CSS & HTML ────────────────────────────────────────────────────

INDEX_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     font-size:16px;line-height:1.5;color:#1a1a2e;background:#f5f6fa;padding:2rem 1rem}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
         overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
header{background:#2c3e50;color:#fff;padding:1.5rem 2rem;border-radius:8px;margin-bottom:2rem}
header h1{font-size:1.8rem;font-weight:700}
header p{font-size:.95rem;opacity:.75;margin-top:.3rem}
.course-list{list-style:none;display:grid;
             grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.25rem}
.course-card{background:#fff;border-radius:8px;
             box-shadow:0 1px 4px rgba(0,0,0,.09);overflow:hidden;
             transition:box-shadow .15s}
.course-card:hover{box-shadow:0 3px 10px rgba(0,0,0,.14)}
.course-card a{display:block;padding:1.4rem 1.6rem;text-decoration:none;color:inherit}
.course-card h2{font-size:1.1rem;font-weight:600;color:#2c3e50;margin-bottom:.3rem}
.course-card p{font-size:.85rem;color:#7f8c8d}
.course-card .arrow{float:right;color:#2980b9;font-size:1.2rem;margin-top:.1rem}
footer{text-align:center;font-size:.8rem;color:#aaa;margin-top:3rem}
a:focus{outline:3px solid #2980b9;outline-offset:2px;border-radius:2px}
"""


def build_index(courses, generated_on):
    cards = ""
    for c in courses:
        slug  = c["slug"]
        title = html.escape(c["title"])
        start = html.escape(c.get("start", ""))
        cards += f"""
  <li class="course-card">
    <a href="{slug}/" aria-label="Open calendar for {title}">
      <span class="arrow" aria-hidden="true">→</span>
      <h2>{title}</h2>
      <p>Starts {start}</p>
    </a>
  </li>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Course Calendars</title>
  <style>{INDEX_CSS}</style>
</head>
<body>
  <a class="sr-only" href="#main-content">Skip to main content</a>
  <header role="banner">
    <h1>Course Calendars</h1>
    <p>Updated {generated_on}</p>
  </header>
  <main id="main-content">
    <ul class="course-list" role="list">
      {cards}
    </ul>
  </main>
  <footer>
    <p>Select a course to view its schedule.</p>
  </footer>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not COURSES.exists():
        print(f"Error: {COURSES} not found.")
        sys.exit(1)

    with open(COURSES, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    course_list = config.get("courses", [])
    if not course_list:
        print("No courses found in courses.yaml.")
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)
    today        = date.today()
    generated_on = today.strftime("%B %d, %Y")
    built        = []
    errors       = []

    for course in course_list:
        csv_file = course.get("file", "")
        title    = course.get("title", csv_file)
        start    = course.get("start", "")

        # Derive URL slug from filename  e.g. physics101.csv → physics101
        slug = Path(csv_file).stem
        course["slug"] = slug

        csv_path = COURSES_DIR / csv_file
        out_path = OUT_DIR / slug / "index.html"

        if not csv_path.exists():
            print(f"  ✗ {csv_file} not found in courses/ — skipping.")
            errors.append(title)
            continue

        # Resolve week1 monday from start date
        week1_monday = None
        if start:
            sd = parse_date(str(start))
            if sd:
                week1_monday = sd - timedelta(days=sd.weekday())
            else:
                print(f"  Warning: cannot parse start date '{start}' for {title}")

        ok = build_calendar(
            csv_path    = str(csv_path),
            out_path    = str(out_path),
            title       = title,
            week1_monday= week1_monday,
            back_link   = True,
        )
        if ok:
            built.append(course)
        else:
            errors.append(title)

    # Write index page
    index_html = build_index(built, generated_on)
    index_path = OUT_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"\n  ✓ Index page  →  {index_path}")

    print(f"\nDone. Built {len(built)} calendar(s).", end="")
    if errors:
        print(f"  Skipped: {', '.join(errors)}")
    else:
        print()


if __name__ == "__main__":
    main()
