from urllib.parse import quote
import requests
import json
import time
from spotipy.oauth2 import SpotifyOAuth
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, Response
)


bp = Blueprint('auth', __name__)


#  Client Keys
CLIENT = json.load(open('conf.json', 'r+'))
CLIENT_ID = CLIENT['id']
CLIENT_SECRET = CLIENT['secret']

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 80
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "user-top-read playlist-modify-public playlist-modify-private"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

sp_oauth = SpotifyOAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, state=None, scope=SCOPE)

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": 'user-top-read',
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}


@bp.route("/login")
def login():
    template = 'layout.html'
    name = "login page"
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)


@bp.route('/logout')
def logout():
    from .wordcloud import home

    session.clear()
    return home()


@bp.route("/callback/q")
def callback():
    from .wordcloud import home
    # Auth Step 4: Requests refresh and access tokens
    if 'task_id' in session:
        session.pop('task_id')
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }

    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)
    
    if 'access_token' not in session:
        # Auth Step 5: Tokens are Returned to Application
        response_data = json.loads(post_request.text)
        access_token = response_data["access_token"]
        refresh_token = response_data["refresh_token"]
        token_type = response_data["token_type"]
        expires_at = int(time.time()) + response_data["expires_in"]


        # Auth Step 6: Use the access token to access Spotify API
        auth_header = {"Authorization": "Bearer {}".format(access_token)}

        user_endpoint = "{}/me".format(SPOTIFY_API_URL)
        profile_response = requests.get(user_endpoint, headers=auth_header)
        profile_data = json.loads(profile_response.text)

    
        session['auth_header'] = auth_header
        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session['expires_at'] = expires_at
        session['user_data'] = profile_data
        user_data = session['user_data']
        session['username'] = user_data['display_name']

    return redirect(url_for("wordcloud.home"))


def renew_access_token():
    if 'refresh_token' in session:
        refresh_token = session['refresh_token']
        token_info = sp_oauth.refresh_access_token(refresh_token=refresh_token)
        session['access_token'] = token_info['access_token']
        session['expires_at'] =  int(time.time()) + token_info['expires_in']
        if not 'refresh_token' in token_info:
                session['refresh_token'] = refresh_token
        else:
            session['refresh_token'] = token_info['refresh_token']
        
    else:
        return login()
    

def is_token_expired():
    if 'expires_at' in session:
        now = int(time.time())
        return session['expires_at'] - now < 60
    else:
        return True



@bp.errorhandler(401)
def custom_401(error):
    return login()
    # return Response('<Why access is denied string goes here...>', 401, {'WWW-Authenticate':'Basic realm="Login Required"'})



# not meant to be deployed, just didnt want to get rid of the logic just yet
def getplaylist():
    # Get user playlist data
    if 'auth_header' in session:
        auth_header = session['auth_header']

        user_endpoint = "{}/me".format(SPOTIFY_API_URL)
        profile_response = requests.get(user_endpoint, headers=auth_header)
        profile_data = json.loads(profile_response.text)

        playlist_api_endpoint = "{}/playlists".format(profile_data["href"])
        playlists_response = requests.get(playlist_api_endpoint, headers=auth_header)
        playlist_data = json.loads(playlists_response.text)

        display_arr = [profile_data] + playlist_data["items"]

        return playlist_data

