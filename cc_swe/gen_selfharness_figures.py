"""Generate the Self-Harness infographics (SVG) for the repo README.
Palette matches the existing assets/*.svg. Writes into assets/self_harness/."""
import os
FONT = 'system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif'
BG, INK, SUB, GRAY, LINE = '#f9f7f4', '#1a1814', '#4a4640', '#7a756e', '#e8e3dc'
ORANGE, GREEN, RED, BLUE = '#c17f3a', '#2d7a4a', '#b84040', '#3a6ea5'
OUT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'self_harness')
os.makedirs(OUT, exist_ok=True)


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def T(x, y, s, size=13, w=400, fill=INK, anchor='start', ls=None, style=None):
    a = f' letter-spacing="{ls}"' if ls else ''
    st = f' font-style="{style}"' if style else ''
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}"{a}{st}>{esc(s)}</text>'


def R(x, y, w, h, fill, rx=6, stroke=None, sw=1, dash=None):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}{d}/>'


def L(x1, y1, x2, y2, stroke=GRAY, sw=1.3, dash=None, marker=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    m = f' marker-end="url(#{marker})"' if marker else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}{m}/>'


def head(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>'
            f'<defs>'
            f'<marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="{GRAY}"/></marker>'
            f'<marker id="ag" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="{GREEN}"/></marker>'
            f'<marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="{RED}"/></marker>'
            f'</defs>')


def chip(x, y, letter, kind):
    """A role box. kind: draft/fix/write_test."""
    fill = {'D': INK, 'F': GREEN, 'W': BLUE}[letter]
    name = {'D': 'draft', 'F': 'fix', 'W': 'write_test'}[letter]
    w = 30
    return R(x, y, w, 26, fill, rx=6) + T(x + w / 2, y + 17, letter, 14, 800, '#fff', 'middle'), x + w, name


def chain(x, y, roles, gap=12):
    """Draw a role chain, return svg + end x."""
    svg = ''
    cx = x
    letters = {'draft': 'D', 'fix': 'F', 'write_test': 'W'}
    for i, r in enumerate(roles):
        if i:
            svg += L(cx + 1, y + 13, cx + gap - 1, y + 13, GRAY, 1.4, marker='a')
            cx += gap
        s, cx2, _ = chip(cx, y, letters[r], r)
        svg += s
        cx = cx2
    return svg, cx


# ============================================================ 1. HERO — evolution trajectory
def hero():
    W, H = 1000, 430
    s = head(W, H)
    s += T(44, 34, 'SELF-HARNESS · SWE-BENCH VERIFIED', 11, 700, ORANGE, ls='0.14em')
    s += T(44, 64, 'A fixed Haiku model rebuilt its own harness — and resolved 64% → 82% of issues', 22, 800, INK)
    s += T(44, 88, 'No weight updates. No stronger model. Haiku reads its own failures, proposes bounded harness edits, and a two-split verifier keeps only what helps.', 13, 400, SUB)
    stages = [
        ('h₀', ['draft'], 64, 'minimal seed', 'single draft = 1-shot Haiku', GRAY),
        ('h₁', ['draft', 'fix'], 64, '+ refine step', 'authored a root-cause runtime policy', GREEN),
        ('h₂', ['draft', 'write_test', 'fix'], 82, '+ write_test step', 'independent reproduction test', BLUE),
        ('h₃', ['draft', 'write_test', 'fix'], 82, 'locked in', 'round-3 edits all rejected → carried', GRAY),
    ]
    cx0, cardw, gap, top, cardh = 44, 216, 22, 120, 250
    for i, (name, roles, pct, delta, cap, dc) in enumerate(stages):
        x = cx0 + i * (cardw + gap)
        s += R(x, top, cardw, cardh, '#fff', rx=12, stroke=LINE, sw=1.2)
        s += T(x + 16, top + 30, name, 18, 800, INK)
        # resolved % big
        s += T(x + cardw - 16, top + 34, f'{pct}%', 26, 800, GREEN if pct >= 82 else SUB, 'end')
        s += T(x + cardw - 16, top + 50, 'resolved', 10, 400, GRAY, 'end')
        # % bar
        bw = cardw - 32
        s += R(x + 16, top + 60, bw, 7, LINE, rx=3)
        s += R(x + 16, top + 60, bw * pct / 100, 7, GREEN if pct >= 82 else GRAY, rx=3)
        # chain
        cs, _ = chain(x + 16, top + 92, roles)
        s += cs
        # divider
        s += L(x + 16, top + 138, x + cardw - 16, top + 138, LINE, 1)
        # change label + caption
        s += T(x + 16, top + 162, delta, 13, 800, dc)
        # wrap caption (~24 chars)
        words = cap.split(); lines = []; cur = ''
        for wd in words:
            if len(cur) + len(wd) + 1 > 26:
                lines.append(cur); cur = wd
            else:
                cur = (cur + ' ' + wd).strip()
        lines.append(cur)
        for j, ln in enumerate(lines[:3]):
            s += T(x + 16, top + 184 + j * 16, ln, 11.5, 400, SUB)
        # arrow to next
        if i < 3:
            ax = x + cardw + 3
            s += L(ax, top + cardh / 2, ax + gap - 6, top + cardh / 2, GRAY, 1.6, marker='a')
    s += T(44, H - 22, 'Each step is the model’s own edit, accepted only after re-solving the benchmark. The big jump comes when Haiku adds the reproduction-test step it diagnosed it was missing.', 11.5, 400, GRAY)
    return s + '</svg>'


