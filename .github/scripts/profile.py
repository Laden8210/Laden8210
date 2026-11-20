"""Profile README automation (run by GitHub Actions, stdlib only).

    python .github/scripts/profile.py stats     -> assets/stats.svg (live numbers, count-up animation)
    python .github/scripts/profile.py activity  -> README section between ACTIVITY markers
    python .github/scripts/profile.py ttt       -> play one tic-tac-toe move from an issue
                                                   (env: TITLE, PLAYER; writes .github/ttt/comment.md)
"""
import json
import os
import random
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER = "Laden8210"
REPO = f"{USER}/{USER}"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
README = os.path.join(ROOT, "README.md")
NAVY, BLUE, ORANGE = "#1B2F4B", "#7FB8C9", "#E8A33D"
SANS = "'Segoe UI', Helvetica, Arial, sans-serif"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": "profile-readme-bot"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def graphql(query):
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-readme-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]


def replace_section(name, body):
    text = open(README, encoding="utf-8").read()
    start, end = f"<!--{name}:START-->", f"<!--{name}:END-->"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        sys.exit(f"markers {start} / {end} not found in README")
    text = pat.sub(lambda _: f"{start}\n{body}\n{end}", text)
    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ------------------------------------------------------------------ stats
def stats():
    try:
        q = graphql(f'{{ user(login: "{USER}") {{ contributionsCollection {{ contributionCalendar {{ totalContributions }} }} }} }}')
        contribs = q["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        live = (contribs, "", "Contributions", "last 12 months · live")
    except Exception as exc:  # fall back to a REST number
        print(f"graphql failed: {exc}")
        live = (api(f"/users/{USER}").get("public_repos", 0), "", "Public repos", "live from GitHub")
    years = max(1, datetime.now(timezone.utc).year - 2023)
    tiles = [
        (20, "+", "Projects shipped", "web · mobile · cloud · AI"),
        live,
        (years, "+", "Years shipping", "freelancing since 2023"),
        (2, "", "Certifications", "TESDA · TryHackMe"),
    ]
    W, H = 900, 150
    tw = (W - 40 - 3 * 16) / 4
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">',
         f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1F3757"/><stop offset="1" stop-color="#0A1424"/></linearGradient>'
         f'<filter id="gl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>']
    for i, (n, suf, label, sub) in enumerate(tiles):
        x = 20 + i * (tw + 16)
        col = ORANGE if i % 2 == 0 else BLUE
        b = 0.2 + i * 0.15
        p.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{b:.2f}s" fill="freeze"/>'
                 f'<rect x="{x}" y="10" width="{tw:.1f}" height="{H-20}" rx="16" fill="url(#bg)" stroke="{col}" stroke-opacity="0.45"/>'
                 f'<rect x="{x+20}" y="{H-30}" height="3" rx="1.5" fill="{col}" width="0"><animate attributeName="width" from="0" to="{tw-40:.0f}" dur="1.4s" begin="{b:.2f}s" fill="freeze"/></rect>')
        steps = 12
        for k in range(steps + 1):
            v = round(n * k / steps)
            t0, t1 = k / steps, (k + 1) / steps
            vis = (f'values="0;1" keyTimes="0;{t0:.3f}"' if k == steps else f'values="0;1;0" keyTimes="0;{t0:.3f};{t1:.3f}"')
            p.append(f'<text x="{x+20}" y="62" font-size="36" font-weight="800" fill="#FFFFFF" opacity="0"'
                     f'{" filter=\"url(#gl)\"" if k == steps else ""}>{v}<tspan fill="{col}">{suf}</tspan>'
                     f'<animate attributeName="opacity" {vis} calcMode="discrete" dur="1.4s" begin="{b:.2f}s" fill="freeze"/></text>')
        p.append(f'<text x="{x+20}" y="88" font-size="14" font-weight="700" fill="{col}">{label}</text>'
                 f'<text x="{x+20}" y="108" font-size="11.5" fill="#8FA6BD">{sub}</text></g>')
    p.append('</svg>')
    with open(os.path.join(ROOT, "assets", "stats.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(p))
    print(f"stats: {live[2]}={live[0]} years={years}")


# ------------------------------------------------------------------ activity
def activity():
    """30-day summary from the contributions graph (the public events feed is empty
    for this account), plus the most recently updated public repos."""
    now = datetime.now(timezone.utc)
    frm = now.replace(microsecond=0) - __import__("datetime").timedelta(days=30)
    q = graphql(
        f'{{ user(login: "{USER}") {{ contributionsCollection(from: "{frm.isoformat()}", to: "{now.replace(microsecond=0).isoformat()}") {{'
        ' totalCommitContributions totalPullRequestContributions totalPullRequestReviewContributions'
        ' totalIssueContributions restrictedContributionsCount'
        ' commitContributionsByRepository(maxRepositories: 5) { repository { name url isPrivate } contributions { totalCount } } } } }')
    c = q["user"]["contributionsCollection"]
    total = (c["totalCommitContributions"] + c["totalPullRequestContributions"] + c["totalPullRequestReviewContributions"]
             + c["totalIssueContributions"] + c["restrictedContributionsCount"])
    parts = [f"**{c['totalCommitContributions']}** public commits"]
    for key, label in (("totalPullRequestContributions", "PRs"), ("totalPullRequestReviewContributions", "reviews"), ("totalIssueContributions", "issues")):
        if c[key]:
            parts.append(f"**{c[key]}** {label}")
    if c["restrictedContributionsCount"]:
        parts.append(f"**{c['restrictedContributionsCount']}** in private client repos 🔒")
    lines = [f"📊 **{total} contributions in the last 30 days**: " + " · ".join(parts)]
    for r in c["commitContributionsByRepository"]:
        repo = r["repository"]
        if not repo["isPrivate"]:
            n = r["contributions"]["totalCount"]
            lines.append(f"🔨 {n} commit{'s' if n != 1 else ''} to [{repo['name']}]({repo['url']})")
    for repo in api(f"/users/{USER}/repos?sort=pushed&per_page=3&type=owner"):
        days = (now - datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))).days
        if days > 90:
            continue
        ago = "today" if days == 0 else ("yesterday" if days == 1 else f"{days} days ago")
        lines.append(f"🕒 Updated [{repo['name']}]({repo['html_url']}) · <sub>{ago}</sub>")
    replace_section("ACTIVITY", "\n".join(f"- {l}" for l in lines))
    print(f"activity: total={total}")


