# Importing os to check if token.pickle file exists in the directory
import os
# Importing pickle to save and load credentials as and from byte streams
import pickle
# Importing google modules to help authorise API requests
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# OAuth 2.0 authorisation function
def auth():
    # Initialising credentials which will store tokens for verification with Google's YouTube API
    credentials = None

    # pickle loads token from token.pickle file if it exists and saves the contents to credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    # If there are no credentials or no valid credentials available...
    if not credentials or not credentials.valid:
        # if there are credentials that have expired and there is a refresh token to get new access tokens then refresh
        # the access token
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        # Otherwise...
        else:
            # fetch new tokens with the client secrets file and with the following defined scopes 
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json',
                scopes=['https://www.googleapis.com/auth/youtube']
            )
            # run the local authorisation server
            flow.run_local_server(port=8080, prompt='consent', authorization_prompt_message='')
            # save the credentials
            credentials = flow.credentials

            # Dump the credentials for use in later API queries
            with open('token.pickle', 'wb') as f:
                pickle.dump(credentials, f)
    # Otherwise return the credentials
    return credentials

# Function to insert a video into my 'To watch later' YouTube playlist
def playlistInsert(videoID):
    # Retrieving the authorisation credentials using the auth function from before
    credentials = auth()
    # Building the service object which will make the API call to insert the video
    with build('youtube', 'v3', credentials=credentials) as ytService:
        # Creating the API request
        request = ytService.playlistItems().insert(
            part='snippet',
            body={
                'snippet': {
                    'playlistId': 'PLL_zqGJzFipIjbeZfTmJTgnoM4Gl-80Hn',
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': videoID
                    }
                }
            }
        )
        # Executing the request
        response = request.execute()
