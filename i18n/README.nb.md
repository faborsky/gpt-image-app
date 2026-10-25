# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇨🇳 简体中文](README.zh-CN.md) · [🇯🇵 日本語](README.ja.md) · [🇸🇪 Svenska](README.sv.md) · **🇳🇴 Norsk** · [🇩🇰 Dansk](README.da.md)

Et CLI for å generere bilder med OpenAIs **GPT Image**-modeller (`gpt-image-2` med søsken): enkeltbilder eller batcher, redigering ut fra referansebilder og bildeanalyse. Laget for å styres av et menneske eller av en AI-agent som Claude Code. For deg som lager bilder i terminalen eller via en agent og vil vite hva hvert bilde kostet.

Bilder faktureres per token, og kvaliteten `high` koster rundt 35 ganger mer enn `low`. CLI-et viser den faktiske kostnaden etter hvert kall og stopper kombinasjoner som API-et uansett ville avvist, før du betaler for dem.

Forfatter: [Jindřich Fáborský](https://www.faborsky.com)

## Hva det gjør

- `generate`: ett bilde fra en prompt. Sideforhold i stedet for piksler (`-a 16:9 -r 2K`) og opptil 16 referansebilder (`-ref`) for redigering og komposisjoner.
- `batch`: flere bilder fra en JSON-fil, med fremdriftslinje og total kostnad til slutt. `validate` sjekker filen offline og gratis.
- `describe`: analyserer et bilde og returnerer en gjenbrukbar prompt.
- Faktisk kostnad basert på tokenene API-et brukte, og `--json` for skript og agenter.
- Fanger umulige kombinasjoner før du betaler (gjennomsiktig bakgrunn i JPEG) og prøver bare 429- og 5xx-feil på nytt, med eksponentiell backoff og jitter.
- Inkluderer en skill for Claude Code i `skill/`.

## Hurtigstart

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

Den fullstendige dokumentasjonen (OpenAI-nøkkel, alle flagg, priser, promptguide) er på engelsk: **[README.md](../README.md)**.

## Lisens

MIT · [LICENSE](../LICENSE)

## Forfatter

[Jindřich Fáborský](https://www.faborsky.com), markedsfører og underviser fra Praha. Jeg lærer markedsførere å bygge egne verktøy med AI.
