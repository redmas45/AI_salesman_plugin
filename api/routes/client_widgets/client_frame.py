"""HTML rendering helpers for the external widget frame route."""

from __future__ import annotations

EMPTY_WIDGET_FRAME_HTML = "<!doctype html><html><body></body></html>"


def render_widget_frame_html(script_path: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Hub Widget</title>
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: transparent;
      }}
      body {{
        position: relative;
      }}
    </style>
  </head>
  <body>
    <script src="{script_path}"></script>
  </body>
</html>"""
