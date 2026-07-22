from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from traceable_support.provider.contract import (
    Tg07aContractError,
    calculate_cost,
    canonical_json_bytes,
    parse_chat_completion,
)
from traceable_support.provider.response import json_response
from traceable_support.provider.usage import (
    normalize_provider_usage,
    parse_chat_completion_compatible,
    validate_usage_compatibility_facts,
    validate_usage_normalization,
)


USAGE = {
    "prompt_tokens": 1000,
    "completion_tokens": 200,
    "total_tokens": 1200,
    "prompt_cache_hit_tokens": 100,
    "prompt_cache_miss_tokens": 900,
}


def usage_with_details(cached_tokens: object = 100) -> dict:
    return {**USAGE, "prompt_tokens_details": {"cached_tokens": cached_tokens}}


def plan_result() -> dict:
    return {
        "schema_version": "tg07a-evidence-plan-output-v1",
        "stage": "evidence_plan",
        "issue_points": ["核对CZ-R1复位步骤"],
        "model_scope": {"mode": "current_model_only", "models": ["CZ-R1"]},
        "query_intents": [
            {"intent_id": "intent-1", "query": "CZ-R1 复位步骤", "model_scope": ["CZ-R1"]}
        ],
    }


def extended_body() -> bytes:
    return json_response(plan_result(), usage=usage_with_details())


