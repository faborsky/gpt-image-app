# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇨🇳 简体中文](README.zh-CN.md) · **🇯🇵 日本語** · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md) · [🇩🇰 Dansk](README.da.md)

OpenAI の **GPT Image** モデル（`gpt-image-2` ほか）で画像を生成する CLI です。単体生成とバッチ生成、参照画像をもとにした編集、画像の分析に対応。人が直接使うことも、Claude Code のような AI エージェントから操作することもできます。ターミナルやエージェントで画像を作り、1 枚ごとのコストを把握したい人向け。

画像はトークン単位で課金され、`high` 品質は `low` のおよそ 35 倍の料金です。この CLI は呼び出しのたびに実際のコストを表示し、どうせ API に拒否される組み合わせは課金前に止めます。

作者：[Jindřich Fáborský](https://www.faborsky.com)

## できること

- `generate`：プロンプトから画像を 1 枚生成。ピクセルではなくアスペクト比で指定（`-a 16:9 -r 2K`）し、編集や合成には参照画像を最大 16 枚（`-ref`）使えます。
- `batch`：JSON ファイルから複数の画像を生成。進捗バーを表示し、最後に合計コストを出します。`validate` はジョブファイルをオフラインで無料チェックします。
- `describe`：画像を分析し、再利用できるプロンプトを返します。
- API が実際に消費したトークンから算出した実コスト。スクリプトやエージェント向けに `--json` も用意。
- 課金前にありえない組み合わせ（JPEG の透過背景など）を検出し、再試行は 429 と 5xx だけ。指数バックオフとジッター付きです。
- Claude Code 用の skill を `skill/` に同梱。

## クイックスタート

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

完全なドキュメント（OpenAI キー、全フラグ、料金、プロンプトガイド）は英語です：**[README.md](../README.md)**

## ライセンス

MIT · [LICENSE](../LICENSE)

## 作者

[Jindřich Fáborský](https://www.faborsky.com)、プラハ在住のマーケター・講師。マーケターが AI で自分のツールを作れるよう教えています。
