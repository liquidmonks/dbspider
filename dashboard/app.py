from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import os
import json  # Moved to top

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


if __name__ == '__main__':
    app.run(debug=True)