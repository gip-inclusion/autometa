#!/usr/bin/env python3
"""
Tiny web service to convert raw Matomo API calls into clickable URLs.
Run: python api-linker.py
Open: http://localhost:8765
"""

import http.server
import os
from pathlib import Path

# Load token from .env
env = {}
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

MATOMO_URL = env.get("MATOMO_URL", "matomo.inclusion.beta.gouv.fr")
MATOMO_TOKEN = env.get("MATOMO_API_KEY", "")

HTML = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Matomo API Linker</title>
  <style>
    body {{ font-family: system-ui; max-width: 900px; margin: 2em auto; padding: 0 1em; }}
    textarea {{ width: 100%; height: 60px; font-family: monospace; font-size: 14px; }}
    button {{ padding: 0.5em 1em; font-size: 14px; cursor: pointer; margin-right: 0.5em; }}
    button.primary {{ background: #0066cc; color: white; border: none; border-radius: 3px; }}
    #results {{ margin-top: 1.5em; }}
    dl {{ background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px; padding: 1em; margin: 0.5em 0; }}
    dt {{ font-weight: bold; color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 0.3em; }}
    dd {{ margin: 0 0 0.8em 0; font-family: monospace; font-size: 13px; word-break: break-all; }}
    dd:last-child {{ margin-bottom: 0; }}
    a {{ color: #0066cc; }}
  </style>
</head>
<body>
  <h1>Matomo API Linker</h1>
  <p>Paste a raw API call, get a clickable URL with token.</p>

  <textarea id="input" placeholder="VisitsSummary.get?idSite=117&period=month&date=2025-12-01&segment=pageUrl=@/gps/"></textarea>
  <br><br>
  <button class="primary" onclick="openUrl()">Open</button>
  <button onclick="convert()">Copy URL</button>

  <div id="results"></div>

  <script>
    const BASE = "https://{MATOMO_URL}/";
    const TOKEN = "{MATOMO_TOKEN}";

    function buildUrl(input) {{
      let method, params;
      if (input.includes('?')) {{
        [method, params] = input.split('?', 2);
      }} else {{
        method = input;
        params = '';
      }}
      return BASE + "?module=API&method=" + encodeURIComponent(method)
        + "&format=JSON&token_auth=" + TOKEN
        + (params ? "&" + params : "");
    }}

    function addResult(apiCall, url) {{
      const dl = document.createElement('dl');
      dl.innerHTML = `
        <dt>API Call</dt>
        <dd>${{apiCall}}</dd>
        <dt>URL</dt>
        <dd><a href="${{url}}" target="_blank">${{url}}</a></dd>
      `;
      const results = document.getElementById('results');
      results.insertBefore(dl, results.firstChild);
    }}

    function convert() {{
      const input = document.getElementById('input').value.trim();
      if (!input) return;
      const url = buildUrl(input);
      addResult(input, url);
      navigator.clipboard.writeText(url);
    }}

    function openUrl() {{
      const input = document.getElementById('input').value.trim();
      if (!input) return;
      const url = buildUrl(input);
      addResult(input, url);
      window.open(url, '_blank');
    }}

    document.getElementById('input').addEventListener('keydown', (e) => {{
      if (e.key === 'Enter' && !e.shiftKey) {{
        e.preventDefault();
        openUrl();
      }}
    }});
  </script>
</body>
</html>
"""

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def log_message(self, format, *args):
        pass  # Quiet

if __name__ == "__main__":
    port = 8765
    print(f"Starting on http://localhost:{port}")
    http.server.HTTPServer(("", port), Handler).serve_forever()