# ============================================================ 2. LOOP — the self-improvement cycle
def loop():
    W, H = 1000, 300
    s = head(W, H)
    s += T(44, 34, 'THE SELF-IMPROVEMENT LOOP', 11, 700, ORANGE, ls='0.14em')
    s += T(44, 60, 'One fixed model plays every role — miner, proposer, and the harness being improved', 18, 800, INK)
    boxes = [
        ('1 · WEAKNESS MINING', ['Run the current harness,', 'cluster its verifier-grounded', 'failures into patterns.'], BLUE),
        ('2 · HARNESS PROPOSAL', ['Propose K bounded, minimal', 'edits to declared surfaces', '(structure · prompts · runtime).'], ORANGE),
        ('3 · VALIDATION', ['Re-solve on two splits;', 'accept iff non-regressive', '(Δin ≥ 0 ∧ Δout ≥ 0 ∧ max > 0).'], GREEN),
        ('4 · MERGE', ['Compose accepted edits over', 'disjoint surfaces → next', 'harness. Repeat.'], INK),
    ]
    bx, bw, gap, by, bh = 44, 216, 22, 90, 130
    for i, (title, lines, c) in enumerate(boxes):
        x = bx + i * (bw + gap)
        s += R(x, by, bw, bh, '#fff', rx=10, stroke=c, sw=1.6)
        s += R(x, by, bw, 5, c, rx=0)
        s += T(x + 14, by + 30, title, 11.5, 800, c)
        for j, ln in enumerate(lines):
            s += T(x + 14, by + 54 + j * 18, ln, 11.5, 400, SUB)
        if i < 3:
            ax = x + bw + 3
            s += L(ax, by + bh / 2, ax + gap - 6, by + bh / 2, GRAY, 1.6, marker='a')
    # feedback arrow
    s += f'<path d="M {bx+3*(bw+gap)+bw/2} {by+bh+8} C {bx+3*(bw+gap)+bw/2} {by+bh+40}, {bx+bw/2} {by+bh+40}, {bx+bw/2} {by+bh+8}" fill="none" stroke="{GRAY}" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#a)"/>'
    s += T(W / 2, by + bh + 44, 'the accepted harness becomes the next round’s starting point', 11.5, 400, GRAY, 'middle')
    s += T(44, H - 16, 'The proposer is Haiku itself (not a stronger model) — the distinction from Meta-Harness / GEPA, where a larger model mutates the harness.', 11.5, 400, GRAY)
    return s + '</svg>'