class TG07UUsageCompatibilityTests(unittest.TestCase):
    def assertCode(self, code: str, operation) -> None:  # noqa: N802 - unittest convention
        with self.assertRaises(Tg07aContractError) as raised:
            operation()
        self.assertEqual(raised.exception.code, code)

    def test_historical_five_field_usage_normalizes_without_change(self) -> None:
        normalized = normalize_provider_usage(USAGE)
        self.assertEqual(normalized["normalized_usage"], USAGE)
        self.assertEqual(
            normalized["compatibility_facts"],
            {
                "schema_version": "tg07u-usage-compatibility-facts-v1",
                "prompt_tokens_details_present": False,
                "prompt_tokens_details_exact_cached_tokens_object": False,
                "cached_tokens_matches_prompt_cache_hit_tokens": None,
                "completion_tokens_details_present": False,
                "completion_tokens_details_exact_reasoning_tokens_object": False,
                "reasoning_tokens_within_completion_tokens": None,
                "validation_passed": True,
            },
        )

    def test_observed_six_field_usage_normalizes_to_exact_historical_five(self) -> None:
        source = usage_with_details()
        before = copy.deepcopy(source)
        normalized = normalize_provider_usage(source)
        self.assertEqual(source, before)
        self.assertEqual(normalized["normalized_usage"], USAGE)
        self.assertEqual(
            normalized["compatibility_facts"],
            {
                "schema_version": "tg07u-usage-compatibility-facts-v1",
                "prompt_tokens_details_present": True,
                "prompt_tokens_details_exact_cached_tokens_object": True,
                "cached_tokens_matches_prompt_cache_hit_tokens": True,
                "completion_tokens_details_present": False,
                "completion_tokens_details_exact_reasoning_tokens_object": False,
                "reasoning_tokens_within_completion_tokens": None,
                "validation_passed": True,
            },
        )

    def test_completion_details_usage_normalizes_to_exact_historical_five(self) -> None:
        source = {**USAGE, "completion_tokens_details": {"reasoning_tokens": 50}}
        normalized = normalize_provider_usage(source)
        self.assertEqual(normalized["normalized_usage"], USAGE)
        self.assertEqual(
            normalized["compatibility_facts"]["completion_tokens_details_present"], True
        )
        self.assertEqual(
            normalized["compatibility_facts"]["reasoning_tokens_within_completion_tokens"], True
        )

    def test_both_optional_usage_fields_normalize_together(self) -> None:
        source = {
            **usage_with_details(),
            "completion_tokens_details": {"reasoning_tokens": 200},
        }
        normalized = normalize_provider_usage(source)
        self.assertEqual(normalized["normalized_usage"], USAGE)

    def test_completion_details_response_matches_five_field_usage_and_cost(self) -> None:
        five = parse_chat_completion_compatible(json_response(plan_result(), usage=USAGE))
        body = json_response(
            plan_result(),
            usage={**USAGE, "completion_tokens_details": {"reasoning_tokens": 100}},
        )
        extended = parse_chat_completion_compatible(body)
        self.assertEqual(extended["usage"], five["usage"])
        self.assertEqual(extended["cost"], five["cost"])
        self.assertEqual(extended["content"], five["content"])

    def test_completion_details_bad_shapes_are_rejected(self) -> None:
        for details in (None, {}, {"reasoning_tokens": -1}, {"reasoning_tokens": True},
                        {"reasoning_tokens": 201}, {"reasoning_tokens": 10, "other": 0}):
            with self.subTest(details=details):
                self.assertCode(
                    "provider_usage_invalid",
                    lambda details=details: normalize_provider_usage(
                        {**USAGE, "completion_tokens_details": details}
                    ),
                )

    def test_reasoning_content_is_removed_and_recorded_not_persisted(self) -> None:
        envelope = json.loads(extended_body())
        envelope["choices"][0]["message"]["reasoning_content"] = "隐藏推理过程"
        parsed = parse_chat_completion_compatible(canonical_json_bytes(envelope))
        self.assertTrue(parsed["reasoning_content_removed"])
        self.assertNotIn("隐藏推理过程", json.dumps(parsed, ensure_ascii=False))
        self.assertEqual(parsed["usage"], USAGE)

    def test_reasoning_content_non_string_is_rejected(self) -> None:
        envelope = json.loads(extended_body())
        envelope["choices"][0]["message"]["reasoning_content"] = {"nested": True}
        self.assertCode(
            "provider_reasoning_unexpected",
            lambda: parse_chat_completion_compatible(canonical_json_bytes(envelope)),
        )

    def test_historical_response_keeps_old_parser_result_and_cost(self) -> None:
        body = json_response(plan_result(), usage=USAGE)
        old = parse_chat_completion(body)
        compatible = parse_chat_completion_compatible(body)
        self.assertEqual({key: compatible[key] for key in old}, old)
        self.assertEqual(compatible["usage"], USAGE)
        self.assertEqual(compatible["cost"], calculate_cost(USAGE))

    def test_six_field_response_matches_five_field_usage_and_cost(self) -> None:
        five = parse_chat_completion_compatible(json_response(plan_result(), usage=USAGE))
        six = parse_chat_completion_compatible(extended_body())
        self.assertEqual(six["usage"], five["usage"])
        self.assertEqual(six["cost"], five["cost"])
        self.assertEqual(six["content"], five["content"])
        self.assertTrue(six["usage_compatibility"]["validation_passed"])

    def test_six_field_path_calls_the_frozen_complete_parser_with_normalized_usage(self) -> None:
        import traceable_support.provider.usage as compat

        with patch.object(compat, "parse_chat_completion", wraps=parse_chat_completion) as old_parser:
            parse_chat_completion_compatible(extended_body())
        old_parser.assert_called_once()
        normalized_envelope = json.loads(old_parser.call_args.args[0])
        self.assertEqual(normalized_envelope["usage"], USAGE)
        self.assertNotIn("prompt_tokens_details", normalized_envelope["usage"])

    def test_prompt_tokens_details_null_is_rejected(self) -> None:
        self.assertCode("provider_usage_invalid", lambda: normalize_provider_usage({**USAGE, "prompt_tokens_details": None}))

    def test_unknown_top_level_usage_field_is_rejected(self) -> None:
        self.assertCode("provider_usage_invalid", lambda: normalize_provider_usage({**USAGE, "other": 1}))

    def test_completion_tokens_details_exact_reasoning_shape_is_allowed(self) -> None:
        normalized = normalize_provider_usage(
            {**USAGE, "completion_tokens_details": {"reasoning_tokens": 0}}
        )
        self.assertEqual(normalized["normalized_usage"], USAGE)

    def test_prompt_details_missing_nested_key_is_rejected(self) -> None:
        self.assertCode("provider_usage_invalid", lambda: normalize_provider_usage({**USAGE, "prompt_tokens_details": {}}))

    def test_prompt_details_extra_nested_key_is_rejected(self) -> None:
        self.assertCode(
            "provider_usage_invalid",
            lambda: normalize_provider_usage(
                {**USAGE, "prompt_tokens_details": {"cached_tokens": 100, "other": 0}}
            ),
        )

    def test_prompt_details_non_object_shapes_are_rejected(self) -> None:
        for value in ("100", 100, [100], {"cached_tokens": {"nested": 100}}):
            with self.subTest(value=value):
                self.assertCode(
                    "provider_usage_invalid",
                    lambda value=value: normalize_provider_usage({**USAGE, "prompt_tokens_details": value}),
                )

    def test_cached_tokens_bool_is_rejected(self) -> None:
        self.assertCode("provider_usage_invalid", lambda: normalize_provider_usage(usage_with_details(True)))

    def test_cached_tokens_negative_is_rejected(self) -> None:
        self.assertCode("provider_usage_invalid", lambda: normalize_provider_usage(usage_with_details(-1)))

    def test_cached_tokens_string_array_and_deep_object_are_rejected(self) -> None:
        for value in ("100", [100], {"nested": 100}):
            with self.subTest(value=value):
                self.assertCode(
                    "provider_usage_invalid",
                    lambda value=value: normalize_provider_usage(usage_with_details(value)),
                )

    def test_cached_tokens_mismatch_is_rejected(self) -> None:
        self.assertCode("provider_usage_invalid", lambda: normalize_provider_usage(usage_with_details(99)))

    def test_missing_required_base_usage_field_is_rejected(self) -> None:
        value = usage_with_details()
        del value["prompt_cache_miss_tokens"]
        self.assertCode("provider_usage_invalid", lambda: normalize_provider_usage(value))

    def test_base_usage_bool_negative_and_string_types_are_rejected(self) -> None:
        for replacement in (True, -1, "1000"):
            with self.subTest(replacement=replacement):
                self.assertCode(
                    "provider_usage_invalid",
                    lambda replacement=replacement: normalize_provider_usage(
                        {**usage_with_details(), "prompt_tokens": replacement}
                    ),
                )

    def test_cache_split_arithmetic_error_is_rejected(self) -> None:
        self.assertCode(
            "provider_usage_invalid",
            lambda: normalize_provider_usage({**usage_with_details(), "prompt_cache_miss_tokens": 899}),
        )

    def test_total_arithmetic_error_is_rejected(self) -> None:
        self.assertCode(
            "provider_usage_invalid",
            lambda: normalize_provider_usage({**usage_with_details(), "total_tokens": 1199}),
        )

    def test_usage_missing_remains_missing_and_never_becomes_zero(self) -> None:
        body = json_response(plan_result(), usage=None)
        self.assertCode("provider_usage_missing", lambda: parse_chat_completion_compatible(body))
        self.assertCode("provider_usage_missing", lambda: normalize_provider_usage(None))

    def test_legal_optional_usage_does_not_bypass_model_validation(self) -> None:
        body = json_response(plan_result(), usage=usage_with_details(), model="wrong-model")
        self.assertCode("provider_model_mismatch", lambda: parse_chat_completion_compatible(body))

    def test_legal_optional_usage_does_not_bypass_choice_validation(self) -> None:
        envelope = json.loads(extended_body())
        envelope["choices"].append(copy.deepcopy(envelope["choices"][0]))
        self.assertCode(
            "provider_response_envelope_invalid",
            lambda: parse_chat_completion_compatible(canonical_json_bytes(envelope)),
        )

    def test_legal_optional_usage_does_not_bypass_finish_reason_validation(self) -> None:
        envelope = json.loads(extended_body())
        envelope["choices"][0]["finish_reason"] = "length"
        self.assertCode(
            "provider_response_envelope_invalid",
            lambda: parse_chat_completion_compatible(canonical_json_bytes(envelope)),
        )

    def test_legal_optional_usage_strips_reasoning_before_historical_parser(self) -> None:
        envelope = json.loads(extended_body())
        envelope["choices"][0]["message"]["reasoning_content"] = "hidden reasoning"
        parsed = parse_chat_completion_compatible(canonical_json_bytes(envelope))
        self.assertTrue(parsed["reasoning_content_removed"])
        self.assertNotIn("hidden reasoning", json.dumps(parsed, ensure_ascii=False))

    def test_legal_optional_usage_does_not_bypass_content_validation(self) -> None:
        envelope = json.loads(extended_body())
        envelope["choices"][0]["message"]["content"] = ""
        self.assertCode(
            "provider_response_envelope_invalid",
            lambda: parse_chat_completion_compatible(canonical_json_bytes(envelope)),
        )

    def test_legal_optional_usage_does_not_bypass_fingerprint_validation(self) -> None:
        envelope = json.loads(extended_body())
        envelope["system_fingerprint"] = None
        self.assertCode(
            "provider_response_envelope_invalid",
            lambda: parse_chat_completion_compatible(canonical_json_bytes(envelope)),
        )

    def test_safe_compatibility_fact_tamper_is_rejected_by_rederivation(self) -> None:
        source = usage_with_details()
        normalized = normalize_provider_usage(source)
        facts = copy.deepcopy(normalized["compatibility_facts"])
        facts["cached_tokens_matches_prompt_cache_hit_tokens"] = False
        self.assertCode(
            "tg07u_usage_compatibility_facts_invalid",
            lambda: validate_usage_compatibility_facts(facts, source_usage=source),
        )

    def test_normalized_usage_or_safe_fact_reseal_is_rejected(self) -> None:
        source = usage_with_details()
        normalized = normalize_provider_usage(source)
        altered = copy.deepcopy(normalized)
        altered["normalized_usage"]["completion_tokens"] = 201
        altered["normalized_usage"]["total_tokens"] = 1201
        self.assertCode(
            "tg07u_usage_normalization_invalid",
            lambda: validate_usage_normalization(altered, source_usage=source),
        )

    def test_sensitive_reflection_remains_rejected_by_old_response_boundary(self) -> None:
        canary = "SYNTHETIC-TG07U-CANARY"
        body = json_response(plan_result(), usage=usage_with_details(), response_id=canary)
        self.assertCode(
            "provider_sensitive_reflection",
            lambda: parse_chat_completion_compatible(body, sensitive_values=(canary,)),
        )


if __name__ == "__main__":
    unittest.main()
