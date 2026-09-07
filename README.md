# GPT Image

CLI na generování obrázků přes modely **GPT Image** od OpenAI (`gpt-image-2` a spol.). Jednotlivé obrázky i dávky, úpravy podle referenčních obrázků, rozbor obrázku. Postavené tak, aby to ovládal člověk i AI agent typu Claude Code.

Součástí je **[skill pro Claude Code](skill/INSTALL.md)**, takže tvůj agent zná ceny, kvalitativní stupně, pravidla promptování i to, co modely umí a co ne.

```bash
./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

- **Reálné náklady:** cena se bere z toho, kolik tokenů API skutečně spotřebovalo, není to odhad.
- **Poměry stran místo pixelů** (`-a 16:9 -r 2K`), namapované na to, co který model bere.
- **Strojově čitelný `--json`** na stdout, lidský výstup na stderr.
- **Opakuje jen to, co má smysl opakovat:** rate limity a pětistovky, které tenhle endpoint reálně vrací. S exponenciálním backoffem a jitterem.
- **Nemožné kombinace parametrů odchytí dřív, než zaplatíš:** třeba průhlednost v JPEGu, který alfa kanál nemá.

> [!TIP]
> **Appka je zdarma a je tvoje.** Naklonuj si ji, používej ji, přestav si ji po svém.
>
> Nevíš, jak ji rozjet? Nebo chceš AI v marketingu používat systematicky: řídit z jednoho místa všechny kanály, automatizovat rutinu, postavit si vlastní znalostní bázi a vibe codovat si nástroje na míru své firmě? To učím v kurzu **[AI First](https://aifirst.cz)**. Tahle appka je v něm vysvětlená i s tím, jak si postavit vlastní.

---

## Obsah

- [Instalace](#instalace)
- [Příkazy](#příkazy)
- [Modely](#modely)
- [Ceny](#ceny)
- [Referenční obrázky a kompozice](#referenční-obrázky-a-kompozice)
- [Průhlednost](#průhlednost)
- [Formát batch souboru](#formát-batch-souboru)
- [JSON výstup](#json-výstup)
- [Jak promptovat](#jak-promptovat)
- [Rate limity a spolehlivost](#rate-limity-a-spolehlivost)
- [Skill pro Claude Code](#skill-pro-claude-code)
- [Vývoj](#vývoj)
- [Když něco nefunguje](#když-něco-nefunguje)

---

## Instalace

**Co potřebuješ:** Python 3.11+ a API klíč od OpenAI.

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
```

Pak si přidej API klíč:

```bash
cp .env.example .env
# otevři .env a vlož svůj klíč
```

```
OPENAI_API_KEY=your-api-key-here
```

