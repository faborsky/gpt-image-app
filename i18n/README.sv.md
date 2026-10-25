# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇨🇳 简体中文](README.zh-CN.md) · [🇯🇵 日本語](README.ja.md) · **🇸🇪 Svenska** · [🇳🇴 Norsk](README.nb.md) · [🇩🇰 Dansk](README.da.md)

Ett CLI för att generera bilder med OpenAI:s **GPT Image**-modeller (`gpt-image-2` med syskon): enstaka bilder eller batchar, redigering utifrån referensbilder och bildanalys. Byggt för att styras av en människa eller av en AI-agent som Claude Code. För dig som skapar bilder i terminalen eller via en agent och vill veta vad varje bild kostade.

Bilder debiteras per token, och kvaliteten `high` kostar ungefär 35 gånger mer än `low`. CLI:t visar den faktiska kostnaden efter varje anrop och stoppar kombinationer som API:t ändå skulle avvisa innan du betalar för dem.

Författare: [Jindřich Fáborský](https://www.faborsky.com)

## Vad det gör

- `generate`: en bild från en prompt. Bildformat i stället för pixlar (`-a 16:9 -r 2K`) och upp till 16 referensbilder (`-ref`) för redigering och kompositioner.
- `batch`: flera bilder från en JSON-fil, med förloppsindikator och total kostnad på slutet. `validate` kontrollerar filen offline och gratis.
- `describe`: analyserar en bild och returnerar en återanvändbar prompt.
- Faktisk kostnad utifrån de tokens API:t förbrukade, och `--json` för skript och agenter.
- Fångar omöjliga kombinationer innan du betalar (transparent bakgrund i JPEG) och gör bara om 429- och 5xx-fel, med exponentiell backoff och jitter.
- Innehåller en skill för Claude Code i `skill/`.

## Snabbstart

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

Den fullständiga dokumentationen (OpenAI-nyckel, alla flaggor, priser, promptguide) finns på engelska: **[README.md](../README.md)**.

## Licens

MIT · [LICENSE](../LICENSE)

## Författare

[Jindřich Fáborský](https://www.faborsky.com), marknadsförare och utbildare från Prag. Jag lär marknadsförare att bygga egna verktyg med AI.
