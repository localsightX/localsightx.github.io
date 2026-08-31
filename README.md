# LocalSight — GitHub Pages

The public website for **LocalSight**, a local-first, privacy-by-design video
intelligence platform. Served via GitHub Pages at
`https://jatinkray.github.io/localsight.github.io/`.

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