# ============================================================ 3. WHAT EVOLVED — structure / runtime / prompts
def evolved():
    W, H = 1000, 440
    s = head(W, H)
    s += T(44, 34, 'WHAT THE MODEL EVOLVED', 11, 700, ORANGE, ls='0.14em')
    s += T(44, 60, 'Most of the gain was structure and runtime policy — not prose', 18, 800, INK)
    colw, gap, x0, top = 300, 24, 44, 88
    # --- col 1: structure ---
    x = x0
    s += T(x, top, 'STRUCTURE', 12, 800, INK)
    for j, roles in enumerate([['draft'], ['draft', 'fix'], ['draft', 'write_test', 'fix']]):
        yy = top + 30 + j * 46
        s += T(x, yy + 17, ['h₀', 'h₁', 'h₂'][j], 12, 700, GRAY)
        cs, _ = chain(x + 34, yy, roles)
        s += cs
    s += T(x, top + 190, 'D → D·F → D·W·F', 13, 800, GREEN)
    s += T(x, top + 212, 'grew a refine step, then an', 11.5, 400, SUB)
    s += T(x, top + 228, 'independent reproduction-test step.', 11.5, 400, SUB)
    # --- col 2: runtime policy ---
    x = x0 + colw + gap
    s += T(x, top, 'RUNTIME POLICY  (harness.json)', 12, 800, INK)
    s += R(x, top + 14, colw, 30, '#fdf3ec', rx=6, stroke=LINE)
    s += T(x + 12, top + 33, 'h₀:  { }  — empty', 12, 600, GRAY)
    fields = ['system_preamble — root-cause rule', 'bootstrap — 5-step scope analysis',
              'verification — independent repro test', 'failure_recovery + error_middleware',
              'max_tool_calls = 100', 'redirect_after_calls = 35']
    s += T(x, top + 66, 'authored from empty →', 11.5, 700, GREEN)
    for j, f in enumerate(fields):
        yy = top + 84 + j * 22
        s += R(x, yy, colw, 18, '#fff', rx=4, stroke=LINE)
        s += T(x + 8, yy + 13, '+ ' + f, 11, 500, SUB)
    # --- col 3: prompts ---
    x = x0 + 2 * (colw + gap)
    s += T(x, top, 'PROMPTS  (surgical)', 12, 800, INK)
    rows = [('draft.md', 'changed', GREEN, '+ “your fix WILL be validated'), ('', '', GREEN, '  against a reproduction test”'),
            ('fix.md', 'changed', GREEN, '+ “if the test still fails, you'), ('', '', GREEN, '  fixed a symptom, not the cause”'),
            ('write_test.md', 'unchanged', GRAY, ''), ('critique.md', 'unchanged', GRAY, '')]
    yy = top + 20
    for name, tag, c, note in rows:
        if name:
            s += T(x, yy + 13, name, 12, 700, INK)
            s += R(x + 96, yy, 74, 18, '#fff', rx=9, stroke=c, sw=1.3)
            s += T(x + 96 + 37, yy + 13, tag, 10, 700, c, 'middle')
            yy += 24
        if note:
            s += T(x, yy + 11, note, 10.5, 400, SUB, style='italic')
            yy += 18
    s += T(x, top + 210, 'Only draft & fix got one clause', 11.5, 400, SUB)
    s += T(x, top + 226, 'each; the test/critique text was left', 11.5, 400, SUB)
    s += T(x, top + 242, 'as-is. Intelligence went to design.', 11.5, 400, SUB)
    return s + '</svg>'


# ============================================================ 4. DIAGNOSIS -> REPAIR chain
def diagnosis():
    W, H = 1000, 340
    s = head(W, H)
    s += T(44, 34, 'DIAGNOSIS → REPAIR', 11, 700, ORANGE, ls='0.14em')
    s += T(44, 60, 'Each round’s mined failure correctly motivates the next structural fix', 18, 800, INK)
    rounds = [
        ('ROUND 0  ·  mines h₀', 'support 5', '“fixes the symptom, not the root cause;\nmisses other affected components”', '+ fix step  &  root-cause policy', '→ h₁'),
        ('ROUND 1  ·  mines h₁', 'support 6', '“patches pass without a reproduction\ntest; verification doesn’t enforce one”', '+ write_test step   (18 → 23)', '→ h₂'),
        ('ROUND 2  ·  mines h₂', 'support 2', '“the reproduction test’s coverage\nis incomplete”', 'refine test quality — all rejected', '→ h₃ = h₂'),
    ]
    top, rh = 92, 68
    for i, (r, sup, diag, repair, arrow) in enumerate(rounds):
        y = top + i * rh
        accept = 'rejected' not in repair
        c = GREEN if accept else RED
        s += T(44, y + 20, r, 12.5, 800, INK)
        s += R(44, y + 28, 150, 16, '#fff', rx=8, stroke=BLUE, sw=1.2)
        s += T(44 + 75, y + 40, 'mining ' + sup, 10, 600, BLUE, 'middle')
        # diagnosis text (2 lines)
        for j, ln in enumerate(diag.split('\n')):
            s += T(214, y + 16 + j * 16, ln, 11.5, 400, SUB, style='italic')
        # arrow
        s += L(600, y + 24, 636, y + 24, c, 1.8, marker='ag' if accept else 'ar')
        # repair
        s += R(646, y + 12, 300, 26, '#fff', rx=6, stroke=c, sw=1.5)
        s += T(660, y + 29, repair, 12, 700, c)
        s += T(956, y + 29, arrow, 12, 800, INK, 'end')
        if i < 2:
            s += L(44, y + rh - 6, 956, y + rh - 6, LINE, 1)
    s += T(44, H - 16, 'The model recognized, in order: I need to refine → I need an independent test to refine against → my test coverage is now the bottleneck.', 11.5, 400, GRAY)
    return s + '</svg>'


