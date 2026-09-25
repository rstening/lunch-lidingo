# Lunch Lidingö

En sida som samlar dagens lunch från restauranger på Lidingö. Menyerna hämtas
automatiskt varje morgon kl 09 av GitHub Actions och publiceras som en statisk
sida via GitHub Pages från mappen `docs/`.

## Så funkar det

1. `python -m scraper` läser `restaurants.yaml`, hämtar varje restaurangs meny
   och skriver `data/menus.json`. En restaurang som inte går att läsa behåller
   sin senaste meny.
2. `python -m scraper.build` gör om JSON-filen till `docs/index.html`.
3. Actions committar och pushar filerna om de ändrats.

## Köra lokalt

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m scraper
.venv/bin/python -m scraper.build
open docs/index.html
```

## Lägga till en restaurang

Lägg till en rad i `restaurants.yaml` och en läsare i `scraper/readers/`
med funktionen `read(get, url, today)`. Spara en kopia av källan i
`tests/fixtures/` och skriv ett test.

## Engångsinställningar i GitHub

1. Settings → Pages → Build and deployment → Source: "Deploy from a branch",
   Branch: `main`, mapp `/docs`.
2. Settings → Actions → General → Workflow permissions: "Read and write permissions".
3. Actions → "Hämta menyer" → "Run workflow" för att köra första gången.