Klíč získáš na **[platform.openai.com/api-keys](https://platform.openai.com/api-keys)**. Na generování obrázků musí být na účtu kredit.

> `.env` je v gitignore. Klíč nikdy necommituj a nikdy ho nevkládej do kódu.

Ověř si instalaci, aniž bys cokoli utratil:

```bash
./run.sh --version
./run.sh validate jobs/example.json
```

---

## Příkazy

| Příkaz | Co dělá | Stojí peníze |
|---|---|---|
| `generate` | Vygeneruje jeden obrázek z promptu | ano |
| `batch` | Vygeneruje víc obrázků podle JSON souboru | ano |
| `validate` | Zkontroluje job soubor na chyby, offline | ne |
| `describe` | Rozebere existující obrázek a vrátí prompt | ano (levné) |

### generate

```bash
./run.sh generate "PROMPT" [options]
```

| Flag | Výchozí | Popis |
|---|---|---|
| `-a`, `--aspect` | `1:1` | Poměr stran |
| `-r`, `--resolution` | `1K` | `1K`, `2K`, `4K`, namapované na konkrétní pixely |
| `-q`, `--quality` | `high` | `low`, `medium`, `high`, `auto`. **Hlavní páka na cenu** |
| `-m`, `--model` | `gpt-image-2` | Viz [Modely](#modely) |
| `-b`, `--background` | `auto` | `auto`, `transparent`, `opaque` |
| `-f`, `--format` | `png` | `png`, `webp`, `jpeg` |
| `-o`, `--output` | `./output` | Výstupní složka |
| `-n`, `--name` | odvozeno z promptu | Vlastní název souboru, bez přípony |
| `-ref`, `--reference` | žádná | Referenční obrázek. **Opakuj, když jich chceš víc** (max 16) |
| `-if`, `--input-fidelity` | žádná | `high` / `low`, kolik detailu se zachová z referencí (ne na `gpt-image-2`) |
| `--json` | vypnuto | Strojově čitelný výsledek na stdout |

```bash
# Nejdřív levný náhled
./run.sh generate "a red bicycle against a white wall" -q low

# Pak ostrá verze
./run.sh generate "a red bicycle against a white wall" -q high -r 2K

# Široký formát na nejlevnějším modelu
./run.sh generate "abstract gradient background, deep teal to amber" -a 21:9 -m gpt-image-1-mini -q low

# Úprava existujícího obrázku
./run.sh generate "Replace the background with a seamless deep navy studio backdrop. Keep the product, its label and the lighting exactly the same." -ref product.png

# Kompozice: produkt do cílové scény (dvě reference)
./run.sh generate "Place the product from the first image onto the table from the second image. Keep its shape and colour exactly as they are. Match the scene's lighting and add a soft contact shadow." -ref product.png -ref scene.png
```

Soubory se jmenují `gpt_<base>_<ratio>_<resolution>_<timestamp>.<ext>`. Prefix `gpt_` drží výstupy rozpoznatelné, když do stejné složky zapisuje víc nástrojů na obrázky.

### batch

```bash
./run.sh batch jobs/example.json [-o ./images] [-m gpt-image-2] [-d 1.0] [--json]
```

Projede joby popořadě, ukazuje progress bar, hlásí chyby průběžně a na konci vypíše **celkovou cenu**. `Ctrl+C` dodělá rozdělaný obrázek a čistě skončí. Job soubor se ověří ještě před prvním voláním API, takže překlep nic nestojí.

### validate

```bash
./run.sh validate jobs/example.json
```

Zkontroluje strukturu, povolené hodnoty a cesty k referencím. **Žádná volání API, žádné náklady.**

### describe

```bash
./run.sh describe image.jpg              # krátký popis
./run.sh describe image.jpg --detailed   # plný popis rovnou použitelný jako prompt
```

Rozebere obrázek modelem `gpt-5.4-mini` a vrátí text, který můžeš poslat rovnou do `generate`.

---

## Modely

| Model | Velikosti | Průhlednost | Poznámka |
|---|---|---|---|
| **`gpt-image-2`** (výchozí) | libovolné šířka×výška do limitů | ano (preview, od 2026-08-20) | Vlajková loď. Nejlepší kvalita a úpravy. |
| `gpt-image-1.5` | 3 pevné velikosti | ano | Předchozí vlajková loď. |
| `gpt-image-1-mini` | 3 pevné velikosti | ano | Nejlevnější, dobrý na náhledy a objem. |
| `gpt-image-1` | 3 pevné velikosti | ano | Legacy. |

`gpt-image-2` bere libovolné rozměry: obě strany násobek 16, nejdelší hrana max 3840 px, poměr mezi 1:3 a 3:1 a **minimální rozpočet zhruba 1 MP**. Poslední podmínka nikde v dokumentaci není, vyšla najevo až při ostrém testování. Proto se `-a`/`-r` mapují podle *plochy*, ne podle delší hrany. Kdyby se 16:9 v 1K počítalo podle delší hrany, vyšlo by 1024×576 (0.59 MP), což API rovnou odmítne.

Ostatní modely berou jen `1024x1024`, `1536x1024` a `1024x1536`. Požadavek se automaticky zaokrouhlí na nejbližší z nich.

---

## Ceny

Obrázky se účtují jako **tokeny**, takže CLI po každém volání hlásí **reálnou cenu z pole `usage`, které vrací API**. Když `usage` chybí, spadne to zpátky na publikovanou tabulku cen za obrázek.

Publikované ceny za obrázek pro `gpt-image-2` ([zdroj](https://developers.openai.com/api/docs/guides/image-generation), ověřeno 2026-07-25):

| Kvalita | 1024×1024 | 1024×1536 / 1536×1024 |
|---|---|---|
| `low` | **$0.006** | $0.005 |
| `medium` | **$0.053** | $0.041 |
| `high` | **$0.211** | $0.165 |

Sazby za 1M tokenů:

| Model | Vstup | Výstup |
|---|---|---|
| `gpt-image-2` | $8.00 | $30.00 |
| `gpt-image-1.5` | $8.00 | $32.00 |
| `gpt-image-1-mini` | $2.50 | $8.00 |
| `gpt-image-1` | $10.00 | $40.00 |

**Kvalita je hlavní páka na cenu, `high` vyjde zhruba 35× dráž než `low`.** Iteruj na `low` a vítěze vyrenderuj na `high`. Větší nečtvercové formáty můžou stát o kus *míň* než čtvercové, protože výstupní tokeny kopírují i tvar, nejen plochu.

`describe` běží na `gpt-5.4-mini` ($0.75/1M vstup, $4.50/1M výstup), zlomek centu za obrázek.

---

## Referenční obrázky a kompozice

Když předáš referenci, obrázek se upravuje místo generování od nuly. **Opakuj `-ref`, pokud chceš referencí víc.** Maximum je **16**, tolik má endpoint zdokumentováno, každý soubor png/webp/jpg do 50 MB.

Víc referencí je to, co dělá kompozici vůbec zadatelnou. Typický případ je *produkt + cílová scéna*:

```bash
./run.sh generate "Place the product from the first image onto the wooden table from the second image. \
  Keep its shape and colour exactly as they are. Match the scene's morning lighting and add a soft contact shadow." \
  -ref product.png -ref scene.png
```

Na vstupy odkazuj pozicí („the first image“, „the second image“) a napiš výslovně, co má zůstat beze změny.

V batch jobech projde obojí:

```json
{ "prompt": "...", "reference_path": "single.png" }
{ "prompt": "...", "reference_paths": ["product.png", "scene.png"] }
```

### Reference stojí reálné peníze

Referenční obrázky se účtují jako **vstupní obrazové tokeny**, takže kompozice zdaleka není zadarmo. Změřeno na stejném běhu 1024×1024 v `low`:

| Volání | Vstupní tokeny | Cena |
|---|---|---|
| jen text | 24 | $0.0063 |
| dvě reference | 2365 | **$0.025** |

Počítej s tím: batch dvaceti kompozic je blíž $0.50 než $0.13, a to ještě na `low`.

### input_fidelity

`-if high` / `-if low` řídí, jak silně se zachová detail z reference. Funguje to ale jen na `gpt-image-1`, `gpt-image-1.5` a `gpt-image-1-mini`. **`gpt-image-2` to odmítne** (`400`), protože vstupy zpracovává vždycky ve vysoké věrnosti. CLI to odchytí lokálně a řekne ti to.

Na modelech, které to berou, je to zároveň páka na cenu: `high` spotřebovalo **4791** tokenů proti **618** u `low` na stejné úpravě.

**Jedna věc, o které je dobré vědět:** u kompozice ze dvou referencí na `gpt-image-2` model neuposlechl výslovný pokyn zachovat jemný detail povrchu („keep the ripeness spots exactly as they are“). Tvar a barva přežily, jemná kresba ne. Věrnost se na tomhle modelu zvednout nedá, takže úpravy, které stojí na zachování jemného detailu, můžou dopadnout líp na `gpt-image-1.5` s `-if high`.

---

## Průhlednost

**Průhledné pozadí zvládnou všechny současné modely**, včetně `gpt-image-2`. Tomu průhlednost přibyla **v preview 2026-08-20** ([changelog](https://developers.openai.com/api/docs/changelog)). Do té doby to byla jediná věc, kterou vlajková loď neuměla. To omezení je pryč.

```bash
# Ořezaný asset, který položíš na jakékoli pozadí
./run.sh generate "A single glossy red apple, centered, studio product shot, no shadow" -b transparent -f png
```

**Průhlednost potřebuje formát s alfa kanálem**, takže jen `-f png` nebo `-f webp`. `-f jpeg` skončí odmítnutím, a to lokálně, ještě než odejde jakékoli volání:

```
Transparent background requires png or webp output (jpeg has no alpha channel).
```

Kdyby to přesto odešlo, vrátí se `400 invalid_transparent_background_output_format`.

**Ověřeno naživo 2026-08-23** na `gpt-image-2`: PNG i WebP se vrací jako opravdové RGBA s plně průhlednými pixely (alfa 0 v rozích, neprůhledný objekt), a to u `generate` i u úprav s `-ref`. A protože `gpt-image-2` bere i libovolné rozměry, dá se teď mít průhlednost *a zároveň* nestandardní velikost v jednom volání, třeba 1072×1072 nebo 16:9 ve 2K. Starší modely to neumí.

U automatizace pamatuj na to, že je to pořád preview: chování se ještě může změnit. Pojistka v CLI je proto datová (`MODELS_WITHOUT_TRANSPARENCY` v `config.py`), kdyby některý model podporu ztratil.

---

## Formát batch souboru

```json
{
  "defaults": {
    "aspect_ratio": "16:9",
    "resolution": "1K",
    "quality": "medium",
    "format": "png"
  },
  "jobs": [
    {
      "prompt": "Photorealistic product shot of a matte ceramic pour-over dripper on pale oak, morning window light",
      "output_name": "coffee_dripper"
    },
    {
      "prompt": "Editorial illustration of a city at dusk as layered paper cut-outs, deep teal and amber",
      "output_name": "paper_city",
      "quality": "high",
      "aspect_ratio": "4:5"
    }
  ]
}
```

`defaults` je volitelný a platí pro každý job. Každý job **musí** mít `prompt`. Volitelné přepisy jsou `output_name`, `aspect_ratio`, `resolution`, `quality`, `background`, `format` a `reference_path`. Funkční příklad je v [`jobs/example.json`](jobs/example.json).

---

## JSON výstup

`--json` dá parsovatelný výsledek na **stdout** a lidsky čitelný výstup přesune na **stderr**.

```bash
./run.sh generate "a lake at dawn" --json | jq -r '.cost_usd'
```

```json
{
  "success": true,
  "output_path": "/path/to/output/gpt_a_lake_at_dawn_1x1_1K_20260725_120000.png",
  "model": "gpt-image-2",
  "aspect_ratio": "1:1",
  "resolution": "1K",
  "size": "1072x1072",
  "quality": "high",
  "format": "png",
  "background": "auto",
  "cost_usd": 0.2113,
  "cost_source": "actual (32 in + 7040 out tokens)",
  "attempts": 1
}
```

`cost_source` říká, jestli číslo přišlo ze skutečné spotřeby tokenů (`actual (…)`), nebo ze záložní tabulky (`estimate (…)`). Batch k tomu přidá součty a pole s údaji za jednotlivé obrázky.

---

## Jak promptovat

Vychází z [průvodce promptováním GPT Image](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) od OpenAI.

**Prompt skládej v tomhle pořadí: pozadí/scéna → objekt → hlavní detaily → omezení.** U složitějších věcí použij krátké pojmenované bloky nebo odřádkování místo jednoho dlouhého odstavce. Šablona, kterou jde přeletět očima, funguje líp než souvislý text.

### Co dělat a co ne

| Dělej | Nedělej |
|---|---|
| Buď konkrétní na materiály, tvary, textury a médium (fotka, akvarel, 3D render) | Nechávat médium náhodě |
| Napiš výslovně **„photorealistic“**, když chceš realismus | Spoléhat, že realismus je výchozí |
| Vyžádej si reálnou texturu: „pores, fabric wear, wood grain“ | Čekat živé povrchy bez vyžádání |
| Přesné znění textu dej do **uvozovek** nebo VELKÝMI PÍSMENY a vyžaduj doslovné vykreslení | Doufat, že text vyjde správně |
| Záludné názvy značek vyhláskuj **písmeno po písmenu** | Věřit, že neobvyklý pravopis přežije |
| U úprav: „change only X“ + „keep everything else the same“ | Popsat jen to, co se mění |
| Seznam toho, co se nesmí měnit, zopakuj v **každé** iteraci | Spoléhat, že si model pamatuje, co má chránit |
| Iteruj malými kroky, jedna změna na kolo | Nacpat všechno do jednoho přeplácaného promptu |
| Řekni, k čemu to bude (reklama, UI mock, infografika), ať model ví, jak to vypiplat | Nechávat vyznění nejasné |
| Fotografický jazyk používej jen na celkový dojem | Přespecifikovat objektiv a tělo foťáku |

**Co platí ze všeho nejvíc:** iteruj v malých krocích po jedné změně a vždycky z čistého základního promptu. Přeplácané prompty a přepisování všeho najednou jsou nejrychlejší cesta, jak přijít o to, co už fungovalo.

### Text uvnitř obrázků

Dokumentace to říká narovinu: *„I když se to výrazně zlepšilo, model může pořád mít problém s přesným umístěním textu a jeho čitelností.“*

Takže když na textu záleží:

1. Uveď přesný řetězec v uvozovkách a napiš **verbatim, no extra characters**.
2. Neobvyklá slova vyhláskuj písmeno po písmenu.
3. Použij `-q medium` nebo `-q high`. Na `low` se malý text rozsype.
4. Drž jednoduchý layout a málo slov.

### Identita a kompozice

U úprav, kde musí zůstat zachovaná podoba, vyjmenuj výslovně, co se nesmí měnit, a opakuj to každé kolo. U kompozice řekni jasně, který prvek se přesouvá kam. A pozor, `input_fidelity` na `gpt-image-2` neplatí, jeho výstup je ve vysoké věrnosti už z principu.

### Známé slabiny

- Přesné umístění textu a jeho čitelnost, hlavně u malého nebo hustého textu.
- Průhlednost na `gpt-image-2` je pořád **preview** (viz [Průhlednost](#průhlednost)).
- Moderace obsahu může prompt odmítnout. Parametr `moderation` (`auto`/`low`) tohle CLI zatím ven nevystavuje.

---

## Rate limity a spolehlivost

Limity jsou podle usage tieru (Free → Tier 5, posouvá se podle kumulativní útraty) a měří se v **RPM**, **TPM** a u obrázkových modelů navíc v **IPM (obrázky za minutu)**. V hlavičkách odpovědi najdeš `x-ratelimit-remaining-requests` a spol.

Jak se chová tohle CLI:

- **429 a 5xx** → zopakuje se až 3×, exponenciální backoff **plus jitter**, strop 60 s. OpenAI jitter výslovně doporučuje a obrázkový endpoint opravdu občas vrací pětistovky. Při vývoji téhle verze vracel 500 pro všechny modely delší dobu.
- **400 / 401 / 403 / 404** → okamžitá chyba. Opakovat neplatný požadavek nebo špatný klíč jen žere čas a kvótu.
- **Odmítnutí moderací** → nahlásí se jako `Content filtered` a nikdy se neopakuje.
- **Nemožné kombinace parametrů** (průhledný JPEG, `input_fidelity` na `gpt-image-2`) → odmítnou se lokálně, ještě než odejde volání.
- **Batch** čeká `--delay` sekund mezi obrázky. Zvedni to, když narážíš na IPM limity.

---

## Skill pro Claude Code

Ve složce [`skill/`](skill/) je skill pro Claude Code, který tvého agenta naučí tenhle nástroj: příkazy, ceny, kvalitativní stupně, pravidla promptování a limity modelů. Návod na instalaci: **[skill/INSTALL.md](skill/INSTALL.md)**.

```bash
mkdir -p ~/.claude/skills
cp -R skill/gptimage ~/.claude/skills/gptimage
# pak ve skillu nahraď <GPT_IMAGE_APP_DIR> cestou k tomuhle repu
```

---

## Vývoj

```bash
source .venv/bin/activate
python -m pytest tests/ -q     # offline testy, žádná volání API
ruff check gptimage/           # lint
```

| Soubor | Za co odpovídá |
|---|---|
| `gptimage/config.py` | Modely, ceny, `aspect_res_to_size()`, validátory, pojistka na průhlednost, klasifikace retry |
| `gptimage/generator.py` | `images.generate` / `images.edit`, dekódování base64, reálná cena z usage, retry a backoff |
| `gptimage/batch.py` | Parsování a validace job souboru, sekvenční runner, součty nákladů |
| `gptimage/cli.py` | Typer příkazy, lidský a `--json` výstup |
| `gptimage/utils.py` | Čištění a generování názvů souborů |

Poznámky k architektuře, které potřebuje AI agent, jsou v **[CLAUDE.md](CLAUDE.md)**. Jak se OpenAI Image API reálně chová, popisuje **[docs/api-notes.md](docs/api-notes.md)**.

---

## Když něco nefunguje

**`Missing API key`**: zkopíruj `.env.example` do `.env` a vlož svůj klíč.

**`Transparent background requires png or webp output`**: `-b transparent` spolu s `-f jpeg`. Změň formát, viz [Průhlednost](#průhlednost).

**`below the current minimum pixel budget`**: do API dorazila velikost pod ~1 MP. Mapování `-a`/`-r` tomuhle předchází, takže když to vidíš, velikost přišla odjinud.

**Chyby 500 na každém požadavku**: výpadek na straně OpenAI, ne tvoje nastavení. CLI to zkouší znovu s backoffem, stav najdeš na [status.openai.com](https://status.openai.com).

**`429`**: rate limit nebo strop útraty. U batchů zvedni `--delay`, nebo si zkontroluj tier.

**`Content filtered`**: moderace prompt odmítla. Přeformuluj ho, opakovat stejné znění nepomůže.

**`Virtual environment not found`**: spusť `./setup.sh`.

---

## Licence

MIT, viz [LICENSE](LICENSE).
