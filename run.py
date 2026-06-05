import os
import sys
import re          # Michael Part 3: ADDED FOR SECURITY: Regular Expressions for input validation
import html        # Michael Part 3: ADDED FOR SECURITY: HTML escaping for XSS prevention
from importlib import reload
from flask import Flask, render_template, redirect, request, url_for, session
import time

# Needed for encoding to utf8
reload(sys)

# # Jake - Part 3, Idle Timeout
# # Time in Seconds (default = 600):
# IDLE_TIMEOUT = 600

# Jake - Part 3, Rate Limiting
MAX_REQUESTS = 10
REQUEST_WINDOW = 60
window_start = time.time()
request_count = 0

app = Flask(__name__)
app.secret_key = 'some_secret'
data = []


# ==========================================
# Michael Part 3: SECURE FEATURE 1: INPUT VALIDATION ENGINE
# ==========================================

def is_valid_username(username):
    """
    Michael Part 3: SECURITY PRINCIPLE: Input Validation (Allow-listing)
    Mitigates Path Traversal by ensuring only safe, alphanumeric characters 
    can be used in the username, which is later used to construct file paths.
    Enforces a length limit (3 to 15 characters) to prevent buffer/DoS issues.
    """
    if not username:
        return False
    # Michael Part 3: Regex strictly matches string start to end, 3-15 alphanumeric chars only.
    if not re.match(r'^[a-zA-Z0-9]{3,15}$', username):
        return False
    return True

def sanitize_input(text):
    """
    Michael Part 3: SECURITY PRINCIPLE: Data Sanitization (Output Encoding/Escaping)
    Strips leading/trailing whitespace and escapes HTML characters 
    to mitigate Cross-Site Scripting (XSS) when inputs are rendered.
    """
    if not text:
        return ""
    # Michael Part 3: Strip whitespace and safely escape HTML tags
    return html.escape(text.strip())

# Jake - Part 3, Idle Timeout
# Before any request that isn't on the homepage, highscores or timeout page.
# @app.before_request
# def check_idle():
#     if request.endpoint == 'index' or request.endpoint == 'highscores' or request.endpoint == 'timeout':
#         return

#     name = (request.view_args or {}).get('username')
#     if not name:
#         return
    
#     last_activity_key = "last_activity_" + name
#     last_activity = session.get(last_activity_key)

#     if last_activity:
#         time_since_activity = int(time.time()) - last_activity
#         if time_since_activity > IDLE_TIMEOUT:
#             cleanup(name)
#             session.clear()
#             return redirect(url_for('timeout'))
        
#     session[last_activity_key] = time.time()

# Jake - Part 3, Rate-Limiting helper
def is_overwhelmed():
    global request_count, window_start

    curr_time = time.time()
    if curr_time - window_start > REQUEST_WINDOW:
        request_count = 0
        window_start = curr_time

    if request_count > MAX_REQUESTS:
        return True
    
    return False
    

def write_to_file(filename, data):
    with open(filename, "a+") as file:
        file.writelines(data)


#This is where the riddles live
def riddle():
    riddles = []
    with open("data/-riddles.txt", "r") as e:
        lines = e.read().splitlines()
    for line in lines:
        riddles.append(line)
    return riddles


# This is where the answers for the riddles live
def riddle_answers():
    answers = []
    with open("data/-answers.txt", "r") as e:
        lines = e.read().splitlines()
    for line in lines:
        answers.append(line)
    return answers


# Clear functions for wrong answers and score
def clear_guesses(username):
    with open("data/user-" + username + "-guesses.txt", "w"):
        return

def clear_score(username):
    with open("data/user-" + username + "-score.txt", "w"):
        return

# Jake - Part 3, File Deletion
def cleanup(username):
    if os.path.exists("data/user-" + username + "-guesses.txt"):
        os.remove("data/user-" + username + "-guesses.txt")
    if os.path.exists("data/user-" + username + "-score.txt"):
        os.remove("data/user-" + username + "-score.txt")

# Wrong answer handling
def store_all_attempts(username):
    attempts = []
    if os.path.exists("data/user-" + username + "-guesses.txt"):
        with open("data/user-" + username + "-guesses.txt", "r") as incorrect_attempts:
            attempts = incorrect_attempts.readlines()
    return attempts

def num_of_attempts():
    attempts = store_all_attempts(username)
    return len(attempts)

def attempts_remaining():
    remaining_attempts = 3 - num_of_attempts()
    return remaining_attempts


# Score gets lower the more attempts used
def add_to_score():
    round_score = 4 - num_of_attempts()
    return round_score

#Adds all the scores from all riddles to make final score
def end_score(username):
    with open("data/user-" + username + "-score.txt", "r") as numbers_file:
        total = 0
        for line in numbers_file:
            try:
                total += int(line)
            except ValueError:
                pass
    return total

#Add final score to highscore list after the last riddle
def final_score(username):
    score = str(end_score(username))

    if username != "" and score != "":
        with open("data/-highscores.txt", "a") as file:
                file.writelines(username + "\n")
                file.writelines(score + "\n")
    else:
        return

