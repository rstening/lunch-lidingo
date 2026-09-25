# Lunch Lidingö

En sida med dagens lunch på restaurangerna på Lidingö. Varje morgon kl 09
hämtar GitHub Actions menyerna, och GitHub Pages visar sidan från mappen
`docs/`.

## Så funkar det

1. `python -m scraper` läser `restaurants.yaml`, hämtar varje restaurangs meny
   och skriver `data/menus.json`. Om en restaurang inte går att läsa ligger
   dess senaste meny kvar.
2. `python -m scraper.build` gör om JSON-filen till `docs/index.html`.
3. Actions committar och pushar filerna om de ändrats.

Notiserna på sidan betyder:

- "Kunde inte hämta menyn, se restaurangens sida": hämtningen har inte
  fungerat på mer än 7 dagar, eller aldrig.
- "Nästa veckas meny finns på restaurangens sida": restaurangen har lagt upp
  nästa vecka men vi har inte den här veckans meny. Sidan visar då ingenting
  hellre än fel veckas rätter.
- "Ingen aktuell meny, se restaurangens sida": den senaste menyn vi har är
  mer än en vecka gammal.
- "Visar vecka N, inte uppdaterad än": restaurangen har inte lagt upp den här
  veckans meny, så förra veckans visas.

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

Repot måste vara publikt för att GitHub Pages ska fungera på ett gratiskonto.
Privata repon kräver GitHub Pro, Team eller Enterprise för Pages.
