# Franklinton Family Events

A free, mobile-first website for finding family-friendly events near Franklinton, North Carolina.

The initial experience will default to:

- ZIP code 27525
- A 20-mile radius
- Events happening today
- Activities suitable for a 2.5-year-old

The first implementation is a dependency-free static website backed by a small event dataset and a Python standard-library collector. See [the requirements](docs/requirements.md) and [system architecture](docs/architecture.md) for the decisions behind it.

## Current capabilities

- Today, tomorrow, weekend, and coming-up views
- Age filtering in half-year increments
- A 5-to-50-mile travel slider centered on 27525
- Cost, setting, and activity filters
- Saved events stored privately in the browser
- Official source links and data freshness
- Daily refresh from supported official iCalendar feeds

## Local preview

Serve the repository with any static web server, then open its root URL. For example, with Python installed:

```sh
python -m http.server 8000
```

GitHub Pages publishes the production site from `main` after verification passes.

## Working agreement

Changes are developed on focused branches, checked automatically, independently reviewed, and merged only after the acceptance criteria are satisfied. The human architect makes the final merge decision.