#Used to retrieve scores from highscore file for use on highscore page
def get_scores():
    usernames = []
    scores = []

    with open("data/-highscores.txt", "r") as file:
        lines = file.read().splitlines()
    # Separates usernames and scores
    for i, text in enumerate(lines):
        if i%2 ==0:
            usernames.append(text)
        else:
            scores.append(text)
    # Sorts and zips all the highscore info up for use on highscore page
    usernames_and_scores = sorted(zip(usernames, scores), key=lambda x: x[1], reverse=True)
    return usernames_and_scores


# HOMEPAGE
@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        global username
        
        # Michael Part 3: SECURE IMPLEMENTATION: Capture, sanitize, and validate input
        raw_username = request.form['username'].lower()
        username = sanitize_input(raw_username)
        
        # Michael Part 3: Check against our strict allow-list before proceeding
        if not is_valid_username(username):
            # Michael Part 3: Return to home page if input is malicious or invalid
            error_msg = "Security Error: Username must be 3-15 alphanumeric characters only."
            return render_template("index.html", page_title="Home", username="", error=error_msg)

        return redirect(url_for('user', username=username))
    return render_template("index.html", page_title="Home")


# USER WELCOME PAGE
@app.route('/<username>', methods=["GET", "POST"])
def user(username):

    if request.method =="POST":
        return redirect(url_for('game', username=username))

    return render_template("welcome.html",
                            username=username)


# GAME PAGE
@app.route('/<username>/game', methods=["GET", "POST"])
def game(username):
    global request_count

    # Jake, Rate-Limiting
    # Shows the toomanyrequests.html page and informs of a 429
    request_count+=1
    if is_overwhelmed():
        return render_template("toomanyrequests.html"), 429
    # Jake - Part 3, File Deletion
    # If files don't exist (due to a delete from the end of a prior session), create them.
    # Moved from user() so that they're always made right before a new game.
    if not os.path.exists("data/user-" + username + "-score.txt"):
        open("data/user-" + username + "-score.txt", 'a').close()
    if not os.path.exists("data/user-" + username + "-guesses.txt"):
        open("data/user-" + username + "-guesses.txt", 'a').close()

    
    remaining_attempts = 3
    riddles = riddle()
    riddle_index = 0
    answers = riddle_answers()
    score = 0

    if request.method == "POST":

        riddle_index = int(request.form["riddle_index"])
        
        # Michael Part 3: SECURE IMPLEMENTATION: Sanitize the riddle answer to prevent XSS
        raw_response = request.form["answer"].title()
        user_response = sanitize_input(raw_response)

        write_to_file("data/user-" + username + "-guesses.txt", user_response + "\n")

        # Compare the user's answer to the correct answer of the riddle
        if answers[riddle_index] == user_response:
            # Correct answer
            if riddle_index < 9:
                # If riddle number is less than 10 & answer is correct: add score, clear wrong answers file and go to next riddle
                write_to_file("data/user-" + username + "-score.txt", str(add_to_score()) + "\n")
                clear_guesses(username)
                riddle_index += 1
            else:
                # If right answer on LAST riddle: add score, submit score to highscore file and redirect to congrats page
                write_to_file("data/user-" + username + "-score.txt", str(add_to_score()) + "\n")
                final_score(username)
                return redirect(url_for('congrats', username=username, score=end_score(username)))

        else:
            # Incorrect answer
            if attempts_remaining() > 0:
                # if answer was wrong and more than 0 attempts remaining, reload current riddle
                riddle_index = riddle_index
            else:
                # If all attempts are used up, redirect to Gameover page
                return redirect(url_for('gameover', username=username))

    return render_template("game.html",
                            username=username, riddle_index=riddle_index, riddles=riddles,
                            answers=answers, attempts=store_all_attempts(username), remaining_attempts=attempts_remaining(), score=end_score(username))


# GAMEOVER PAGE
@app.route('/<username>/gameover', methods=["GET", "POST"])
def gameover(username):

    # Jake - bug fix
    if request.method =="POST":
        return redirect(url_for('game', username=username))
    
    # Jake - Part 3, File Deletion
    cleanup(username)

    rem_attempts = 3
    riddles = riddle()
    riddle_index = 0
    answers = riddle_answers()
    score = 0



    return render_template("gameover.html",
                            username=username)


# FINISH PAGE
@app.route('/<username>/congratulations', methods=["GET", "POST"])
def congrats(username):

    # Jake - Part 3, File Deletion
    winning_score = end_score(username)
    cleanup(username)


    if request.method =="POST":
        usernames_and_scores = get_scores()
        return redirect(url_for('highscores', usernames_and_scores=usernames_and_scores))

    return render_template("congratulations.html",
                            username=username, score=winning_score)


# HIGHSCORE PAGE
@app.route('/highscores')
def highscores():

    usernames_and_scores = get_scores()

    return render_template("highscores.html", page_title="Highscores", usernames_and_scores=usernames_and_scores)

# # Jake - Timeout Page
# @app.route('/timeout', methods=["GET", "POST"])
# def timeout():
#     if request.method == "POST":
#         return redirect(url_for('index'))
#     return render_template("timeout.html")


if __name__ == '__main__':
    ip = "127.0.0.1"
    port = 8000
    app.run(host=ip,
            port=port,
            debug=True)