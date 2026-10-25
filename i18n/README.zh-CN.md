# GPT Image

[🇬🇧 English](../README.md) · [🇨🇿 Čeština](../README.cs.md) · [🇪🇸 Español](README.es.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · **🇨🇳 简体中文** · [🇯🇵 日本語](README.ja.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md) · [🇩🇰 Dansk](README.da.md)

一个用 OpenAI **GPT Image** 模型（`gpt-image-2` 等）生成图片的命令行工具：单张或批量生成、基于参考图编辑、分析图片。人可以直接用，Claude Code 这类 AI 智能体也能调用。适合在终端或通过智能体生成图片、并想知道每张图花了多少钱的人。

图片按 token 计费，`high` 质量的价格大约是 `low` 的 35 倍。这个工具每次调用后都会报告真实费用，并在你付钱之前拦下 API 反正会拒绝的参数组合。

作者：[Jindřich Fáborský](https://www.faborsky.com)

## 功能

- `generate`：根据提示词生成一张图。用宽高比代替像素（`-a 16:9 -r 2K`），最多 16 张参考图（`-ref`）用于编辑和合成。
- `batch`：按 JSON 文件批量生成，带进度条，结束时显示总费用。`validate` 离线免费检查任务文件。
- `describe`：分析一张图片，返回可复用的提示词。
- 按 API 实际消耗的 token 计算真实费用；`--json` 方便脚本和智能体使用。
- 在付费前拦下不可能的组合（比如 JPEG 透明背景），只对 429 和 5xx 错误重试，采用指数退避加随机抖动。
- 附带一个 Claude Code skill，位于 `skill/`。

## 快速开始

```bash
git clone https://github.com/faborsky/gpt-image-app.git
cd gpt-image-app
./setup.sh
cp .env.example .env        # OPENAI_API_KEY=...

./run.sh generate "Photorealistic product shot of a matte ceramic mug on pale oak, morning window light, shallow depth of field" -a 16:9 -r 1K -q medium
```

完整文档（OpenAI 密钥、全部参数、价格、提示词指南）为英文：**[README.md](../README.md)**。

## 许可证

MIT · [LICENSE](../LICENSE)

## 作者

[Jindřich Fáborský](https://www.faborsky.com)，来自布拉格的营销人和讲师，教营销人员用 AI 自己做工具。
