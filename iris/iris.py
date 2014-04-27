# built-in
import time
import json
import logging
from datetime import datetime
from sqlite3 import dbapi2 as sqlite3
from urlparse import urlparse, parse_qs

# third party
from flask import Flask, render_template, request, g, flash, redirect, url_for, abort
import requests

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE='/tmp/iris.db'
))
#app.config.from_envvar('SETTINGS', silent=True)
app.config.from_pyfile('config')

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

def format_timestamp(sqlite_date):
    if sqlite_date:
        return datetime.fromtimestamp(int(sqlite_date))
    else:
        return ""

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/add', methods=['POST'])
def add_entry():
    # validating the url before allowing anything to be submitted
    url = urlparse(request.form['url'])
    if url.hostname:
        db = get_db()
        # check to see if the url has been posted yet
        cur = db.execute('SELECT * FROM entries WHERE url = ?', [request.form['url']])
        db_entries = cur.fetchall()
        if len(db_entries) > 0:
            return redirect(url_for('index'))
        if url.hostname == 'www.youtube.com' or url.hostname.endswith('bandcamp.com') or \
                url.hostname.endswith('soundcloud.com'):
            # validating bandcamp url
            if url.hostname.endswith('bandcamp.com'):
                url = derive_bandcamp_url(url.geturl())
                if not url:
                    return redirect(url_for('index'))
            # validating soundcloud url
            if url.hostname.endswith('soundcloud.com'):
                url = derive_soundcloud_url(url.geturl())
                if not url:
                    return redirect(url_for('index'))
            cur = db.execute(
                'INSERT INTO entries (title, url, artist, created_at) VALUES (?, ?, ?, ?)',
                [request.form['title'], url.geturl(),
                 request.form['artist'], time.time()])
            db.commit()
            entry_id = cur.lastrowid
            # adding tagging to the entry, using crappy ip based validation
            # this is for the nginx proxied case, could be spoofed
            if not request.headers.getlist("X-Real-IP"):
                ip = request.remote_addr
            else:
                ip = request.headers.getlist("X-Real-IP")[0]
            if 'ALLOWED_IPS' in app.config and ip in app.config['ALLOWED_IPS']:
                # user can add new tags
                for tag_name in request.form['tags'].split(','):
                    db.execute('INSERT INTO tags (name, entry_id) VALUES (?, ?)',
                               [tag_name, entry_id])
                    db.commit()
            else:
                # user can only add existing tags
                cur = db.execute('SELECT DISTINCT name FROM tags')
                current_tags = [t[0] for t in cur.fetchall()]
                for tag_name in request.form['tags'].split(','):
                    if tag_name in current_tags:
                        db.execute('INSERT INTO tags (name, entry_id) VALUES (?, ?)',
                                   [tag_name, entry_id])
                        db.commit()
            # update the main list of videos with the secret header
            # if it exists in the config file, this is for nginx
            if 'SECRET_HEADER' and 'SITE_URL' in app.config:
                r = requests.get(app.config['SITE_URL'],
                                 headers={app.config['SECRET_HEADER']:1})
                if r.status_code != requests.codes.ok:
                    abort(500)
            if 'HIPCHAT_ROOM_ID' and 'HIPCHAT_ROOM_TOKEN' in app.config:
                headers = {'content-type': 'application/json'}
                params = {'auth_token':app.config['HIPCHAT_ROOM_TOKEN']}
                payload = {'message':request.form['url'],'notify':True,'message_format':'text'}
                r = requests.post('https://api.hipchat.com/v2/room/%s/notification' % app.config['HIPCHAT_ROOM_ID'],
                                  params=params,data=json.dumps(payload),headers=headers)
        flash('New entry was successfully queued.')

    return redirect(url_for('index'))


if __name__ == "__main__":
    if 'LOG_FILE' in app.config:
        logging.basicConfig(filename=app.config['LOG_FILE'], level=logging.INFO)
    app.run(port=6000,debug=True)
    # for prod with gunicorn the line below is fine
    # app.run()
