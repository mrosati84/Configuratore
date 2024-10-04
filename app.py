import os
from flask import Flask, session, request, redirect
from flask import render_template
from flask_session import Session
import spotipy
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'

Session(app)


@app.route('/')
def index():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope='user-read-currently-playing playlist-modify-private user-top-read',
        cache_handler=cache_handler,
        show_dialog=True)

    if request.args.get("code"):
        # Step 2. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 1. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return f'<h2><a href="{auth_url}">Sign in</a></h2>'

    # Step 3. Signed in, display data
    return render_template("index.html", me=me(), top_genres=get_top_genres())


@app.route('/sign_out')
def sign_out():
    session.pop("token_info", None)
    return redirect('/')


def me():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    return spotify.me()['display_name']


def get_top_genres(time_range='long_term', limit=50):
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    top_artists = spotify.current_user_top_artists(time_range=time_range, limit=limit)
    all_genres = [genre for artist in top_artists['items'] for genre in artist['genres']]
    genre_counts = Counter(all_genres)
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)

    return [genre[0] for genre in top_genres][:5]


if __name__ == '__main__':
    app.run(
        debug=os.environ.get("DEBUG") or False,
        threaded=True,
        port=int(os.environ.get("PORT", os.environ.get("SPOTIPY_REDIRECT_URI", 8080).split(":")[-1]))
    )