# ------------------------------------------------------------------ tic-tac-toe
STATE = os.path.join(ROOT, ".github", "ttt", "state.json")
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def winner(b):
    for a, c, d in LINES:
        if b[a] != " " and b[a] == b[c] == b[d]:
            return b[a]
    return "draw" if " " not in b else None


def bot_move(b):
    free = [i for i in range(9) if b[i] == " "]
    for mark in ("O", "X"):  # win, then block
        for i in free:
            t = b[:i] + mark + b[i + 1:]
            if winner(t) == mark:
                return i
    if random.random() < 0.25:  # stay beatable
        return random.choice(free)
    for group in ([4], [0, 2, 6, 8], [1, 3, 5, 7]):
        opts = [i for i in group if i in free]
        if opts:
            return random.choice(opts)
    return free[0]


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"board": " " * 9, "status": "playing", "stats": {"you": 0, "bot": 0, "draw": 0}, "moves": []}


def render(st):
    url = f"https://github.com/{REPO}/issues/new"
    body = "Just+press+%22Create%22+%E2%80%94+no+need+to+write+anything.+The+bot+answers+in+about+a+minute."
    rows = []
    for r in range(3):
        cells = []
        for c in range(3):
            i = r * 3 + c
            v = st["board"][i]
            if v == "X":
                cells.append('<img src="./assets/ttt/x.svg" width="86" alt="X" />')
            elif v == "O":
                cells.append('<img src="./assets/ttt/o.svg" width="86" alt="O" />')
            elif st["status"] == "playing":
                cells.append(f'<a href="{url}?title=ttt%7Cmove%7C{i}&body={body}"><img src="./assets/ttt/empty.svg" width="86" alt="play square {i+1}" /></a>')
            else:
                cells.append('<img src="./assets/ttt/empty.svg" width="86" alt="empty" />')
        rows.append('<p align="center">\n  ' + "\n  ".join(cells) + "\n</p>")
    s = st["stats"]
    if st["status"] == "playing":
        head = "<b>Your turn — you are ❌.</b> Click any empty square, then press <i>Create</i> on the issue page."
    else:
        res = {"X": "🏆 A visitor beat the bot!", "O": "🤖 The bot won this one.", "draw": "🤝 It's a draw."}[st["status"]]
        head = f'<b>{res}</b> <a href="{url}?title=ttt%7Cnew&body={body}">Start a new game →</a>'
    recent = ", ".join(f"[@{m['user']}](https://github.com/{m['user']})" for m in st["moves"][-5:][::-1]) or "_be the first!_"
    return (f'<p align="center">{head}</p>\n\n' + "\n".join(rows) +
            f'\n\n<p align="center"><sub>Scoreboard · visitors <b>{s["you"]}</b> · bot <b>{s["bot"]}</b> · draws <b>{s["draw"]}</b>'
            f'<br/>Latest players: {recent}</sub></p>')


def ttt():
    title = os.environ.get("TITLE", "").strip()
    player = re.sub(r"[^A-Za-z0-9-]", "", os.environ.get("PLAYER", "someone"))[:39] or "someone"
    st = load()
    msg = ""
    m = re.fullmatch(r"ttt\|move\|([0-8])", title)
    if title == "ttt|new":
        if st["status"] == "playing" and st["board"].strip():
            msg = "A game is already in progress — jump in and make a move on the profile!"
        else:
            st.update(board=" " * 9, status="playing")
            msg = "New game started. Your move! 🎮"
    elif m:
        i = int(m.group(1))
        b = st["board"]
        if st["status"] != "playing":
            msg = "That game is over — start a new one from the profile. 🙂"
        elif b[i] != " ":
            msg = "Someone already took that square — pick another one on the profile!"
        else:
            b = b[:i] + "X" + b[i + 1:]
            st["moves"].append({"user": player, "cell": i})
            w = winner(b)
            if not w:
                j = bot_move(b)
                b = b[:j] + "O" + b[j + 1:]
                w = winner(b)
                msg = f"You played square {i+1}; the bot answered with square {j+1}."
            st["board"] = b
            if w:
                st["status"] = w
                key = {"X": "you", "O": "bot", "draw": "draw"}[w]
                st["stats"][key] += 1
                msg += {"X": " 🏆 You won! Nice.", "O": " 🤖 The bot wins this round.", "draw": " 🤝 It's a draw."}[w]
    else:
        msg = "I only understand moves made from the board on the profile. 🙂"
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    st["moves"] = st["moves"][-50:]
    with open(STATE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(st, f, indent=1)
    replace_section("TTT", render(st))
    with open(os.path.join(ROOT, ".github", "ttt", "comment.md"), "w", encoding="utf-8") as f:
        f.write(f"{msg}\n\n👉 [Back to the board](https://github.com/{USER}#-play-tic-tac-toe-with-me)\n")
    print(msg)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    for cmd in sys.argv[1:]:
        {"stats": stats, "activity": activity, "ttt": ttt, "render": lambda: replace_section("TTT", render(load()))}[cmd]()
