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
def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def activity():
    """Animated 30-day activity panel built from the contributions graph (the public
    events feed is empty for this account) + text links to recently updated repos."""
    from datetime import timedelta
    now = datetime.now(timezone.utc).replace(microsecond=0)
    frm = now - timedelta(days=29)
    q = graphql(
        f'{{ user(login: "{USER}") {{ contributionsCollection(from: "{frm.isoformat()}", to: "{now.isoformat()}") {{'
        ' totalCommitContributions totalPullRequestContributions totalPullRequestReviewContributions'
        ' totalIssueContributions restrictedContributionsCount'
        ' contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }')
    c = q["user"]["contributionsCollection"]
    days = [d for w in c["contributionCalendar"]["weeks"] for d in w["contributionDays"]][-30:]
    total = sum(d["contributionCount"] for d in days)
    public = (c["totalCommitContributions"] + c["totalPullRequestContributions"]
              + c["totalPullRequestReviewContributions"] + c["totalIssueContributions"])
    private = c["restrictedContributionsCount"]
    best = max(days, key=lambda d: d["contributionCount"]) if days else None
    active = sum(1 for d in days if d["contributionCount"])
    repos = []
    for repo in api(f"/users/{USER}/repos?sort=pushed&per_page=4&type=owner"):
        ago_d = (now - datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))).days
        if ago_d <= 90:
            ago = "today" if ago_d == 0 else ("yesterday" if ago_d == 1 else f"{ago_d}d ago")
            repos.append((repo["name"], repo["html_url"], ago))

    W, H = 900, 300
    glow = ' filter="url(#gl)"'
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{SANS}">',
         '<defs><radialGradient id="bg" cx="30%" cy="20%" r="90%"><stop offset="0" stop-color="#16294A"/><stop offset="1" stop-color="#080F1C"/></radialGradient>'
         f'<linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{NAVY}"/><stop offset="1" stop-color="{BLUE}"/></linearGradient>'
         '<filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
         f'<rect width="{W}" height="{H}" rx="16" fill="url(#bg)"/>',
         '<circle cx="32" cy="34" r="5" fill="#3FB950"><animate attributeName="opacity" values="1;0.3;1" dur="1.4s" repeatCount="indefinite"/></circle>'
         '<circle cx="32" cy="34" r="5" fill="none" stroke="#3FB950"><animate attributeName="r" values="5;13" dur="1.4s" repeatCount="indefinite"/><animate attributeName="opacity" values="0.8;0" dur="1.4s" repeatCount="indefinite"/></circle>'
         '<text x="46" y="39" font-size="12" font-weight="800" letter-spacing="2" fill="#3FB950">LIVE · LAST 30 DAYS</text>',
         f'<text x="{W-24}" y="39" text-anchor="end" font-size="11.5" fill="#8FA6BD">updated {now:%b %d, %Y %H:%M} UTC</text>']
    # big counter
    steps = 14
    for k in range(steps + 1):
        v = round(total * k / steps)
        if k == steps:
            vis = f'values="0;1" keyTimes="0;{k/steps:.3f}"'
        else:
            vis = f'values="0;1;0" keyTimes="0;{k/steps:.3f};{(k+1)/steps:.3f}"'
        p.append(f'<text x="28" y="104" font-size="52" font-weight="800" fill="#FFFFFF" opacity="0"{glow if k == steps else ""}>{v}'
                 f'<animate attributeName="opacity" {vis} calcMode="discrete" dur="1.6s" begin="0.2s" fill="freeze"/></text>')
    p.append(f'<text x="30" y="128" font-size="14" font-weight="700" fill="{ORANGE}">contributions</text>')
    rows = [(f"{public}", "public", BLUE), (f"{private}", "private client work 🔒", ORANGE), (f"{active}/30", "active days", BLUE)]
    if best and best["contributionCount"]:
        rows.append((f'{best["contributionCount"]}', f'best day · {datetime.fromisoformat(best["date"]):%b %d}', ORANGE))
    for i, (n, lbl, col) in enumerate(rows):
        y = 158 + i * 26
        p.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{0.6+i*0.2:.1f}s" fill="freeze"/>'
                 f'<rect x="28" y="{y-13}" width="5" height="18" rx="2.5" fill="{col}"/>'
                 f'<text x="42" y="{y+1}" font-size="15" font-weight="800" fill="#FFFFFF">{esc(n)}</text>'
                 f'<text x="{48 + len(n)*9}" y="{y+1}" font-size="13" fill="#C9D6E3">{esc(lbl)}</text></g>')
    # bar chart of real daily contributions
    cx0, cy0, cw, ch = 300, 62, 572, 150
    mx = max([d["contributionCount"] for d in days] + [1])
    bw = cw / max(len(days), 1)
    p.append(f'<line x1="{cx0}" x2="{cx0+cw}" y1="{cy0+ch}" y2="{cy0+ch}" stroke="{BLUE}" stroke-opacity="0.25"/>')
    for i, d in enumerate(days):
        n = d["contributionCount"]
        h = max(3, ch * n / mx) if n else 3
        x = cx0 + i * bw + bw * 0.18
        w = bw * 0.64
        last = i == len(days) - 1
        fill = ORANGE if last else ("url(#bar)" if n else BLUE)
        op = 1 if (n or last) else 0.18
        pulse = '<animate attributeName="opacity" values="1;0.55;1" dur="1.6s" begin="2s" repeatCount="indefinite"/>' if last else ""
        p.append(f'<rect x="{x:.1f}" y="{cy0+ch}" width="{w:.1f}" height="0" rx="2" fill="{fill}" opacity="{op}"{glow if last else ""}>'
                 f'<animate attributeName="height" from="0" to="{h:.1f}" dur="0.5s" begin="{0.3+i*0.04:.2f}s" fill="freeze"/>'
                 f'<animate attributeName="y" from="{cy0+ch}" to="{cy0+ch-h:.1f}" dur="0.5s" begin="{0.3+i*0.04:.2f}s" fill="freeze"/>{pulse}</rect>')
    if days:
        p.append(f'<text x="{cx0}" y="{cy0+ch+18}" font-size="11" fill="#8FA6BD">{datetime.fromisoformat(days[0]["date"]):%b %d}</text>'
                 f'<text x="{cx0+cw}" y="{cy0+ch+18}" text-anchor="end" font-size="11" font-weight="700" fill="{ORANGE}">today</text>')
    # recent repos
    x = 300
    for i, (name, _, ago) in enumerate(repos[:3]):
        label = f"{name} · {ago}"
        w = len(label) * 7.2 + 34
        p.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{1.6+i*0.2:.1f}s" fill="freeze"/>'
                 f'<rect x="{x}" y="{H-50}" width="{w:.0f}" height="28" rx="14" fill="{NAVY}" stroke="{BLUE}" stroke-opacity="0.5"/>'
                 f'<text x="{x+14}" y="{H-31}" font-size="12.5" fill="#FFFFFF">🕒 <tspan fill="{BLUE}" font-weight="700">{esc(name)}</tspan> · {ago}</text></g>')
        x += w + 10
    p.append(f'<text x="30" y="{H-31}" font-size="12" fill="#8FA6BD">recently updated →</text>')
    p.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="16" fill="none" stroke="{BLUE}" stroke-opacity="0.35"/></svg>')
    with open(os.path.join(ROOT, "assets", "activity.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(p))
    links = " · ".join(f'<a href="{u}">{esc(n)}</a>' for n, u, _ in repos) or "<i>none in the last 90 days</i>"
    replace_section("ACTIVITY",
                    f'<p align="center">\n  <img src="./assets/activity.svg" width="100%" alt="{total} contributions in the last 30 days: '
                    f'{public} public, {private} in private repos" />\n</p>\n\n<p align="center"><sub>🕒 Recently updated: {links}</sub></p>')
    print(f"activity: total={total} public={public} private={private} days={len(days)}")


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
