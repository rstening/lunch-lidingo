# Lunch Lidingö – designdokument

Datum: 2026-09-25
Status: godkänd i brainstorming, väntar på granskning av spec

## Syfte

En enda webbsida som visar dagens lunch hos alla kända lunchrestauranger på Lidingö, så att man slipper besöka sju olika hemsidor. Primär användare: en pensionär som kollar på förmiddagen för att bestämma var han ska äta idag. Sekundärt: planera veckan.

## Restauranger i första versionen

| Namn | Källa | Format |
|---|---|---|
| Firren | https://firren.org/bistro/ | HTML, rubriker Måndag–Fredag, en rätt per dag |
| Ronneberga | https://ronneberga.se/restaurang/lunchmeny/ | HTML, rubriker måndag–fredag, svenska och engelska rader blandade, veckonummer i text ("v. 40") |
| Lidingö Golfrestaurang | https://www.lidingogolfrestaurang.com/ | HTML, rubriker Måndag–Fredag, kategorier Dagens/Buffé/Vegetarisk/Veckans lätta, "Vecka NN" i text |
| Pocket (Nordrest) | https://www.nordrest.se/restaurang/pocket-lidingo/ | HTML, rubriker Måndag–Fredag, tre rätter per dag med allergener |
| Lidingö Saluhall | https://www.lidingosaluhall.com/ | HTML, sektion `#lunchmeny-section` på startsidan, "Lunchmeny vecka NN", MÅNDAG–FREDAG i versaler, "VECKANS VEGETARISKA" |
| Bibliothek | https://bibliothek.nu/menyer | Länkar till PDF `Lunch-vNN-YYYY.pdf`, textbaserad PDF, samma meny hela veckan (kött, fisk, veg, soppa), flera veckor kan finnas |
| Brasserie Jernet | https://brasseriejernet.se/ | JavaScript-app; menyn hämtas från deras öppna Supabase-API, tabell `lunch_menu`, fem rader (day_of_week 1–5) med kött/fisk/veg och pris. API-adress och publik nyckel läses ur sidans JS-bundle vid körning, inte hårdkodas, eftersom bundle-namnet ändras vid deras deploy |

Ankarlänkar i de ursprungliga adresserna (`#lunch`, `#meny`) ignoreras; hela sidan hämtas.

## Arkitektur

Statisk sida byggd av Python, publicerad via GitHub Pages från repot `rstening/lunch-lidingo` (privat konto, aldrig jobbkontot). Ett schemalagt GitHub Actions-jobb kör varje morgon kl 09:00 svensk tid (cron körs i UTC, så jobbet schemaläggs både 07:00 och 08:00 UTC; det ger 09 och 10 svensk tid på sommaren och 08 och 09 på vintern. Två körningar per dag är ofarligt: sidan innehåller alltid en "Uppdaterad …"-tidsstämpel, så filerna skiljer sig mellan körningarna även när ingen meny ändrats, och jobbet committar därför normalt två gånger per dag. Det är avsiktligt accepterat, inte ett fel).

Flöde per körning:

1. **Scrape.** `python -m scraper` läser `restaurants.yaml` och kör varje restaurangs läsare. Varje läsare returnerar samma datastruktur (se nedan).
2. **Spara.** Resultatet slås ihop med föregående `data/menus.json`. Veckor slås ihop per läsare nycklat på (år, vecka): ny data skriver över gammal för samma vecka, veckor äldre än förra veckan tas bort. Misslyckade läsare behåller föregående post och får `last_success` oförändrad samt `error` satt.
3. **Bygg.** `python -m scraper.build` läser `data/menus.json` och skriver `docs/index.html`.
4. **Publicera.** Actions committar `data/menus.json` och `docs/index.html` och pushar. GitHub Pages serverar `docs/`.

Om alla läsare misslyckas avbryts jobbet innan bygg och commit, så gårdagens sida ligger kvar.

### Mappstruktur

