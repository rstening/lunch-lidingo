# Lunch Lidingö

En sida med dagens lunch på några restauranger på Lidingö: https://lunch.richardstening.com

Sidan är gjord för en pensionär som kollar kvällen före eller samma morgon, oftast i mobilen. Den visar bara innevarande vecka, måndag till fredag.

## Ägaren och hur vi jobbar

- Ägaren är inte utvecklare. All utveckling görs av Claude. Svara på svenska och i vanligt språk.
- Fatta tekniska beslut själv. Fråga om design och innehåll, gärna med AskUserQuestion och en motivering per alternativ.
- Kör all text som syns för läsaren genom skillen `anthropic-skills:humanizer`.
- Ägaren vill inte synas när någon googlar hens namn. Se "Sökmotorer" nedan.

## Konton och git

- Använd bara GitHub-kontot `rstening`. Datorn kan vara inloggad på fler konton, och skalet kan ha en `GITHUB_TOKEN` för ett annat konto. Kör därför alla `gh`- och push-kommandon med `env -u GITHUB_TOKEN`, och kontrollera med `env -u GITHUB_TOKEN gh auth status` att `rstening` är aktivt.
- Commits skrivs som `rstening <rstening@users.noreply.github.com>` (repo-lokal `git config`). Använd aldrig ägarens riktiga namn eller e-post.
- Svenska för det ägaren läser: branchnamn, commit-meddelanden, PR-titlar och beskrivningar, README och designdokument. Engelska i koden: namn och kommentarer.
- Branchnamn bara med a–z, siffror och bindestreck, till exempel `fler-korningar`.
- Arbetsflöde: ny branch, visa ändringen på devservern, PR till `main`, slå ihop när ägaren säger till. Repot raderar sammanslagna brancher automatiskt.
- Bygg om `docs/index.html` med färsk data innan sammanslagning, så att ändringen syns direkt.
- När en regel eller ett beteende ändras: uppdatera README, designdokumentet och den här filen i samma branch.

## Så funkar det

1. `python -m scraper` läser `restaurants.yaml`, kör en läsare per restaurang (`scraper/readers/`) och skriver `data/menus.json`. En restaurang som inte går att läsa behåller sin senaste meny. Om alla misslyckas skrivs ingen fil.
2. `python -m scraper.build` gör om datan till `docs/index.html`.
3. GitHub Actions (`.github/workflows/daily.yml`) kör båda varje morgon kl 09, och på vardagar även kl 10:30 och 12:00 svensk tid, och committar om något ändrats. GitHub Pages visar `docs/`.
4. Sist körs `tools/halsokoll.py`, som öppnar ett ärende i repot när en restaurang har misslyckats i ungefär två dagar (40 timmar sedan senaste lyckade hämtning) och stänger det när den fungerar igen. Ärendet känns igen på en dold markering `<!-- lunch-bot:<id> -->`.

Designdokumentet `planning/superpowers/specs/2026-09-25-lunch-lidingo-design.md` beskriver allt i detalj och hålls uppdaterat.

## Kommandon

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m scraper
.venv/bin/python -m scraper.build
.venv/bin/python tools/dev_server.py
.venv/bin/python tools/make_icons.py
```

Devservern (`lunch-dev` i `.claude/launch.json`) bygger om sidan vid varje omladdning på http://localhost:8000/. Lägg till `?datum=2026-09-23` för att se en viss dag. Starta om servern om `tools/dev_server.py` själv ändras.

## Designregler

- Färger som variabler i `:root`: `--bg` #fafafa, `--text` #121212, `--text-2` #121212 59,5 %, `--disabled` #121212 18,5 %, `--line` #121212 6,8 %, `--accent` #24cc5c. Inga andra färger. Ett test kontrollerar det.
- Fonten Geist, självhostad i `docs/fonts/`. Inga externa resurser.
- All text 16 px, utom sidfoten och taggarna som är 14 px.
- En smal spalt, högst 640 px, på alla skärmar.
- Inga kort eller linjer. Restaurangerna grupperas med luft, och bitext har `--text-2`.
- Taggarna är runda kapslar och står till höger, direkt före priset. Rättens text börjar alltid vid vänsterkanten.
- Dagväljaren visar bara veckodagar, ovalda dagar i `--text-2` och vald dag i `--text` och fet stil. Sidhuvudet visar den valda dagens datum, och veckan på en egen rad under som inte flyttar när man byter dag. Dagens veckodag har en grön prick.
- Lunchtider skrivs alltid som `HH:MM-HH:MM` i `restaurants.yaml`, till exempel `10:00-14:00`. Ett test kontrollerar det.
- Alla notiser och andra meningar på sidan slutar med punkt. Undantag utan punkt, eftersom de är etiketter: lunchtiden och sidfotens två rader ("Uppdaterad …" och "© …"). Ett test kontrollerar notiserna.
- Visa aldrig en annan veckas rätter som den här veckans. Saknas veckans meny står det "Veckans meny är inte upplagd än.", och har restaurangen redan bytt till nästa vecka står det "Veckans meny saknas."
- Allergenmärkning, som "(Gluten, Laktos)", "(G/L)" eller "G,L,Ä" sist i en rätt, tas bort när sidan byggs (`without_allergens` i `scraper/build.py`). Datan i `data/menus.json` behåller allt.
- Infotexten under en restaurang börjar alltid med meningen om vad som ingår i lunchen (`included_text`). Därefter kommer korta extrarader i vår egen formulering, till exempel "Pensionärspris 120 kr." eller "145 kr 10:00-11:00, 160 kr 11:00-14:00." Extraraderna skapas av läsaren (`WeekMenu.extras`), inte genom att klippa i restaurangens text. Allt annat i infotexten visas inte.
- Ett pris kan vara ett intervall (`Dish.price_to`) och visas då som "145-160 kr". Saknar restaurangen pris på lunchen visas inget pris.
- Inga långa streck (– eller —) i sidans egen text. Ett test kontrollerar det.
- Mobile first: kontrollera varje designändring i 320 och 375 px bredd, utan sidledsscroll.
- Sidan ska fungera utan JavaScript. Det enda skriptet lägger till dragning i dagväljaren.

## Sökmotorer

Sidan har `<meta name="robots" content="noindex, nofollow, noarchive">`. Ta aldrig bort den, och lägg aldrig till en `robots.txt` som blockerar, eftersom Google då inte ser taggen. Ett test kontrollerar båda.

## Restauranger att känna till

- Lidingö Golfrestaurang är borttagen från sidan, eftersom deras sida blockerar GitHubs servrar. Läsaren finns kvar, och en utkommenterad post i `restaurants.yaml` visar hur den läggs tillbaka.
- Brasserie Jernet fyller i varje dags rätt samma dag. Varje rad hör därför till den vecka då den senast ändrades (`updated_at`, svensk tid).
- Rönneberga och Lidingö Saluhall visar bara en vecka åt gången och byter tidigt. `scraper/merge.py` sparar därför alla veckor den har sett.

## Adress

DNS för richardstening.com ligger hos GoDaddy: en CNAME-post `lunch` pekar på `rstening.github.io`, och en TXT-post verifierar domänen hos GitHub. `docs/CNAME` innehåller adressen.
