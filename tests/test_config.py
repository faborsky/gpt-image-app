"""Tests for validation, size mapping, pricing and retry classification. No API calls."""

from __future__ import annotations

import pytest

from gptimage.config import (
    FALLBACK_COST,
    MAX_LONG_EDGE,
    MAX_SHORT_EDGE,
    MIN_PIXELS,
    MODEL_PRICING,
    MODELS_WITHOUT_TRANSPARENCY,
    VALID_ASPECT_RATIOS,
    VALID_MODELS,
    VALID_QUALITIES,
    aspect_res_to_size,
    estimate_cost,
    is_retryable_error,
    validate_background_for_model,
    validate_model,
    validate_quality,
)


class _ApiError(Exception):
    """Stands in for openai.APIStatusError, which carries .status_code."""

    def __init__(self, status_code: int, message: str = "api error") -> None:
        super().__init__(message)
        self.status_code = status_code


class TestSizeMapping:
    """gpt-image-2 requires: multiples of 16, <=3840x2160, and a ~1 MP minimum."""

    @pytest.mark.parametrize("ratio", sorted(VALID_ASPECT_RATIOS))
    @pytest.mark.parametrize("resolution", ["1K", "2K", "4K"])
    def test_every_combination_satisfies_api_constraints(self, ratio: str, resolution: str) -> None:
        w, h = (int(x) for x in aspect_res_to_size(ratio, resolution).split("x"))

        assert w % 16 == 0 and h % 16 == 0, "both edges must be multiples of 16"
        assert max(w, h) <= MAX_LONG_EDGE, "long edge must fit the 3840 box"
        assert min(w, h) <= MAX_SHORT_EDGE, "short edge must fit the 2160 box"
        assert w * h >= MIN_PIXELS, "must stay above the ~1 MP minimum pixel budget"
        assert 1 / 3 <= w / h <= 3, "ratio must stay within 1:3..3:1"

    def test_wide_ratios_at_1k_stay_above_the_minimum(self) -> None:
        # The bug this guards: sizing by long edge gives 1024x576 = 0.59 MP, which the
        # API rejects outright. Sizing by area is what keeps 16:9 @ 1K legal.
        w, h = (int(x) for x in aspect_res_to_size("16:9", "1K").split("x"))
        assert w * h >= MIN_PIXELS

    def test_keeps_requested_orientation(self) -> None:
        w, h = (int(x) for x in aspect_res_to_size("9:16", "2K").split("x"))
        assert h > w, "portrait ratio must produce a portrait image"

    def test_approximates_the_requested_ratio(self) -> None:
        w, h = (int(x) for x in aspect_res_to_size("16:9", "2K").split("x"))
        assert abs((w / h) - (16 / 9)) < 0.05

    def test_higher_resolution_never_shrinks_the_image(self) -> None:
        def px(res: str) -> int:
            w, h = (int(x) for x in aspect_res_to_size("1:1", res).split("x"))
            return w * h

        assert px("1K") < px("2K") <= px("4K")


class TestPricing:
    def test_every_model_has_token_rates_and_a_fallback(self) -> None:
        assert VALID_MODELS == set(MODEL_PRICING) == set(FALLBACK_COST)

    def test_official_gpt_image_2_per_image_prices(self) -> None:
        # Source: https://developers.openai.com/api/docs/guides/image-generation
        assert FALLBACK_COST["gpt-image-2"] == {"low": 0.006, "medium": 0.053, "high": 0.211}

    def test_real_usage_beats_the_fallback_table(self) -> None:
        cost, source = estimate_cost("gpt-image-2", "high", {"input_tokens": 1000, "output_tokens": 5000})
        # 1000 * $8/1M + 5000 * $30/1M = $0.008 + $0.150
        assert cost == pytest.approx(0.158)
        assert "actual" in source

    def test_falls_back_when_usage_is_missing(self) -> None:
        cost, source = estimate_cost("gpt-image-2", "low", None)
        assert cost == 0.006
        assert "estimate" in source

    def test_auto_quality_is_priced_as_high(self) -> None:
        assert estimate_cost("gpt-image-2", "auto")[0] == estimate_cost("gpt-image-2", "high")[0]

    def test_quality_tiers_are_ordered_by_price(self) -> None:
        for model in VALID_MODELS:
            low = estimate_cost(model, "low")[0]
            medium = estimate_cost(model, "medium")[0]
            high = estimate_cost(model, "high")[0]
            assert low < medium < high, f"{model} tiers must increase in price"

    def test_mini_is_the_cheapest_model(self) -> None:
        costs = {m: estimate_cost(m, "high")[0] for m in VALID_MODELS}
        assert min(costs, key=costs.get) == "gpt-image-1-mini"

    def test_unknown_model_falls_back_to_the_default(self) -> None:
        assert estimate_cost("gpt-image-99", "high")[0] == estimate_cost("gpt-image-2", "high")[0]


class TestTransparencyGuard:
    """gpt-image-2 rejects background=transparent; catch it before spending a call."""

    def test_gpt_image_2_rejects_transparent(self) -> None:
        with pytest.raises(ValueError, match="does not support transparent"):
            validate_background_for_model("transparent", "gpt-image-2", "png")

    def test_error_names_a_model_that_does_support_it(self) -> None:
        with pytest.raises(ValueError) as exc:
            validate_background_for_model("transparent", "gpt-image-2", "png")
        assert "gpt-image-1.5" in str(exc.value)

    @pytest.mark.parametrize("model", sorted(VALID_MODELS - MODELS_WITHOUT_TRANSPARENCY))
    def test_older_models_allow_transparent_png(self, model: str) -> None:
        validate_background_for_model("transparent", model, "png")

    @pytest.mark.parametrize("model", sorted(VALID_MODELS - MODELS_WITHOUT_TRANSPARENCY))
    def test_jpeg_cannot_carry_transparency(self, model: str) -> None:
        with pytest.raises(ValueError, match="png or webp"):
            validate_background_for_model("transparent", model, "jpeg")

    @pytest.mark.parametrize("background", ["auto", "opaque"])
    def test_non_transparent_backgrounds_are_always_fine(self, background: str) -> None:
        validate_background_for_model(background, "gpt-image-2", "jpeg")


class TestValidators:
    def test_known_models_pass(self) -> None:
        for model in VALID_MODELS:
            assert validate_model(model) == model

    def test_unknown_model_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid model"):
            validate_model("dall-e-3")

    def test_quality_tiers(self) -> None:
        assert VALID_QUALITIES == {"low", "medium", "high", "auto"}
        with pytest.raises(ValueError, match="Invalid quality"):
            validate_quality("ultra")


class TestRetryClassification:
    @pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
    def test_retries_rate_limits_and_server_errors(self, code: int) -> None:
        # OpenAI's image endpoint does return sporadic 500s, so this path matters.
        assert is_retryable_error(_ApiError(code)) is True

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
    def test_does_not_retry_hard_errors(self, code: int) -> None:
        assert is_retryable_error(_ApiError(code)) is False

    def test_reads_code_attribute_as_well(self) -> None:
        err = Exception("rate limited")
        err.code = 429
        assert is_retryable_error(err) is True

    @pytest.mark.parametrize(
        "message", ["Connection error", "Request timed out", "temporarily unavailable"]
    )
    def test_retries_transient_network_failures(self, message: str) -> None:
        assert is_retryable_error(Exception(message)) is True

    def test_does_not_retry_unrecognised_error(self) -> None:
        assert is_retryable_error(ValueError("bad prompt")) is False
