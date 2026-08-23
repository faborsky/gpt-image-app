# Instalace skillu `/gptimage` do Claude Code

Tahle složka obsahuje **skill pro Claude Code**, který obaluje CLI aplikaci v tomhle repu a přidává know-how ke generování obrázků přes OpenAI — ceny podle kvality, rozdíly mezi modely, oficiální pravidla promptování a co modely umí a neumí. Po instalaci ho v Claude Code vyvoláš jako `/gptimage`.

> Skill bez aplikace nefunguje — nejdřív zprovozni samotnou appku podle hlavního [`README.md`](../README.md) (`./setup.sh` + klíč v `.env`).

## Předpoklady

1. **Naklonovaný tenhle repozitář** a funkční appka (`./setup.sh` proběhl, `.env` má klíč).
2. Nainstalovaný **Claude Code**.

### Kde vzít API klíč

1. Otevři **[platform.openai.com/api-keys](https://platform.openai.com/api-keys)** a vygeneruj klíč.
2. Klíč vlož do `.env` v repu appky jako `OPENAI_API_KEY` (šablona je v `.env.example`).
3. Na účtu musíš mít **kredit** — bez něj volání spadne.

> Klíč je heslo k tvému účtu přes API — patří jen do `.env` (je v `.gitignore`), nikdy do kódu ani do gitu.

## Krok za krokem

Předpokládejme, že sis repo naklonoval do `~/dev/gpt-image-app` (uprav cesty podle sebe).

### 1) Zkopíruj skill do své Claude Code složky se skilly

```bash
mkdir -p ~/.claude/skills
cp -R ~/dev/gpt-image-app/skill/gptimage ~/.claude/skills/gptimage
```

### 2) Nastav skillu cestu k appce

Skill volá aplikaci přes placeholder `<GPT_IMAGE_APP_DIR>`. Nahraď ho **absolutní cestou** ke svému klonu repa. Jednorázově:

```bash
# macOS — uprav cestu za = na svoji
APP_DIR="$HOME/dev/gpt-image-app"
sed -i '' "s#<GPT_IMAGE_APP_DIR>#$APP_DIR#g" ~/.claude/skills/gptimage/SKILL.md

# na Linuxu použij:
# sed -i "s#<GPT_IMAGE_APP_DIR>#$APP_DIR#g" ~/.claude/skills/gptimage/SKILL.md
```

> Můžeš to udělat i ručně — otevři `~/.claude/skills/gptimage/SKILL.md` a nahraď všechny výskyty `<GPT_IMAGE_APP_DIR>` cestou ke své appce.

### 3) Ověř

Otevři Claude Code a napiš:

```
/gptimage
```

Skill by se měl nabídnout. Zkus třeba:

```
/gptimage udělej produktovou fotku hrnku na světlém dřevě, na šířku
```

Claude si doptá, co potřebuje, u dražších věcí řekne **kolik to bude stát**, a teprve pak generuje.

## Co skill umí

- **Jeden obrázek** z textového promptu — poměr stran, rozlišení, kvalita, model, formát.
- **Dávku obrázků** z JSON souboru, včetně bezplatné kontroly (`validate`) předtím, než se cokoli zaplatí.
- **Úpravu existujícího obrázku** — výměna pozadí, stylová transformace.
- **Kompozici z víc referencí** (až 16) — třeba produkt z jedné fotky do scény z druhé.
- **Analýzu obrázku** (`describe`) — vytáhne z obrázku prompt, který můžeš použít dál.
- **Hlídá ceny** — cenu bere z reálné odpovědi API, ne z odhadu, a doporučí ti levný draft před drahým finálem.
- **Zná pravidla promptování** — pořadí `scéna → subjekt → detaily → omezení`, tabulku DO/DON'T a hlavní lekci: *měň jednu věc po druhé*.
- **Zná limity modelů** — že průhledné pozadí je na `gpt-image-2` zatím v preview (a v JPEG nejde nikde) a že drobný text se pořád láme.

## Tři věci, které ti ušetří peníze

1. **Kvalita je ta drahá páka, ne rozlišení.** Podle ceníku je `high` ~35× dražší než `low` ($0,211 vs $0,006); na reálném editu s referencí to vyšlo ~17×. Tak či tak: iteruj na `low`, finál dej na `high`.
2. **`gpt-image-1-mini` je výrazně levnější** — na návrhy a velké objemy je to rozumná volba.
3. **U dávky vždycky nejdřív `validate`.** Je zdarma a offline.

## Reference se účtují — pozor na rozpočet

Referenční obrázky se účtují jako **vstupní tokeny**, takže kompozice je výrazně dražší
než generování z textu. Naměřeno na stejném obrázku: bez referencí **$0,0063**, se dvěma
referencemi **$0,025** — tedy ~4×. Proto skill u dávek nejdřív vygeneruje jeden kus,
přečte reálnou cenu a teprve pak spočítá rozpočet.

Druhá věc: **ceníková tabulka je spodní odhad.** Platí pro 1024×1024 bez reference.
S referencí a 2K výstupem jde cena 2–4× nahoru.

## Průhledné pozadí — pozor

**`gpt-image-2` průhledné pozadí neumí** a API takový požadavek odmítne. Máš dvě cesty:

1. Použij model, který to umí: `-m gpt-image-1.5` (nebo `-1-mini`, `-1`) s `-f png` nebo `-f webp`.
2. Vygeneruj na jednolitém pozadí a odmaž ho v editoru.

Appka tuhle kombinaci zachytí **ještě předtím**, než se za volání zaplatí, a sama ti nabídne obě řešení.

## Doplň si skill o své vlastní know-how (doporučeno!)

Tenhle skill je **schválně univerzální** — umí nástroj a umí promptovat, ale nezná tvoji značku. Skill je jen složka markdown souborů, takže si ho snadno přizpůsobíš:

1. **Přidej vlastní referenční dokument.** Do `~/.claude/skills/gptimage/` si vytvoř např. `muj-styl.md` a sepiš:
   - tvoji barevnou paletu a vizuální styl (klidně i osvědčené prompty),
   - formáty, které reálně používáš,
   - jakou kvalitu chceš defaultně (třeba „vždycky draft na low, ať to nestojí majlant"),
   - co ve vizuálech nikdy nechceš.

2. **Odkaž na něj ze `SKILL.md`:**
   ```
   - `muj-styl.md` — moje vizuální pravidla (VŽDY přečíst před generováním)
   ```

3. **Klidně si uprav i defaulty.** Je to tvůj soubor.

> Čím konkrétnější kontext skillu dáš, tím víc budou výstupy „tvoje".

## Aktualizace skillu

Když stáhneš novější verzi repa, zopakuj krok 1 (přepíše starou verzi) a krok 2 (znovu nastav cestu). Vlastní `muj-styl.md` zůstane — krok 1 přepisuje jen `SKILL.md`.