```
lunch-lidingo/
  restaurants.yaml              Lista: id, namn, adress, url, läsare
  scraper/
    __main__.py                 Kör alla läsare, slår ihop, skriver JSON
    build.py                    JSON -> docs/index.html
    model.py                    Datastruktur (Restaurant, WeekMenu, Dish)
    fetch.py                    Gemensam HTTP-hämtning med timeout och user-agent
    weeks.py                    Veckonummer, "idag", helg -> måndag
    readers/
      firren.py, ronneberga.py, golf.py, pocket.py, saluhallen.py, bibliothek.py, jernet.py
  data/menus.json
  docs/index.html
  docs/superpowers/specs/       Designdokument
  tests/
    fixtures/                   Sparade kopior av varje källa
    test_<läsare>.py            Ett test per läsare
    test_build.py, test_merge.py
  .github/workflows/daily.yml   Schema + commit
  .github/workflows/test.yml    Tester vid push
  requirements.txt
```

## Datastruktur

`data/menus.json`:

```json
{
  "generated_at": "2026-09-25T07:02:11Z",
  "restaurants": [
    {
      "id": "firren",
      "name": "Firren",
      "url": "https://firren.org/bistro/",
      "address": "…",
      "last_success": "2026-09-25T07:02:05Z",
      "error": null,
      "weeks": [
        {
          "year": 2026,
          "week": 40,
          "week_known": true,
          "days": {
            "1": [{"name": "Scampi Indiana med grönsaksris", "price": null, "tags": []}],
            "2": [...],
            "5": [...]
          },
          "notes": "I lunchen ingår salladsbuffé, kaffe …"
        }
      ]
    }
  ]
}
```

- `days` nycklas på ISO-veckodag 1–5 som sträng. Dag som saknas i källan utelämnas.
- `tags` är en lista av strängar ur mängden `veg`, `fisk`, `kött`, `soppa`, `buffé`, `lätt`. Tom lista om källan inte anger.
- `week_known` är false när källan inte anger vecka (Jernet). Då sätts `week` till innevarande vecka vid hämtning.
- `weeks` kan innehålla flera veckor (Bibliothek). Bygget visar innevarande vecka; om den saknas visas den senast tillgängliga med veckonotis.
- `error` är en kort sträng vid senaste misslyckande, annars null.

## Läsare

Gemensamma regler:

- Timeout 20 sekunder per hämtning, tydlig user-agent med länk till repot.
- En läsare som hittar noll rätter totalt kastar fel. Tom meny räknas som fel, aldrig som lyckat resultat.
- Läsare får bara `bytes`/`str` in (HTML, PDF, JSON) och ett datum; nätverk sköts av `fetch.py`. Det gör dem testbara mot fixtures.
- Veckonummer parsas där det finns: Ronneberga (`v. 40`), Golfrestaurangen (`Vecka 39`), Saluhallen (`vecka 40`), Bibliothek (filnamn `Lunch-v40-2026.pdf`). Firren har datum per dag (`2026-09-21`), veckan räknas från dem. Pocket och Jernet saknar veckoangivelse och antas vara innevarande vecka.

Särskilt per läsare:

- **Ronneberga:** engelska rader (efter `monday`, `Tuesday` osv.) hoppas över. Rätter separeras på radbrytningar inom dagens block.
- **Golfrestaurangen:** rader med prefix `Buffé:`, `Vegetarisk:`, `Veckans lätta:` får motsvarande tagg; första raden utan prefix är dagens rätt. Allergenmarkeringar `(L)(G)(Ä)` behålls i texten.
- **Pocket:** allergenraden (`Gluten • Laktos • Ägg`) läggs till rättens text på en egen rad. `Veckans fisk` ger tagg `fisk`.
- **Saluhallen:** bara texten mellan `#lunchmeny-section` och nästa sektion används. `VECKANS VEGETARISKA` läggs på alla fem dagar med tagg `veg`. Sallader och priser under det ignoreras i första versionen.
- **Bibliothek:** alla PDF-länkar som matchar `Lunch-v(\d+)-(\d{4})` hämtas. Texten delas i kött/fisk/veg/soppa, pris tas från `(\d+)kr`. Samma fyra rätter sätts på alla fem dagar. Rätter med rubriken "affärslunch", "alltid på" och nedåt ignoreras.
- **Jernet:** JS-bundle-adressen läses ur startsidans HTML, Supabase-URL och anon-nyckel ur bundlen med regex, sedan `GET /rest/v1/lunch_menu?select=*&order=day_of_week.asc`. Fält `meat_name`, `fish_name`, `vegetarian_name` med pris blir tre rätter per dag. Fungerar endast så länge deras nyckel är publik i bundlen, vilket är hur deras egen sida fungerar.

