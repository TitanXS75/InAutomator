"""
tests/test_email.py
Unit tests for email composition and duplicate checking logic.
"""

import unittest
import os
import tempfile

# Patch env before importing modules that read .env at import time
os.environ.setdefault("LINKEDIN_EMAIL", "test@test.com")
os.environ.setdefault("LINKEDIN_PASSWORD", "test")
os.environ.setdefault("GMAIL_ADDRESS", "sender@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "testpass")
os.environ.setdefault("SENDER_NAME", "Test User")


class TestEmailComposer(unittest.TestCase):

    def setUp(self):
        from modules.email_composer import EmailComposer
        self.composer = EmailComposer()
        self.sample_recruiter = {
            "name":    "Priya Sharma",
            "email":   "priya@company.com",
            "company": "TechCorp",
            "keyword": "Python Developer",
        }

    def test_compose_returns_dict(self):
        result = self.composer.compose(self.sample_recruiter)
        self.assertIsInstance(result, dict)

    def test_compose_has_required_keys(self):
        result = self.composer.compose(self.sample_recruiter)
        for key in ["to", "subject", "body"]:
            self.assertIn(key, result)

    def test_to_field_is_correct_email(self):
        result = self.composer.compose(self.sample_recruiter)
        self.assertEqual(result["to"], "priya@company.com")

    def test_body_contains_recruiter_first_name(self):
        result = self.composer.compose(self.sample_recruiter)
        self.assertIn("Priya", result["body"])

    def test_body_contains_keyword(self):
        result = self.composer.compose(self.sample_recruiter)
        self.assertIn("Python Developer", result["body"])

    def test_subject_contains_keyword(self):
        result = self.composer.compose(self.sample_recruiter)
        self.assertIn("Python Developer", result["subject"])

    def test_first_name_extraction(self):
        from modules.email_composer import EmailComposer
        self.assertEqual(EmailComposer._get_first_name("John Doe"), "John")
        self.assertEqual(EmailComposer._get_first_name("Alice"), "Alice")
        self.assertEqual(EmailComposer._get_first_name(""), "Recruiter")


class TestDuplicateChecker(unittest.TestCase):

    def setUp(self):
        # Use a temp file as the sent log
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        )
        self.tmp.write("email,sent_at,status\n")
        self.tmp.write("old@example.com,2024-01-01T10:00:00,sent\n")
        self.tmp.close()

        # Patch the SENT_LOG_CSV path
        import config.settings as s
        self._orig = s.SENT_LOG_CSV
        s.SENT_LOG_CSV = self.tmp.name

    def tearDown(self):
        import config.settings as s
        s.SENT_LOG_CSV = self._orig
        os.unlink(self.tmp.name)

    def test_already_sent_true_for_known_email(self):
        from utils.duplicate_checker import DuplicateChecker
        checker = DuplicateChecker()
        self.assertTrue(checker.already_sent("old@example.com"))

    def test_already_sent_false_for_new_email(self):
        from utils.duplicate_checker import DuplicateChecker
        checker = DuplicateChecker()
        self.assertFalse(checker.already_sent("new@example.com"))

    def test_mark_sent_prevents_resend(self):
        from utils.duplicate_checker import DuplicateChecker
        checker = DuplicateChecker()
        checker.mark_sent("brand.new@example.com")
        self.assertTrue(checker.already_sent("brand.new@example.com"))


if __name__ == "__main__":
    unittest.main()
