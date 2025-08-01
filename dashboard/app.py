from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import os
import json  # Moved to top
import subprocess  # For bot controls

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or 'fallback_secret'  # Import os at top if not

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password':  # Hardcoded; secure later
            user = User(1)
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials')
    return render_template('login.html')


@app.route('/')
@login_required
def home():
    return render_template('index.html', title='DBSpider Dashboard')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/config', methods=['GET', 'POST'])
@login_required
def edit_config():
    config_file = '../settings.json'  # Path relative to dashboard (adjust if needed)
    if request.method == 'POST':
        # Save updated config
        updated_config = {
            "guild_id": request.form['guild_id'],
            "service_status_channels": [int(ch) for ch in request.form['service_status_channels'].split(',') if
                                        ch.strip()],
            "down_stream_channels": [int(ch) for ch in request.form['down_stream_channels'].split(',') if ch.strip()],
            "event_update_channels": [int(ch) for ch in request.form['event_update_channels'].split(',') if ch.strip()],
            "find_cmd_channels": [int(ch) for ch in request.form['find_cmd_channels'].split(',') if ch.strip()],
            "other_settings": {
                "scoreboard_bot_id": int(request.form['scoreboard_bot_id'])
            }
        }
        with open(config_file, 'w') as f:
            json.dump(updated_config, f, indent=4)
        flash('Config saved successfully!')
        return redirect(url_for('home'))

    # Load current config for form
    try:
        with open(config_file, 'r') as f:
            current_config = json.load(f)
    except FileNotFoundError:
        current_config = {}

    return render_template('edit_config.html', config=current_config)


bot_process = None  # Global to track bot process


@app.route('/bot_control', methods=['POST'])
@login_required
def bot_control():
    global bot_process
    action = request.form['action']
    if action == 'start':
        if not bot_process or bot_process.poll() is not None:
            bot_process = subprocess.Popen(['python', '../bot.py'])
            flash('Bot started!')
        else:
            flash('Bot is already running.')
    elif action == 'stop':
        if bot_process and bot_process.poll() is None:
            bot_process.terminate()
            flash('Bot stopped!')
        else:
            flash('Bot is not running.')
    elif action == 'restart':
        if bot_process and bot_process.poll() is None:
            bot_process.terminate()
        bot_process = subprocess.Popen(['python', '../bot.py'])
        flash('Bot restarted!')
    return redirect(url_for('home'))


@app.route('/logs')
@login_required
def logs():
    log_file = '../data/bot.log'  # Path to bot log file (adjust if needed)
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()[-100:]  # Last 100 lines
            log_content = ''.join(lines)
    except FileNotFoundError:
        log_content = 'Log file not found.'
    return render_template('logs.html', log_content=log_content)


if __name__ == '__main__':
    app.run(debug=True)