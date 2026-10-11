"""Shared figure/table helpers. Palette = validated reference categorical palette (light mode),
fixed slot order; text uses neutral inks, never series colours."""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
COL_W = 3.5     # IEEE single column (in)
DBL_W = 7.16    # IEEE double column (in)


def set_style():
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7,
        "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
        "lines.linewidth": 1.2, "lines.markersize": 3,
        "legend.frameon": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


set_style()


def savefig(fig, base: str):
    fig.savefig(base + ".pdf")
    fig.savefig(base + ".png", dpi=300)
    plt.close(fig)


def stat_text(ax, lines, loc="upper left"):
    x, ha = (0.03, "left") if "left" in loc else (0.97, "right")
    y, va = (0.97, "top") if "upper" in loc else (0.03, "bottom")
    ax.text(x, y, "\n".join(lines), transform=ax.transAxes, ha=ha, va=va, color=INK2, fontsize=7,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.6), zorder=5)   # points stay visible


def latex_table(df, path: str, caption: str, label: str, col_format: str | None = None):
    cols = list(df.columns)
    col_format = col_format or ("l" * 1 + "r" * (len(cols) - 1))
    def esc(s):   # LaTeX-safe in OT1 text mode ('<', '>' would print as inverted punctuation)
        s = "--" if str(s) == "nan" else str(s)
        for a, b in [("_", r"\_"), ("%", r"\%"), ("&", r"\&"), ("#", r"\#"), ("^", r"\textasciicircum{}"),
                     ("<", r"\textless{}"), (">", r"\textgreater{}"), ("~", r"\textasciitilde{}")]:
            s = s.replace(a, b)
        return s
    # near placement; shrink only tables wider than the column (needs \usepackage{adjustbox}); never enlarge
    size = r"\scriptsize" if len(df) > 30 else r"\footnotesize"     # long tables must fit on one page
    lines = [r"\begin{table}[!htbp]", r"\centering", size, rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             r"\begin{adjustbox}{max width=\columnwidth}", rf"\begin{{tabular}}{{{col_format}}}", r"\toprule",
             " & ".join(rf"\textbf{{{esc(c)}}}" for c in cols) + r" \\", r"\midrule"]
    for _, r in df.iterrows():
        lines.append(" & ".join(esc(v) for v in r.values) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _agree(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    d = y - x
    return ok.sum(), np.corrcoef(x, y)[0, 1], d.mean(), np.abs(d).mean()


def iri_validation_figure(scatter: dict, base: str):
    panels = [("canonical_dx0.10", "(a) This implementation vs. P79", PALETTE[0], "P79-reported IRI, 100 m (m/km)", "upper left"),
              ("legacy_mesh_corrected", "(b) Legacy label pipeline vs. P79", PALETTE[1], "P79-reported IRI, 100 m (m/km)", "upper left"),
              ("ARAN_vs_P79", "(c) ARAN9000 vs. P79 (other device)", PALETTE[2], "P79 IRI from profile, 100 m (m/km)", "lower right")]
    fig, axes = plt.subplots(1, 3, figsize=(DBL_W, 2.35))
    allv = np.concatenate([np.concatenate(v) for v in scatter.values()])
    hi = np.nanpercentile(allv, 99.5) * 1.05
    for ax, (key, title, col, xlab, loc) in zip(axes, panels):
        if key not in scatter:
            ax.set_visible(False); continue
        A = np.concatenate(scatter[key])
        ax.plot([0, hi], [0, hi], color=INK2, lw=0.7, ls="--", zorder=1)
        ax.scatter(A[:, 0], A[:, 1], s=4, color=col, alpha=0.55, linewidths=0, zorder=2)
        n, r, b, m = _agree(A[:, 0], A[:, 1])
        lines = [f"n = {n} segments", f"r = {r:.3f}", f"bias = {b:+.2f} m/km", f"MAE = {m:.2f} m/km"]
        off = int(np.sum((A[:, 0] > hi) | (A[:, 1] > hi)))
        if off:      # never hide points silently: they are in the statistics but outside the axes
            lines.append(f"{off} points > {hi:.0f} m/km off-scale")
        stat_text(ax, lines, loc=loc)
        ax.set_xlim(0, hi); ax.set_ylim(0, hi); ax.set_aspect("equal")
        ax.set_xlabel(xlab)
        ax.set_title(title, loc="left", color=INK)
    axes[0].set_ylabel("Recomputed / other IRI (m/km)")
    fig.tight_layout()
    savefig(fig, base)


def md_table(df) -> str:
    """Markdown table without the optional 'tabulate' dependency."""
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(out) + "\n"
