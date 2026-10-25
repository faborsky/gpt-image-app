# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · **🇧🇷 Português** · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇨🇳 简体中文](README.zh-CN.md) · [🇯🇵 日本語](README.ja.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md) · [🇩🇰 Dansk](README.da.md)

CLI para gerar imagens com os modelos **GPT Image** da OpenAI (`gpt-image-2` e companhia): imagens avulsas ou em lote, edições a partir de imagens de referência e análise de imagens. Feito para ser usado tanto por uma pessoa quanto por um agente de IA como o Claude Code. Para quem gera imagens pelo terminal ou com um agente e quer saber quanto custou cada uma.

As imagens são cobradas por tokens, e a qualidade `high` custa cerca de 35 vezes mais que `low`. O CLI mostra o custo real depois de cada chamada e barra, antes de você pagar, combinações que a API recusaria de qualquer jeito.

Autor: [Jindřich Fáborský](https://www.faborsky.com)

## O que ele faz

- `generate`: uma imagem a partir de um prompt. Proporções em vez de pixels (`-a 16:9 -r 2K`) e até 16 imagens de referência (`-ref`) para edições e composições.
- `batch`: várias imagens a partir de um arquivo JSON, com barra de progresso e custo total no fim. `validate` confere o arquivo offline e de graça.
- `describe`: analisa uma imagem e devolve um prompt reutilizável.
- Custo real com base nos tokens que a API consumiu, e `--json` para scripts e agentes.
- Pega combinações impossíveis antes de você pagar (fundo transparente em JPEG) e só tenta de novo nos erros 429 e 5xx, com backoff exponencial e jitter.
- Inclui um skill para o Claude Code em `skill/`.

## Início rápido

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

A documentação completa (chave da OpenAI, todos os flags, preços, guia de prompts) está em inglês: **[README.md](../README.md)**.

## Licença

MIT · [LICENSE](../LICENSE)

## Autor

[Jindřich Fáborský](https://www.faborsky.com), profissional de marketing e educador de Praga. Ensino profissionais de marketing a criar suas próprias ferramentas com IA.
