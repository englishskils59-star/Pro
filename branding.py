# branding.py
# WDI Visit Analytics Engine — هوية بصرية (لوجو ثابت + متحرك)
# انسخ هذا الملف بجانب app.py، ومجلد static/logo بجانبه.

from pathlib import Path
import streamlit as st

TEAL = "#2DD4BF"
BLUE = "#4C9AFF"
INK = "#0A0E11"
TEXT = "#E6EDF3"
FAINT = "#566573"

_LOGO_DIR = Path(__file__).parent / "static" / "logo"
FAVICON = str(_LOGO_DIR / "favicon.png")          # st.set_page_config(page_icon=FAVICON)
ICON_512 = str(_LOGO_DIR / "icon-512.png")
MARK_SVG_FILE = str(_LOGO_DIR / "logo-mark.svg")

# ── CSS الحركة: يُضاف مرة واحدة داخل بلوك الـ CSS العام في app.py ──
MOTION_CSS = """
@keyframes wdiDraw{0%{stroke-dashoffset:112}45%{stroke-dashoffset:0}78%{stroke-dashoffset:0}100%{stroke-dashoffset:-112}}
@keyframes wdiStopA{0%,13%{transform:scale(0)}19%{transform:scale(1.3)}24%,80%{transform:scale(1)}88%,100%{transform:scale(0)}}
@keyframes wdiStopB{0%,22%{transform:scale(0)}28%{transform:scale(1.3)}33%,82%{transform:scale(1)}90%,100%{transform:scale(0)}}
@keyframes wdiStopC{0%,31%{transform:scale(0)}37%{transform:scale(1.3)}42%,84%{transform:scale(1)}92%,100%{transform:scale(0)}}
@keyframes wdiEnd{0%,44%{transform:scale(0)}50%{transform:scale(1.25)}56%,86%{transform:scale(1)}94%,100%{transform:scale(0)}}
@keyframes wdiRing{0%,46%{transform:scale(.4);opacity:0}53%{opacity:.85}72%,100%{transform:scale(2.4);opacity:0}}
@keyframes wdiGlow{0%,100%{box-shadow:0 0 0 0 rgba(45,212,191,0)}50%{box-shadow:0 0 32px 0 rgba(45,212,191,.22)}}
.wdi-mark circle,.wdi-mark polyline{transform-box:fill-box;transform-origin:center;}
"""


def mark_svg(size: int = 38, stroke: float = 6.0, accent: str = BLUE, teal: str = TEAL) -> str:
    """العلامة الثابتة — تصلح لكل الأحجام (حتى 24px)."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" style="flex-shrink:0">'
        f'<polyline points="9,17 21,47 32,29 43,47 55,13" stroke="{teal}" stroke-width="{stroke}"'
        f' stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="55" cy="13" r="6" fill="{accent}"/></svg>'
    )


def mark_svg_animated(size: int = 38, dur: str = "4.2s", stops: bool = False,
                      stroke: float = 6.0, accent: str = BLUE, teal: str = TEAL,
                      bg: str = "#0F1417") -> str:
    """العلامة المتحركة: الخط يُرسم كمسار زيارات ثم يشتعل مؤشر التحليل.
    stops=True يضيف نقاط الزيارات (للأحجام 64px وأكبر فقط)."""
    a = f'animation:wdiDraw {dur} ease-in-out infinite'
    stop_dots = ""
    if stops:
        for (cx, cy, name) in ((21, 47, "wdiStopA"), (32, 29, "wdiStopB"), (43, 47, "wdiStopC")):
            stop_dots += (
                f'<circle cx="{cx}" cy="{cy}" r="3.4" fill="{bg}" stroke="{teal}" stroke-width="2.4"'
                f' style="animation:{name} {dur} ease-out infinite"/>'
            )
    return (
        f'<svg class="wdi-mark" width="{size}" height="{size}" viewBox="0 0 64 64" fill="none"'
        f' style="overflow:visible;flex-shrink:0">'
        f'<circle cx="55" cy="13" r="5.5" fill="none" stroke="{accent}" stroke-width="2"'
        f' style="animation:wdiRing {dur} ease-out infinite"/>'
        f'<polyline points="9,17 21,47 32,29 43,47 55,13" stroke="{teal}" stroke-width="{stroke}"'
        f' stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="112" style="{a}"/>'
        f'{stop_dots}'
        f'<circle cx="55" cy="13" r="6" fill="{accent}" style="animation:wdiEnd {dur} ease-out infinite"/>'
        f'</svg>'
    )


def sidebar_brand(animated: bool = True) -> None:
    """شعار الشريط الجانبي — بديل بلوك الـ W القديم."""
    logo = mark_svg_animated(34, stroke=7) if animated else mark_svg(34, stroke=7)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:11px;padding:14px 6px 16px">{logo}'
        f'<div><div style="font-size:15px;font-weight:700;letter-spacing:.3px;color:{TEXT}">WDI Analytics</div>'
        f'<div style="font-size:10px;color:{FAINT};margin-top:2px;white-space:nowrap">Visit Analytics Engine v2.0</div>'
        f'</div></div>', unsafe_allow_html=True)


def splash_card(subtitle: str = "ارفع ملف Excel لتصنيف الزيارات وتحليل أداء المندوبين تلقائياً — بدون إنترنت.") -> None:
    """شاشة البدء في «مركز الرفع» — بديل بلوك الترحيب القديم."""
    st.markdown(
        f'<div class="section-card" style="text-align:center;padding:40px">'
        f'<div style="width:78px;height:78px;margin:0 auto 16px;border-radius:20px;background:#131B22;'
        f'border:1px solid #223039;display:flex;align-items:center;justify-content:center;'
        f'animation:wdiGlow 4.2s ease-in-out infinite">{mark_svg_animated(46, stroke=6.5)}</div>'
        f'<div style="font-size:18px;font-weight:700;color:{TEXT}">WDI Visit Analytics Engine</div>'
        f'<div style="font-size:12.5px;color:#8B98A5;max-width:460px;margin:8px auto 0;line-height:1.9">'
        f'{subtitle}</div></div>', unsafe_allow_html=True)


def loading_logo(text: str = "جاري تحليل الزيارات…") -> None:
    """مؤشر تحميل بالعلامة المتحركة — بديل st.spinner عند الرغبة."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;justify-content:center;padding:22px">'
        f'{mark_svg_animated(40, stroke=6.5)}'
        f'<span style="font-size:13px;color:#8B98A5">{text}</span></div>', unsafe_allow_html=True)
