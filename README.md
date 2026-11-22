# THE WORLD TODAY — Sunday 22 November 2026

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/DavidQlla06/news-image-20261122-v3/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/DavidQlla06/news-image-20261122-v3/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

A one-page broadsheet front page summing up the world's news of **Sunday
22 November 2026**, drawn entirely in code with Pillow. Entered in the
make.fun competition [news-image-20261122](https://make.fun/bounty/news-image-20261122).

## What's on the page

- **Lead story** — Iran strikes US bases across the Gulf (Kuwait air base
  hit, four US bases in Bahrain attacked, three tankers hit in the Strait
  of Hormuz), with a large drawn dusk scene: burning tanker, missile arcs,
  air base with hangars and radar dome.
- **12 illustrated story cards** — Kryvyi Rih 'triple-tap' strike; Sparta II
  ablaze in the Gulf of Finland; COP31 close to a final deal; 'El Chapo
  Isidro' captured; M6.9 Peru quake; the AI stock rout (S&P −3.7%); Air
  Niugini emergency landing in Davao; Estonia closes Russia border roads;
  Verstappen inherits Las Vegas pole; RSF accused in West Kordofan; US
  loses measles elimination status; England thrash the All Blacks.
- **Region-grouped headline lists** — 20 more stories across Middle East,
  Europe, Asia-Pacific, Americas, Africa, Planet & Science, and Sport.
- **Ticker strip** — 8 further one-line headlines.

In total: **41 stories, 7 regions, 13 drawn illustrations** (the lead scene
plus one scene per card). Every headline was reported on 22 November 2026
(sourced live from Reuters, AP, CNN, AFP, PAHO and UKMTO reporting).

## How it works

- `stories.json` — the day's verified headlines, summaries and layout data.
- `generate.py` — draws the 1024×1024 front page with Pillow: masthead,
  lead scene, card grid with a scene-painter function per story motif,
  flowing region lists, ticker and footer. Deterministic: no randomness,
  no clock, no network.
- `main.py` — the grader entry point (Python 3.13, standard library
  only). It copies the committed `entry.png` to `$MAKEFUN_OUTPUT_DIR`
  (or `/output`).

## Run it

```sh
python3 generate.py          # redraw entry.png from stories.json
mkdir -p out
MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png
```

`entry.png` is 1024×1024 and under 1 MiB.

## License

MIT — see [LICENSE](LICENSE).
