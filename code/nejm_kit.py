"""NEJM-style figure kit. ggsci 'nejm' palette, Helvetica, 600 DPI PDF+PNG, uppercase panel labels,
minimal chartjunk, no in-figure titles, no gridlines competing with data."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ggsci NEJM palette (Lancet-grade colorblind-safe, NEJM house colors)
NEJM_BLUE   = "#0072B5"
NEJM_RED    = "#BC3C29"
NEJM_ORANGE = "#E18727"
NEJM_GREEN  = "#20854E"
NEJM_LTBLUE = "#6F99AD"
NEJM_PURPLE = "#7876B1"
NEJM_PINK   = "#EE4C97"
GREY        = "#B7C0C9"
LABEL       = "#222222"
MUTED       = "#6B7280"

def set_style():
    plt.rcParams.update({
        "font.family":"sans-serif",
        "font.sans-serif":["Helvetica","Helvetica Neue","Arial","DejaVu Sans"],
        "font.size":10, "axes.titlesize":10, "axes.labelsize":10,
        "xtick.labelsize":9, "ytick.labelsize":9, "legend.fontsize":9,
        "axes.spines.top":False, "axes.spines.right":False,
        "axes.edgecolor":"#9CA3AF", "axes.linewidth":0.8,
        "xtick.color":"#4B5563", "ytick.color":"#4B5563",
        "pdf.fonttype":42, "ps.fonttype":42, "savefig.dpi":600,
    })

def panel(ax, letter):
    ax.text(-0.16, 1.05, letter, transform=ax.transAxes, fontsize=13,
            fontweight="bold", color=LABEL, va="bottom", ha="left")

def faint_grid(ax, axis="x"):
    ax.grid(axis=axis, color="#EEF1F4", lw=0.6, zorder=0)
    ax.set_axisbelow(True)

def save(fig, path_no_ext):
    for ext in ("pdf","png"):
        fig.savefig(f"{path_no_ext}.{ext}", dpi=600, bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)
