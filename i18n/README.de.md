# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · [🇧🇷 Português](README.pt-BR.md) · **🇩🇪 Deutsch** · [🇫🇷 Français](README.fr.md) · [🇨🇳 简体中文](README.zh-CN.md) · [🇯🇵 日本語](README.ja.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md) · [🇩🇰 Dansk](README.da.md)

CLI zum Generieren von Bildern mit den **GPT Image**-Modellen von OpenAI (`gpt-image-2` und Verwandte): einzelne Bilder oder Stapel, Bearbeitung anhand von Referenzbildern und Bildanalyse. Gebaut für Menschen und für KI-Agenten wie Claude Code. Für alle, die Bilder im Terminal oder über einen Agenten erzeugen und wissen wollen, was jedes Bild gekostet hat.

Bilder werden nach Tokens abgerechnet, und die Qualität `high` kostet etwa 35-mal so viel wie `low`. Das CLI zeigt nach jedem Aufruf die tatsächlichen Kosten und stoppt Kombinationen, die die API ohnehin ablehnen würde, bevor du dafür zahlst.

Autor: [Jindřich Fáborský](https://www.faborsky.com)

## Was es kann

- `generate`: ein Bild aus einem Prompt. Seitenverhältnisse statt Pixel (`-a 16:9 -r 2K`) und bis zu 16 Referenzbilder (`-ref`) für Bearbeitungen und Kompositionen.
- `batch`: mehrere Bilder aus einer JSON-Datei, mit Fortschrittsbalken und Gesamtkosten am Ende. `validate` prüft die Datei offline und kostenlos.
- `describe`: analysiert ein Bild und liefert einen wiederverwendbaren Prompt.
- Echte Kosten aus dem Token-Verbrauch der API, dazu `--json` für Skripte und Agenten.
- Fängt unmögliche Kombinationen ab, bevor du zahlst (transparenter Hintergrund im JPEG), und wiederholt nur 429- und 5xx-Fehler, mit exponentiellem Backoff und Jitter.
- Enthält einen Skill für Claude Code in `skill/`.

## Schnellstart

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

Die vollständige Dokumentation (OpenAI-Schlüssel, alle Flags, Preise, Prompting-Leitfaden) gibt es auf Englisch: **[README.md](../README.md)**.

## Lizenz

MIT · [LICENSE](../LICENSE)

## Autor

[Jindřich Fáborský](https://www.faborsky.com), Marketer und Dozent aus Prag. Ich bringe Marketern bei, mit KI eigene Tools zu bauen.