## Felhantering och veckokontroll

- Fel i en läsare loggas som varning med restaurang-id och orsak; övriga fortsätter.
- Post med `error` och `last_success` äldre än 7 dagar visas som "Kunde inte hämta menyn, se restaurangens sida" med länk. Nyare visas med notis "Senast hämtad 24 sep".
- Veckokontroll: visas den exakta innevarande veckan, ingen notis om vecka. Har restaurangen bara veckor senare än innevarande visas ingen meny utan notisen "Nästa veckas meny finns på restaurangens sida". Är den senast kända veckan exakt en vecka äldre än innevarande visas den med notisen "Visar vecka N, inte uppdaterad än". Är den mer än en vecka äldre visas ingen meny utan notisen "Ingen aktuell meny, se restaurangens sida". Detta förhindrar att en restaurang som redan publicerat nästa veckas meny (innan innevarande vecka är slut) visar nästa veckas rätter som dagens.
- Actions-jobbet failar (och GitHub mejlar) bara när alla läsare misslyckas eller bygget kraschar.

## Sidan

En sida, `docs/index.html`, i HTML och CSS utan externa resurser. Ett litet inbäddat skript lägger till dragning i dagväljaren; utan skriptet fungerar sidan fullt ut med tryck.

- Rubrik "Dagens lunch på Lidingö", datum och veckodag, rad "Uppdaterad 25 sep 09:02".
- Flikar Mån–Fre byggs av dolda radioknappar (en `<input type="radio">` per dag) och `<label>`-element; CSS `:checked ~` visar sektionen för vald dag, utan JavaScript. Med skriptet kan man dessutom dra glasbrickan med finger eller mus; den snäpper till närmaste dag vid släpp, och en snabb svepning byter en dag i svepets riktning. Radioknappen för dagens dag är förvald (`checked`) vid sidbygget. På lördag och söndag är måndag förvald.
- Per dag: en ruta per restaurang i fast ordning enligt `restaurants.yaml`. Rutan innehåller namn (länk till källan), rätter som lista med pris och tagg där det finns, samt eventuell notis.
- Restaurang utan rätter för dagen visas ändå, med "Ingen meny för den här dagen".
- All text i 16 px, hierarki med vikt och luft, hög kontrast, en smal spalt (max 640 px) på alla skärmar. Allt på svenska. Ingen vidare design i första versionen.

## Testning

- `tests/fixtures/` innehåller en sparad kopia per källa från 2026-09-25 (HTML, PDF, JSON).
- Ett test per läsare: kör läsaren på fixturen, kontrollerar antal dagar, veckonummer där det finns, och minst en känd rätt per läsare (t.ex. Firren måndag "Scampi Indiana med grönsaksris").
- Test av sammanslagning: veckor slås ihop per (år, vecka) där ny data skriver över gammal och veckor äldre än förra veckan tas bort; misslyckad läsare behåller föregående post; tom meny ger fel.
- Test av bygg: given JSON ger HTML som innehåller alla restaurangnamn och rätt dag markerad.
- `test.yml` kör `pytest` vid varje push. `daily.yml` kör hela kedjan mot riktiga källor.
- Lokalt kommando `python -m scraper && python -m scraper.build` för att se resultatet innan push.

## Manuella steg för Richard

1. Logga in `gh` med kontot `rstening` på den här datorn (Claude ger kommandot när det är dags).
2. I repot på GitHub: Settings → Pages → Deploy from branch → `main` / `/docs`.
3. I repot: Settings → Actions → General → Workflow permissions → "Read and write", så jobbet får committa.

## Utanför första versionen

Egen domän, filter på typ av mat, karta, öppettider, fler restauranger, snyggare design, mejlnotis vid enskilda restaurangfel.
