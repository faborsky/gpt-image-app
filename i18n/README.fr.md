# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · **🇫🇷 Français** · [🇨🇳 简体中文](README.zh-CN.md) · [🇯🇵 日本語](README.ja.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md) · [🇩🇰 Dansk](README.da.md)

CLI pour générer des images avec les modèles **GPT Image** d'OpenAI (`gpt-image-2` et ses cousins) : images à l'unité ou par lots, retouches à partir d'images de référence et analyse d'images. Conçu pour être piloté aussi bien par une personne que par un agent IA comme Claude Code. Pour tous ceux qui génèrent des images depuis le terminal ou via un agent et veulent savoir combien chaque image a coûté.

Les images sont facturées en tokens, et la qualité `high` coûte environ 35 fois plus que `low`. Le CLI affiche le coût réel après chaque appel et bloque, avant que tu paies, les combinaisons que l'API refuserait de toute façon.

Auteur: [Jindřich Fáborský](https://www.faborsky.com)

## Ce qu'il fait

- `generate` : une image à partir d'un prompt. Des proportions au lieu de pixels (`-a 16:9 -r 2K`) et jusqu'à 16 images de référence (`-ref`) pour les retouches et les compositions.
- `batch` : plusieurs images depuis un fichier JSON, avec barre de progression et coût total à la fin. `validate` vérifie le fichier hors ligne, gratuitement.
- `describe` : analyse une image et renvoie un prompt réutilisable.
- Coût réel calculé sur les tokens consommés par l'API, et `--json` pour les scripts et les agents.
- Repère les combinaisons impossibles avant que tu paies (fond transparent en JPEG) et ne relance que les erreurs 429 et 5xx, avec backoff exponentiel et jitter.
- Livré avec un skill pour Claude Code dans `skill/`.

## Démarrage rapide

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

La documentation complète (clé OpenAI, tous les flags, tarifs, guide de prompts) est en anglais : **[README.md](../README.md)**.

## Licence

MIT · [LICENSE](../LICENSE)

## Auteur

[Jindřich Fáborský](https://www.faborsky.com), marketeur et formateur à Prague. J'apprends aux marketeurs à créer leurs propres outils avec l'IA.
