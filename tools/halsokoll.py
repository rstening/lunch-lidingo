"""Open a GitHub issue when a restaurant has failed for about two days, close it when it works again.

Runs at the end of the daily workflow. GitHub emails the repo owner when an issue is opened.
Needs GITHUB_TOKEN and GITHUB_REPOSITORY (both set in GitHub Actions).
Run locally without them to only print what it would do.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.merge import _iso  # noqa: E402  (after sys.path setup)

DATA_PATH = ROOT / "data" / "menus.json"
# "Two days in a row": the 09:00 run on day 1 and day 2 both failed. 40 hours leaves
# room for GitHub starting scheduled runs late.
FAILING_AFTER = timedelta(hours=40)
MARKER = "<!-- lunch-bot:{id} -->"


def _parse(stamp: Optional[str]) -> Optional[datetime]:
    if not stamp:
        return None
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def failing_restaurants(data: dict, now: datetime) -> List[dict]:
    """Restaurants whose latest run failed and that have not worked for FAILING_AFTER."""
    out = []
    for r in data.get("restaurants", []):
        if not r.get("error"):
            continue
        last = _parse(r.get("last_success"))
        if last is None or now - last >= FAILING_AFTER:
            out.append(r)
    return out


def issue_for(issues: List[dict], rid: str) -> Optional[dict]:
    marker = MARKER.format(id=rid)
    for issue in issues:
        if marker in (issue.get("body") or ""):
            return issue
    return None


def plan(data: dict, open_issues: List[dict], now: datetime) -> Tuple[List[dict], List[Tuple[dict, dict]]]:
    """Return (restaurants to open an issue for, (restaurant, issue) pairs to close)."""
    failing = failing_restaurants(data, now)
    failing_ids = {r["id"] for r in failing}
    to_open = [r for r in failing if issue_for(open_issues, r["id"]) is None]
    to_close = []
    for r in data.get("restaurants", []):
        issue = issue_for(open_issues, r["id"])
        if issue is not None and r["id"] not in failing_ids and not r.get("error"):
            to_close.append((r, issue))
    return to_open, to_close


def issue_body(r: dict, run_url: str) -> str:
    last = _parse(r.get("last_success"))
    last_text = last.strftime("%Y-%m-%d %H:%M UTC") if last else "aldrig"
    return (f"{MARKER.format(id=r['id'])}\n"
            f"Hämtningen av menyn från **{r['name']}** har misslyckats i ungefär två dagar.\n\n"
            f"- Senaste fel: `{r.get('error')}`\n"
            f"- Senast lyckad hämtning: {last_text}\n"
            f"- Restaurangens sida: {r.get('url')}\n"
            f"- Körningen: {run_url}\n\n"
            "Sidan visar restaurangens senaste meny tills vidare. "
            "Ärendet stängs automatiskt när hämtningen fungerar igen.")


def main() -> int:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_url = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}"
               f"/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}")

    if not token or not repo:
        for r in failing_restaurants(data, now):
            print(f"Skulle öppna ärende: {r['name']} ({r.get('error')})")
        print(f"Kontrollerade {len(data.get('restaurants', []))} restauranger kl {_iso(now)}")
        return 0

    import requests
    api = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    resp = requests.get(api, headers=headers, params={"state": "open", "per_page": 100}, timeout=20)
    resp.raise_for_status()
    open_issues = [i for i in resp.json() if "pull_request" not in i]

    to_open, to_close = plan(data, open_issues, now)
    for r in to_open:
        payload: Dict[str, str] = {"title": f"Hämtningen av {r['name']} fungerar inte",
                                   "body": issue_body(r, run_url)}
        requests.post(api, headers=headers, json=payload, timeout=20).raise_for_status()
        print(f"Öppnade ärende för {r['name']}")
    for r, issue in to_close:
        url = f"{api}/{issue['number']}"
        requests.post(f"{url}/comments", headers=headers, timeout=20,
                      json={"body": f"Hämtningen av {r['name']} fungerar igen. Stänger ärendet."}
                      ).raise_for_status()
        requests.patch(url, headers=headers, json={"state": "closed"}, timeout=20).raise_for_status()
        print(f"Stängde ärende för {r['name']}")
    if not to_open and not to_close:
        print("Inget att göra")
    return 0


if __name__ == "__main__":
    sys.exit(main())
