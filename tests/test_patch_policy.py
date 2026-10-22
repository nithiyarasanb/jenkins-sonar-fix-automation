import unittest
from pathlib import Path

class PatchPolicyTests(unittest.TestCase):
    def test_policy_has_no_default_transformations(self):
        import json
        policy = json.loads(Path("config/remediation-policy.json").read_text())
        self.assertEqual(policy["deterministic_rules"], {})

    def test_allowed_extensions_are_explicit(self):
        import json
        policy = json.loads(Path("config/remediation-policy.json").read_text())
        self.assertIn(".py", policy["allowed_extensions"])
        self.assertNotIn(".pem", policy["allowed_extensions"])

if __name__ == "__main__":
    unittest.main()
