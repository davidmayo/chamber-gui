"""Styling and theme helpers for Dash app."""

from __future__ import annotations

APP_INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Chamber Monitoring</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --bg0: #e9eef3;
                --bg1: #d7e2ee;
                --panel: rgba(255, 255, 255, 0.94);
                --line: #b7c4d3;
                --text: #1f2933;
                --muted: #48607a;
                --accent: #d24d20;
            }
            * {
                box-sizing: border-box;
            }
            body {
                margin: 0;
                font-family: "Source Sans 3", "Segoe UI", sans-serif;
                color: var(--text);
                background:
                    radial-gradient(circle at 10% 10%, rgba(255,255,255,0.8), transparent 38%),
                    radial-gradient(circle at 90% 80%, rgba(201,220,240,0.8), transparent 42%),
                    linear-gradient(145deg, var(--bg0), var(--bg1));
            }
            .page {
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 14px;
            }
            .title {
                margin: 0;
                font-size: 2rem;
                letter-spacing: 0.01em;
            }
            .grid {
                display: grid;
                gap: 10px;
                grid-template-columns: repeat(5, minmax(0, 1fr));
            }
            .panel {
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 12px;
                box-shadow: 0 8px 18px rgba(39, 64, 90, 0.12);
                overflow: hidden;
                min-height: 240px;
            }
            .info {
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 8px 18px rgba(39, 64, 90, 0.12);
                animation: fade-in 0.4s ease;
            }
            .info h3 {
                margin: 0 0 10px 0;
                color: var(--accent);
            }
            .info ul {
                margin: 0;
                padding-left: 18px;
            }
            .info li {
                margin: 4px 0;
                color: var(--muted);
            }
            @keyframes fade-in {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @media (max-width: 1500px) {
                .grid {
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                }
            }
            @media (max-width: 1000px) {
                .grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
            @media (max-width: 650px) {
                .grid {
                    grid-template-columns: 1fr;
                }
                .title {
                    font-size: 1.4rem;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

