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
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            .panel {
                width: 344px;
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 12px;
                box-shadow: 0 8px 18px rgba(39, 64, 90, 0.12);
                overflow: hidden;
                min-height: 240px;
            }
            .info {
                width: 344px;
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
            /* ===== Hamburger / Dropdown ===== */
            .hamburger-container {
                position: fixed;
                top: 16px;
                right: 16px;
                z-index: 1000;
            }
            .hamburger-btn {
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 1.4rem;
                line-height: 1;
                cursor: pointer;
                box-shadow: 0 2px 8px rgba(39, 64, 90, 0.15);
                transition: background 0.15s;
            }
            .hamburger-btn:hover {
                background: var(--bg1);
            }
            .hamburger-dropdown {
                position: absolute;
                top: calc(100% + 4px);
                right: 0;
                background: var(--panel);
                border: 1px solid var(--line);
                border-radius: 8px;
                box-shadow: 0 4px 16px rgba(39, 64, 90, 0.18);
                min-width: 160px;
                overflow: hidden;
            }
            .hamburger-dropdown.hidden {
                display: none;
            }
            .dropdown-item {
                display: block;
                width: 100%;
                padding: 10px 16px;
                background: none;
                border: none;
                text-align: left;
                cursor: pointer;
                font-size: 0.95rem;
                color: var(--text);
            }
            .dropdown-item:hover {
                background: var(--bg1);
            }
            /* ===== Modal ===== */
            .modal-overlay {
                position: fixed;
                inset: 0;
                background: rgba(31, 41, 51, 0.45);
                z-index: 2000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .modal-overlay.hidden {
                display: none;
            }
            .modal-dialog {
                background: var(--panel);
                border-radius: 14px;
                box-shadow: 0 12px 40px rgba(39, 64, 90, 0.28);
                width: 420px;
                max-height: 80vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            .modal-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 20px;
                border-bottom: 1px solid var(--line);
            }
            .modal-header h3 {
                margin: 0;
                color: var(--accent);
            }
            .modal-close-btn {
                background: var(--accent);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                cursor: pointer;
                font-size: 0.9rem;
            }
            .modal-body {
                display: flex;
                flex: 1;
                min-height: 0;
            }
            .modal-items {
                flex: 1;
                overflow-y: auto;
                padding: 8px 0;
            }
            /* ===== Modal group toggles (left sidebar) ===== */
            .modal-groups {
                display: flex;
                flex-direction: column;
                gap: 2px;
                padding: 10px 8px;
                border-right: 1px solid var(--line);
                flex-shrink: 0;
            }
            .group-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 10px;
                border-radius: 6px;
                cursor: pointer;
                user-select: none;
            }
            .group-item:hover {
                background: var(--bg0);
            }
            .group-label {
                font-size: 0.9rem;
                color: var(--muted);
            }
            /* ===== Modal list items ===== */
            .modal-item {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 8px 20px;
                user-select: none;
            }
            .modal-item:hover {
                background: var(--bg0);
            }
            .modal-item.dragging {
                opacity: 0.4;
            }
            .modal-item.drag-over {
                border-top: 2px solid var(--accent);
            }
            .drag-handle {
                cursor: grab;
                color: var(--muted);
                font-size: 1.2rem;
                padding: 0 4px;
            }
            .drag-handle:active {
                cursor: grabbing;
            }
            .modal-checkbox {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 16px;
                height: 16px;
                border: 2px solid var(--line);
                border-radius: 3px;
                cursor: pointer;
                background: white;
                color: transparent;
                font-size: 11px;
                font-weight: bold;
                transition: background 0.15s, border-color 0.15s, color 0.15s;
                flex-shrink: 0;
            }
            .modal-checkbox.modal-checkbox--on {
                background: var(--accent);
                border-color: var(--accent);
                color: white;
            }
            .modal-checkbox.modal-checkbox--mixed {
                background: var(--bg1);
                border-color: var(--muted);
                color: var(--muted);
            }
            .panel-label {
                flex: 1;
                font-size: 0.95rem;
            }
            @media (max-width: 650px) {
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

