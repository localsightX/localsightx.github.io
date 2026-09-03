# LocalSight — GitHub Pages

The public website for **LocalSight**, a local-first, privacy-by-design video
intelligence platform. Served via GitHub Pages at
`https://localsightx.github.io/`.

## Sections

- **Hero** — Multi-class ONNX detection, MQTT/push alerts, 66 tests, 9-job CI/CD
- **Capabilities** — 10 feature cards: multi-class detection, ANPR, face ID (opt-in),
  behavior rules, LL-HLS live view, event clip export, analytics/BI, VLM search,
  multi-channel alerts, hardened by default
- **How it works** — 4-step pipeline: Ingest → Analyze → Record → Act & review
- **CI/CD & supply chain** — 9-job GitHub Actions pipeline (lint, tests, integration,
  dep audit, CodeQL, Semgrep, Trivy, Docker build, SBOM) with free CVE sources
- **Privacy & compliance** — No cloud by default, opt-in recognition, envelope encryption,
  SSRF guard, alert cooldown, immutable audit log, bounded retention, CI vulnerability gate
- **Quick start** — Python and Docker Compose tabs
- **Cameras** — TP-Link VIGI/Tapo, ONVIF, multi-vendor presets (Axis, Hanwha, Hikvision,
  Dahua, Reolink, Bosch, GB/T 28181)

## Structure

```
index.html              # Landing page
assets/css/style.css    # Styles (no framework, hand-built)
assets/js/main.js       # Nav, tabs, copy buttons, scroll reveal
assets/img/favicon.svg  # Brand mark
assets/img/og.svg       # Social preview image
```

## Local preview

Open `index.html` directly, or serve the folder:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Notes

- This is a static site (`.nojekyll`) — no build step or Jekyll theme required.
- Asset paths are relative so the site works both locally and as a GitHub
  project page under `/localsight.github.io/`.
- Product content mirrors the main repo docs at
  <https://github.com/jatinkray/localsight>.
