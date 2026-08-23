"""Generate the architecture diagram image (assignment section 06 requirement)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

W, H = 16.0, 9.0
fig, ax = plt.subplots(figsize=(W, H), dpi=100)
ax.set_xlim(0, 100)
ax.set_ylim(0, 56)
ax.axis("off")

INK = "#1a1a2e"
BLUE = "#2563eb"
GREEN = "#059669"
ORANGE = "#d97706"
PURPLE = "#7c3aed"
RED = "#dc2626"
GRAY = "#6b7280"


def box(x, y, w, h, title, lines, color, fs_t=13, fs_b=10.5):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.4,rounding_size=0.8",
        linewidth=2.2, edgecolor=color, facecolor="white",
    ))
    ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="center",
            fontsize=fs_t, fontweight="bold", color=color)
    body = "\n".join(lines)
    ax.text(x + w / 2, y + (h - 4.4) / 2, body, ha="center", va="center",
            fontsize=fs_b, color=INK, linespacing=1.45)


def arrow(x1, y1, x2, y2, color, label="", lx=None, ly=None, style="-|>", lw=2.4):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style,
        mutation_scale=22, linewidth=lw, color=color,
        connectionstyle="arc3,rad=0",
    ))
    if label:
        ax.text(lx if lx is not None else (x1 + x2) / 2,
                ly if ly is not None else (y1 + y2) / 2 + 1.1,
                label, ha="center", va="bottom", fontsize=9.5,
                color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none"))


ax.text(50, 53.5, "AI Voice Sales Agent  —  Architecture",
        ha="center", va="center", fontsize=19, fontweight="bold", color=INK)
ax.text(50, 50.8, "outbound call → live decision engine → mid-call WhatsApp → callback booking → smart follow-up",
        ha="center", va="center", fontsize=11, color=GRAY)

# ── Row 1: telephony ────────────────────────────────────────────────
box(2, 36, 20, 11, "Customer Phone",
    ["8688664337", "answers & speaks", "Telugu / Hindi / English"], "#0f172a")
box(28, 36, 24, 11, "Retell AI  (voice layer)",
    ['agent "Priya" · GPT-4o-mini', "STT → LLM → TTS loop", "handles interruptions"], BLUE)

arrow(22.5, 41.5, 27.5, 41.5, BLUE, "outbound dial\nPOST /calls/outbound", ly=42.6)
arrow(40, 35.4, 14, 35.4, "#0f172a", "", style="<|-|>")
ax.text(26, 33.6, "live two-way conversation", ha="center", fontsize=9.5,
        color="#0f172a", fontstyle="italic")

# ── Row 2: backend core ─────────────────────────────────────────────
box(28, 18, 24, 12, "FastAPI backend  :8000",
    ["/webhooks/voice  (per turn)", "latency middleware <150 ms", "idempotent action engine"],
    PURPLE)

arrow(40, 35.4, 40, 30.6, BLUE, "webhook each turn\n(cumulative transcript)",
      lx=52, ly=31.8)

# ── Decision engine ─────────────────────────────────────────────────
box(58, 18, 24, 12, "Decision Engine",
    ["decision.py  classify HOT/WARM/COLD", "timeparse.py  'kal shaam 5 baje'",
     "→ next action + barrier capture"], ORANGE)

arrow(52.6, 24, 57.4, 24, ORANGE, "extract +\nclassify", lx=55, ly=25)

# ── Actions row ─────────────────────────────────────────────────────
box(88, 39, 10.5, 12.5, "Meta\nWhatsApp", ["mid-call", "message", "+ follow-up", "+ resume"], GREEN, fs_t=11, fs_b=9.5)
box(88, 22, 10.5, 12.5, "Scheduler", ["callback", "booked from", "spoken time"], RED, fs_t=11, fs_b=9.5)
box(88, 5, 10.5, 12.5, "Database", ["leads · calls", "messages · reqs", "decisions"], GRAY, fs_t=11, fs_b=9.5)

arrow(82.6, 26, 87.4, 26, RED, "", )
arrow(70, 30.6, 93.2, 38.4, GREEN, "")
ax.text(90, 34.8, "HOT intent →\nfire immediately", fontsize=9.5, color=GREEN,
        fontweight="bold", ha="right")

# follow-up path
arrow(93.2, 17.4, 93.2, 21.4, GRAY)
arrow(82.6, 21, 87.4, 10, GRAY, "")

# DB writes from backend
arrow(46, 17.4, 86, 8.5, GRAY, "persist every turn", lx=64, ly=9.5)

# ── Follow-up strip ─────────────────────────────────────────────────
box(2, 3, 78, 9, "Post-call follow-up  (WhatsApp within seconds of call end)",
    ["quotes the customer's own words  ·  budget/timeline/features recap  ·  resume attached",
     "architecture image attached (this file)  ·  Nikhil's mobile number for direct callback"],
    INK, fs_t=12, fs_b=10)

arrow(40, 17.4, 40, 12.6, INK, "call ends → build from real transcript", lx=63, ly=14)

plt.savefig(r"D:\voice-sales-agent\assets\architecture.png",
            bbox_inches="tight", facecolor="white")
print("saved architecture.png")
