# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇨🇳 简体中文](README.zh-CN.md) · [🇯🇵 日本語](README.ja.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md) · **🇩🇰 Dansk**

Et CLI til at generere billeder med OpenAI's **GPT Image**-modeller (`gpt-image-2` og søskende): enkeltbilleder eller batches, redigering ud fra referencebilleder og billedanalyse. Bygget til at blive styret af et menneske eller af en AI-agent som Claude Code. Til dig, der laver billeder i terminalen eller via en agent og vil vide, hvad hvert billede kostede.

Billeder afregnes pr. token, og kvaliteten `high` koster omkring 35 gange mere end `low`. CLI'et viser den faktiske pris efter hvert kald og stopper kombinationer, som API'et alligevel ville afvise, før du betaler for dem.

Forfatter: [Jindřich Fáborský](https://www.faborsky.com)

## Hvad det gør

- `generate`: ét billede ud fra en prompt. Billedformat i stedet for pixels (`-a 16:9 -r 2K`) og op til 16 referencebilleder (`-ref`) til redigering og kompositioner.
- `batch`: flere billeder fra en JSON-fil, med statuslinje og samlet pris til sidst. `validate` tjekker filen offline og gratis.
- `describe`: analyserer et billede og returnerer en genbrugelig prompt.
- Faktisk pris ud fra de tokens, API'et brugte, og `--json` til scripts og agenter.
- Fanger umulige kombinationer, før du betaler (gennemsigtig baggrund i JPEG), og prøver kun 429- og 5xx-fejl igen, med eksponentiel backoff og jitter.
- Indeholder en skill til Claude Code i `skill/`.

## Hurtig start

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

Den fulde dokumentation (OpenAI-nøgle, alle flag, priser, promptguide) er på engelsk: **[README.md](../README.md)**.

## Licens

MIT · [LICENSE](../LICENSE)

## Forfatter

[Jindřich Fáborský](https://www.faborsky.com), marketingmand og underviser fra Prag. Jeg lærer marketingfolk at bygge deres egne værktøjer med AI.
