import os
import sys
import bcrypt      # Tadhg Part 2: bcrypt is one of the best hashing methods for python
import re          # Michael Part 3: ADDED FOR SECURITY: Regular Expressions for input validation
import html        # Michael Part 3: ADDED FOR SECURITY: HTML escaping for XSS prevention
from importlib import reload
from flask import Flask, render_template, redirect, request, url_for, session, abort
import time
from flask import session #Tadhg Part 2: Uses flasks session to authenticates users session

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
#changed secret_key to make it not hardcoded
app.secret_key = os.urandom(32)
data = []


# ==========================================
# Michael Part 3: SECURE FEATURE 1: INPUT VALIDATION ENGINE
# ==========================================

def is_valid_username(username):
    
    if not username:
        return False
    # Michael Part 3: Regex strictly matches string start to end, 3-15 alphanumeric chars only.
    if not re.match(r'^[a-zA-Z0-9]{3,15}$', username):
        return False
    return True

def sanitise_input(text):
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
    

#Tadhg Part 2: I chose to use a function for the register and login function instead of including them in the Flask endpoints, as that was seemed easier to me
def register(username, password):

    #SECURITY PRINCIPLE: Strong password policy 
    #Enforces passwords length requirements 
    if len(password) < 8: 
        return False
    
    with open("data/users.txt", "r") as file: 
        for line in file: 
            stored_username = line.split(",")[0]
            #Prevents duplicate usernames
            if stored_username == username: 
                return False
    
    #SECURITY PRINCIPLE: Password confidentiality
    #Passwords are not stored in plaintext, bcrypt hashing is used to make them unreadable for humans
    password_hash = bcrypt.hashpw( password.encode('utf-8'),bcrypt.gensalt())
    with open("data/users.txt", "a") as file: 
        file.write( f"{username},{password_hash.decode()},user\n")

    return True

def login(username, password):
    with open("data/users.txt", "r") as file:
        for line in file:
            stored_username, stored_hash = line.strip().split(",")

            if stored_username == username :
                #SECURITY PRINCIPLE: Intergrity-repudation
                #bcrypt checkpw is constant, meaning there are no timing based attacks
                if bcrypt.checkpw(
                    password.encode("utf-8"),
                    stored_hash.encode("utf-8")
                ):
                    #SECURITY PRINCIPLE: Intergrity and Non-repudation
                    #Authentication status stored in session
                    session["username"] = username
                    return True

    return False


#helper function to test if user is logged in when visiting protected pages
def login_required(username):

    # User must be logged in
    if "username" not in session:
        return redirect(url_for("index"))

    # User can only access their own pages
    if session["username"] != username :
        abort(403)

    return None

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

def num_of_attempts(username):
    attempts = store_all_attempts(username)
    return len(attempts)

def attempts_remaining(username):
    remaining_attempts = 3 - num_of_attempts(username)
    return remaining_attempts


# Score gets lower the more attempts used
def add_to_score(username):
    round_score = 4 - num_of_attempts(username)
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
        
        
        # Michael Part 3: SECURE IMPLEMENTATION: Capture, sanitise, and validate input
        raw_username = request.form['username'].lower()
        username = sanitise_input(raw_username)
        
        # Michael Part 3: Check against our strict allow-list before proceeding
        if not is_valid_username(username):
            # Michael Part 3: Return to home page if input is malicious or invalid
            error_msg = "Security Error: Username must be 3-15 alphanumeric characters only."
            return render_template("index.html", page_title="Home", username="", error=error_msg)

        return redirect(url_for('user', username=username))
    return render_template("index.html", page_title="Home")


#Tadhg Part 2: adding register and login pages
@app.route('/register', methods=["GET", "POST"])
def register_page():
    username = request.form["username"]
    password = request.form["password"]

    #Reusing Michael's username validity test to avoid improper inptus
    if not is_valid_username(username):
        return "Invalid username", 400

    if register(username, password):
        return redirect(url_for("login_page"))

    return "Registration failed", 400

@app.route('/login', methods=["GET", "POST"])
def login_page():
    username = request.form["username"]
    password = request.form["password"]

    if login(username, password):
       return redirect(url_for("user", username=username))

    return redirect(url_for("index"))

# USER WELCOME PAGE
@app.route('/<username>', methods=["GET", "POST"])
def user(username):
    auth_check = login_required(username)
    if auth_check:
        return auth_check
    # Create a User Specific File for Score Keeping etc.
    open("data/user-" + username + "-score.txt", 'a').close()
    clear_score(username)
    open("data/user-" + username + "-guesses.txt", 'a').close()
    clear_guesses(username)

    if request.method =="POST":
        return redirect(url_for('game', username=username))

    return render_template("welcome.html",
                            username=username)


# GAME PAGE
@app.route('/<username>/game', methods=["GET", "POST"])
def game(username):
    global request_count
    auth_check = login_required(username)
    if auth_check:
        return auth_check

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
        
        # Michael Part 3: SECURE IMPLEMENTATION: sanitise the riddle answer to prevent XSS
        raw_response = request.form["answer"].title()
        user_response = sanitise_input(raw_response)

        write_to_file("data/user-" + username + "-guesses.txt", user_response + "\n")

        # Compare the user's answer to the correct answer of the riddle
        if answers[riddle_index] == user_response:
            # Correct answer
            if riddle_index < 9:
                # If riddle number is less than 10 & answer is correct: add score, clear wrong answers file and go to next riddle
                write_to_file("data/user-" + username + "-score.txt", str(add_to_score(username)) + "\n")
                clear_guesses(username)
                riddle_index += 1
            else:
                # If right answer on LAST riddle: add score, submit score to highscore file and redirect to congrats page
                write_to_file("data/user-" + username + "-score.txt", str(add_to_score(username)) + "\n")
                final_score(username)
                return redirect(url_for('congrats', username=username, score=end_score(username)))

        else:
            # Incorrect answer
            if attempts_remaining(username) > 0:
                # if answer was wrong and more than 0 attempts remaining, reload current riddle
                riddle_index = riddle_index
            else:
                # If all attempts are used up, redirect to Gameover page
                return redirect(url_for('gameover', username=username))

    return render_template("game.html",
                            username=username, riddle_index=riddle_index, riddles=riddles,
                            answers=answers, attempts=store_all_attempts(username), remaining_attempts=attempts_remaining(username), score=end_score(username))


# GAMEOVER PAGE
@app.route('/<username>/gameover', methods=["GET", "POST"])
def gameover(username):

    auth_check = login_required(username)
    if auth_check:
        return auth_check

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

    auth_check = login_required(username)
    if auth_check:
        return auth_check

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

#SECURITY PRINCIPLE: Integrity 
# Logout is set as post only to avoid CSRF attacks
@app.route('/logout', methods=["POST"])
def logout():
    #session invalidated on logout
    session.clear()
    return redirect(url_for('index'))

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