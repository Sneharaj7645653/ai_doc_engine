import streamlit as st

_LINE_STYLES = {
    "+": ("background:#d4edda", "color:#155724"),
    "-": ("background:#f8d7da", "color:#721c24"),
    "@": ("background:#cce5ff", "color:#004085"),
}
_DEFAULT_STYLE = ("background:#f8f9fa", "color:#333333")


def _style_line(line: str) -> str:
    ch = line[0] if line else " "
    if ch in _LINE_STYLES:
        bg, fg = _LINE_STYLES[ch]
    else:
        bg, fg = _DEFAULT_STYLE
    escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<div style="{bg};{fg};font-family:monospace;font-size:12px;'
        f'padding:1px 8px;white-space:pre;border-radius:2px;">{escaped}</div>'
    )


def render_diff(diff: str) -> None:
    if not diff.strip():
        st.info("No changes detected between old and new documentation.")
        return

    lines = diff.splitlines()
    html = "\n".join(_style_line(line) for line in lines)
    st.markdown(
        f'<div style="border:1px solid #dee2e6;border-radius:6px;overflow:auto;'
        f'max-height:400px;padding:4px;">{html}</div>',
        unsafe_allow_html=True,
    )