# ============================================================ 5. TASK ANATOMY — one SWE-bench task
def task():
    W, H = 1000, 340
    s = head(W, H)
    s += T(44, 34, 'ONE SWE-BENCH VERIFIED TASK', 11, 700, ORANGE, ls='0.14em')
    s += T(44, 60, 'A real GitHub bug, fixed by code, graded by the repository’s own tests', 18, 800, INK)
    colw, gap, x0, top, ch = 300, 24, 44, 92, 176
    # col 1 — the task
    x = x0
    s += R(x, top, colw, ch, '#fff', rx=10, stroke=BLUE, sw=1.6) + R(x, top, colw, 5, BLUE)
    s += T(x + 14, top + 30, 'THE TASK', 11.5, 800, BLUE)
    s += T(x + 14, top + 58, 'A real GitHub issue', 13, 700, INK)
    s += T(x + 14, top + 78, 'the actual bug report / feature', 11.5, 400, SUB)
    s += T(x + 14, top + 94, 'request, in the user’s words', 11.5, 400, SUB)
    s += T(x + 14, top + 126, 'The repository', 13, 700, INK)
    s += T(x + 14, top + 146, 'checked out at the commit', 11.5, 400, SUB)
    s += T(x + 14, top + 162, 'just before the fix', 11.5, 400, SUB)
    # col 2 — the harness
    x = x0 + colw + gap
    s += R(x, top, colw, ch, '#fff', rx=10, stroke=INK, sw=1.6) + R(x, top, colw, 5, INK)
    s += T(x + 14, top + 30, 'THE HARNESS  (fixed Haiku)', 11.5, 800, INK)
    cs, _ = chain(x + 14, top + 52, ['draft', 'write_test', 'fix'])
    s += cs
    s += T(x + 14, top + 108, 'edits the real source until', 11.5, 400, SUB)
    s += T(x + 14, top + 124, 'the fix is right, then emits', 11.5, 400, SUB)
    s += T(x + 14, top + 148, 'a patch', 13, 700, INK)
    s += T(x + 14 + 46, top + 148, '(git diff)', 11.5, 400, GRAY)
    # col 3 — the verdict
    x = x0 + 2 * (colw + gap)
    s += R(x, top, colw, ch, '#fff', rx=10, stroke=GREEN, sw=1.6) + R(x, top, colw, 5, GREEN)
    s += T(x + 14, top + 30, 'THE VERDICT  ·  hidden unit tests', 11.5, 800, GREEN)
    s += R(x + 14, top + 44, colw - 28, 34, '#f2f7f3', rx=6)
    s += T(x + 22, top + 63, 'FAIL→PASS   tests that must now pass', 11, 600, GREEN)
    s += R(x + 14, top + 84, colw - 28, 34, '#f2f7f3', rx=6)
    s += T(x + 22, top + 103, 'PASS→PASS   tests that must still pass', 11, 600, GREEN)
    s += T(x + 14, top + 146, 'RESOLVED', 13, 800, GREEN)
    s += T(x + 14 + 78, top + 146, 'only if all of both pass', 11.5, 400, SUB)
    # arrows
    for i in range(2):
        ax = x0 + (i + 1) * colw + i * gap + 3
        s += L(ax, top + ch / 2, ax + gap - 6, top + ch / 2, GRAY, 1.8, marker='a')
    s += T(44, H - 16, 'A deterministic, deployable verifier — not an LLM judge. Grading runs in the official SWE-bench container (rootless, via Apptainer).', 11.5, 400, GRAY)
    return s + '</svg>'


for name, fn in [('hero_evolution', hero), ('loop', loop), ('what_evolved', evolved), ('diagnosis', diagnosis), ('task_anatomy', task)]:
    p = os.path.join(OUT, name + '.svg')
    open(p, 'w').write(fn())
    print('wrote', os.path.relpath(p, os.path.join(os.path.dirname(__file__), '..')))
