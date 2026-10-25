# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · **🇪🇸 Español** · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇨🇳 简体中文](README.zh-CN.md) · [🇯🇵 日本語](README.ja.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md) · [🇩🇰 Dansk](README.da.md)

CLI para generar imágenes con los modelos **GPT Image** de OpenAI (`gpt-image-2` y compañía): imágenes sueltas o por lotes, ediciones a partir de imágenes de referencia y análisis de imágenes. Pensado para usarlo tanto una persona como un agente de IA tipo Claude Code. Para quien genera imágenes desde la terminal o con un agente y quiere saber cuánto ha costado cada una.

Las imágenes se cobran por tokens, y la calidad `high` sale unas 35 veces más cara que `low`. El CLI te dice el coste real después de cada llamada y frena antes de que pagues por combinaciones que la API va a rechazar de todos modos.

Autor: [Jindřich Fáborský](https://www.faborsky.com)

## Qué hace

- `generate`: una imagen a partir de un prompt. Proporciones en lugar de píxeles (`-a 16:9 -r 2K`) y hasta 16 imágenes de referencia (`-ref`) para ediciones y composiciones.
- `batch`: varias imágenes desde un archivo JSON, con barra de progreso y coste total al final. `validate` revisa el archivo sin conexión y gratis.
- `describe`: analiza una imagen y devuelve un prompt reutilizable.
- Coste real según los tokens que ha consumido la API, y `--json` para scripts y agentes.
- Detecta combinaciones imposibles antes de pagar (fondo transparente en JPEG) y solo reintenta los errores 429 y 5xx, con backoff exponencial y jitter.
- Incluye un skill para Claude Code en `skill/`.

## Inicio rápido

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

La documentación completa (clave de OpenAI, todos los flags, precios, guía de prompts) está en inglés: **[README.md](../README.md)**.

## Licencia

MIT · [LICENSE](../LICENSE)

## Autor

[Jindřich Fáborský](https://www.faborsky.com), marketer y formador de Praga. Enseño a los marketers a crear sus propias herramientas con IA.
