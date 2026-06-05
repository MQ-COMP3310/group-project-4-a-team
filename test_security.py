import os
import unittest
from unittest.mock import patch
import pytest
import time
from random import randint
# Import the security functions we just built in run.py
import run
from run import is_valid_username, sanitize_input, app, cleanup, is_overwhelmed

# Mikey - Part 3 Task 9:
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

# Jake - Part 3 Task 9
# Setup for the rate-limiting tests.
@pytest.fixture
def client():
    # Sets up a test Flask client.
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = app.secret_key
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        with app.app_context():
            yield client

# Called after tests automatically, prevents tests on the rate-limit from bleeding into other test windows.
@pytest.fixture(autouse=True)
def reset_rate_limit():
    run.request_count = 0
    run.window_start = time.time()

# If the test creates any files, this deletes them after use.
@pytest.fixture(autouse=True)
def cleanup_test_files():
    yield
    files = ["data/user-testuser-score.txt", "data/user-testuser-guesses.txt"]
    for file in files:
        if os.path.exists(file):
            os.remove(file)


# Jake - Task 9, File Deletion
    # Security Requirement: When a session ends, either via gameover or congratulations, user data is deleted.
    # Note: was going to include an idle timeout, but that is beyond the scope of file deletion.
# Note that the file deletion tests use patch(), as we know that os.remove() works, so we just need to confirm that cleanup() calls os.remove("data/user-testuser-guesses.txt"), etc. 
class TestFileDeletion():

    ## Testing cleanup()'s accuracy:
    # Ensuring that cleanup() deletes the score.txt file
    def test_cleanup_deletes_score_file(self):
        with patch("run.os.path.exists", return_value=True), patch("run.os.remove") as mock_remove:
            cleanup("testuser")
            mock_remove.assert_any_call("data/user-testuser-score.txt")

    # Ensuring that cleanup() deletes the guesses.txt file
    def test_cleanup_deletes_guesses_file(self):
        with patch("run.os.path.exists", return_value=True), patch("run.os.remove") as mock_remove:
            cleanup("testuser")
            mock_remove.assert_any_call("data/user-testuser-guesses.txt")
    
    # If there are no files to delete, ensure that cleanup() doesn't call os.remove() at all.
    def test_cleanup_no_files(self):
        with patch("run.os.path.exists", return_value=False), patch("run.os.remove") as mock_remove:
            cleanup("testuser")
            mock_remove.assert_not_called()
    
    ## Testing that calls to cleanup() are made at correct times.
    # If the URL for the gameover route is visited, ensure that cleanup() is called with correct arg.
    # Using a fake cleanup() function, as the successful implementation of cleanup() is not this test's aim. If cleanup() fails, this test will be unaffected.
    def test_gameover_calls_cleanup(self, client):
        with patch("run.cleanup") as mock_cleanup:
            client.get("/testuser/gameover")
            mock_cleanup.assert_called_once_with("testuser")
    
    # If the URL for the congratulations route is visited (and that all riddles have been passed), ensure that cleanup() is called with correct arg.
    def test_congrats_calls_cleanup(self, client):
        with patch("run.cleanup") as mock_cleanup, patch("run.end_score", return_value=10):
            client.get("/testuser/congratulations")
            mock_cleanup.assert_called_once_with("testuser")

# Jake - Part 3 Task 9, Rate Limiting
    # Security Requirement: The server must return the HTTP 429 error once the request threshold (MAX_REQUESTS) is met within the time limit (REQUEST_WINDOW).
class TestRateLimiting():
    # Testing is_overwhelmed()
    # Ensures that when request_count hits MAX_REQUESTS, is_overwhelmed returns True (real).
    def test_is_overwhelmed_returns_true_at_threshold(self):
        run.request_count = run.MAX_REQUESTS + 1
        run.window_start = time.time()
        assert is_overwhelmed() is True

    # Ensures that for 5 values of requests that are below the threshold, is_overwhelmed() returns False.
    def test_is_overwhelmed_returns_false_below_threshold(self):
        if run.MAX_REQUESTS <= 0: pytest.skip("Invalid MAX_REQUESTS value to test is_overwhelmed().")
    
        test_count = 5
        for _ in range(test_count):
            run.request_count = randint(0, run.MAX_REQUESTS - 1)
            run.window_start = time.time()
            assert is_overwhelmed() is False
    

    # Ensures that requests under the limit (MAX_REQUESTS) are successful.
    def test_accepts_requests_under_limit(self, client):
        run.request_count = 0
        run.username = "testuser"
        with patch("run.store_all_attempts", return_value=[]), patch("run.end_score", return_value=0):
            response = client.get("/testuser/game")
            assert response.status_code != 429

    # Ensures that requests over the limit are denied.
    def test_denies_requests_over_limit(self, client):
        run.request_count = run.MAX_REQUESTS
        run.window_start = time.time()

        with patch("run.os.path.exists", return_value=True):
            response = client.get("/testuser/game")
            assert response.status_code == 429
    
    # Ensures that the time window expiring resets the request_count, new requests should be accepted.
    def test_window_reset_allows_requests(self, client):
        run.request_count = run.MAX_REQUESTS
        run.window_start = time.time() - (run.REQUEST_WINDOW + 1)
        run.username = "testuser"

        with patch("run.store_all_attempts", return_value=[]), patch("run.end_score", return_value=0):
            response = client.get("/testuser/game")
            assert response.status_code != 429

if __name__ == '__main__':
    unittest.main()