import unittest
# Import the security functions we just built in run.py
from run import is_valid_username, sanitize_input

class TestInputValidation(unittest.TestCase):

    def test_valid_username(self):
        # A normal username should pass
        self.assertTrue(is_valid_username("player1"))
        self.assertTrue(is_valid_username("bob"))

    def test_path_traversal_blocked(self):
        # SECURITY TEST: Ensure directory traversal attempts are rejected
        malicious_input = "../../../etc/passwd"
        self.assertFalse(is_valid_username(malicious_input))

    def test_xss_username_blocked(self):
        # SECURITY TEST: Ensure script tags in usernames are rejected
        malicious_input = "<script>alert(1)</script>"
        self.assertFalse(is_valid_username(malicious_input))

    def test_username_length_limits(self):
        # SECURITY TEST: Ensure boundary limits are enforced
        self.assertFalse(is_valid_username("ab")) # Too short (under 3)
        self.assertFalse(is_valid_username("thisusernameiswaytoolong")) # Too long (over 15)

    def test_input_sanitization(self):
        # SECURITY TEST: Ensure HTML is safely escaped
        raw_input = "  <script>   "
        sanitized = sanitize_input(raw_input)
        self.assertEqual(sanitized, "&lt;script&gt;")

if __name__ == '__main__':
    unittest.main()