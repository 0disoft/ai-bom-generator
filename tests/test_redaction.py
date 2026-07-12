from __future__ import annotations

import unittest

from ai_bom_generator.security.redaction import Redactor


class RedactionTests(unittest.TestCase):
    def test_strict_redaction_masks_sensitive_keys_regardless_of_value_shape(self) -> None:
        redactor = Redactor("strict")
        payload = {
            "password": "ordinary-looking-value",
            "hf_token": "not-provider-shaped",
            "aws_secret_access_key": "also-ordinary-looking",
            "metadata": {"authorization": "Plain local-dev-token"},
            "safe_name": "public-model",
        }

        redacted = redactor.redact_json(payload)

        self.assertEqual(redacted["password"], "REDACTED")
        self.assertEqual(redacted["hf_token"], "REDACTED")
        self.assertEqual(redacted["aws_secret_access_key"], "REDACTED")
        self.assertEqual(redacted["metadata"]["authorization"], "REDACTED")
        self.assertEqual(redacted["safe_name"], "public-model")

    def test_strict_redaction_masks_provider_token_shapes(self) -> None:
        redactor = Redactor("strict")
        value = (
            "hf_abcdefghijklmnopqrstuvwxyz123456 "
            "ya29.abcdefghijklmnopqrstuvwxyz123456 "
            "password=ordinary-looking-value "
            "credential=plain-value"
        )

        redacted = redactor.redact_text(value)

        self.assertNotIn("hf_abcdefghijklmnopqrstuvwxyz123456", redacted)
        self.assertNotIn("ya29.abcdefghijklmnopqrstuvwxyz123456", redacted)
        self.assertNotIn("ordinary-looking-value", redacted)
        self.assertNotIn("plain-value", redacted)
        self.assertIn("REDACTED", redacted)

    def test_strict_redaction_masks_userinfo_for_hierarchical_uris(self) -> None:
        redactor = Redactor("strict")

        for value in (
            "postgresql://alice:supersecret@db.internal/app",
            "mysql://user:p%40ss@db.internal/app",
            "redis://default:short@cache.internal/0",
            "ssh://git:credential@[2001:db8::1]/repo",
        ):
            with self.subTest(value=value):
                redacted = redactor.redact_text(value)
                self.assertNotIn(value.split("://", 1)[1].split("@", 1)[0], redacted)
                self.assertIn("://REDACTED", redacted)

        self.assertEqual(
            redactor.redact_text("postgresql://db.internal/app"),
            "postgresql://db.internal/app",
        )

    def test_redaction_off_preserves_sensitive_key_values(self) -> None:
        redactor = Redactor("off")

        redacted = redactor.redact_json({"password": "ordinary-looking-value"})

        self.assertEqual(redacted["password"], "ordinary-looking-value")


if __name__ == "__main__":
    unittest.main()
