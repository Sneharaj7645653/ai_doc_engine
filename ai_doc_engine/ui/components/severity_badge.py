import streamlit as st

_STYLES = {
    "BROKEN": ("🔴", "#f8d7da", "#721c24", "#f5c6cb"),
    "POTENTIALLY_OUTDATED": ("🟡", "#fff3cd", "#856404", "#ffeeba"),
    "REVIEW_RECOMMENDED": ("🔵", "#cce5ff", "#004085", "#b8daff"),
    "SAFE": ("🟢", "#d4edda", "#155724", "#c3e6cb"),
}
_DEFAULT = ("⚪", "#e9ecef", "#495057", "#dee2e6")


def render_severity_badge(severity: str) -> None:
    sev = severity.upper().strip()
    icon, bg, color, border = _STYLES.get(sev, _DEFAULT)
    st.markdown(
        f"""<span style="
            background:{bg};
            color:{color};
            border:1px solid {border};
            padding:4px 14px;
            border-radius:20px;
            font-weight:700;
            font-size:13px;
            letter-spacing:0.5px;
            display:inline-block;
            margin-bottom:8px;">
            {icon}&nbsp;{sev}
        </span>""",
        unsafe_allow_html=True,
    )
