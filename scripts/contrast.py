"""WCAG contrast of the text tokens on every surface they are used on (reads frontend/src/styles/tokens.css).

    python3 scripts/contrast.py
Rule (docs/DESIGN.md): all text >= 4.5:1 (large text 3:1). Semi-transparent colours are blended over the surface first.
"""
import pathlib
import re

CSS = pathlib.Path(__file__).resolve().parent.parent / "frontend/src/styles/tokens.css"


def parse() -> dict[str, tuple[float, float, float, float]]:
    out = {}
    for name, val in re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6}|rgba?\([^)]*\))", CSS.read_text()):
        if val.startswith("#"):
            out[name] = (*(int(val[i : i + 2], 16) for i in (1, 3, 5)), 1.0)
        else:
            n = [float(x) for x in re.findall(r"[\d.]+", val)]
            out[name] = (n[0], n[1], n[2], n[3] if len(n) > 3 else 1.0)
    return out


def blend(fg, bg):
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main() -> int:
    t = parse()
    solid = lambda k: t[k][:3]
    # Surfaces: workspace solids, and the showcase canvas (glass laid over base / bloom / highlight).
    surfaces = {
        "bg-ws (page)": solid("bg-ws"), "surface-panel": solid("surface-panel"), "surface-1 (card)": solid("surface-1"), "surface-2 (raised)": solid("surface-2"),
        "glass on bg-base": blend(t["glass"], solid("bg-base")),
        "glass-strong on bg-base": blend(t["glass-strong"], solid("bg-base")),
        "glass on bg-bloom": blend(t["glass"], solid("bg-bloom")),
        "glass-strong on bg-highlight (worst case)": blend(t["glass-strong"], solid("bg-highlight")),
        "bg-bloom": solid("bg-bloom"), "bg-base": solid("bg-base"),
    }
    fails = 0
    print(f"{'text':<9}{'surface':<46}{'ratio':>6}  verdict")
    for tn in ("text-1", "text-2", "text-3"):
        for sn, sc in surfaces.items():
            fg = blend(t[tn], sc)
            r = ratio(fg, sc)
            ok = r >= 4.5
            fails += not ok
            print(f"{tn:<9}{sn:<46}{r:>6.2f}  {'pass' if ok else 'FAIL'}")
    for name in ("ok", "warn", "bad", "info"):
        for sn in ("bg-ws (page)", "surface-panel", "surface-1 (card)", "surface-2 (raised)"):
            r = ratio(solid(name), surfaces[sn])
            fails += r < 4.5
            print(f"{name:<9}{sn:<46}{r:>6.2f}  {'pass' if r >= 4.5 else 'FAIL'}")
    for name in ("signal", "stage-sourced", "stage-screened", "stage-submitted", "stage-shortlisted", "stage-interview", "stage-offered", "stage-joined", "stage-rejected"):
        for sn in ("bg-ws (page)", "surface-1 (card)", "surface-2 (raised)"):
            r = ratio(solid(name), surfaces[sn])
            need = 3.0 if name.startswith("stage-") else 4.5  # stage hues are a 6px dot (non-text, 3:1); the label carries the meaning
            fails += r < need
            print(f"{name:<18}{sn:<28}{r:>6.2f}  {'pass' if r >= need else 'FAIL'}")
    r = ratio(solid("on-accent"), solid("accent"))
    print(f"{'on-accent':<9}{'accent (primary button)':<46}{r:>6.2f}  {'pass' if r >= 4.5 else 'FAIL'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
