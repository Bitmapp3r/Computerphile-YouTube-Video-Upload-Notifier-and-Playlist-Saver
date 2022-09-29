# Importing urlparse, parse_qs from urllib.parse to help parse the request URLs 
from urllib.parse import urlparse, parse_qs
# Importing HTTPServer, BaseHTTPRequestHandler from http.server to launch HTTP server using the BaseHTTPRequestHandler
# request handler
from http.server import HTTPServer, BaseHTTPRequestHandler
# Importing ngrok, conf from pyngrok to create a HTTP tunnel from a generated public ngrok URL to the localhost, and to
# edit the ngrok hosting configuration
from pyngrok import ngrok, conf
# Importing os to get environment variables
import os
# Importing requests to send a post request to subscribe to Google's Pubsubhubbub Hub
import requests
# Importing load_dotenv from dotenv to load environment variables
from dotenv import load_dotenv
# Importing threading to run the ngrok connection and HTTP server connection on separate threads (the threads still 
# only execute concurrently and not in parallel)
import threading
# Importing queue in order to store the generated public ngrok URL from the separate ngrok connection thread
import queue
# Importing xmltodict in order to parse the xml body from the POST response to the HTTP server
import xmltodict
# Importing datetime, timezone from datetime in order to format the dates and convert into local time
from datetime import datetime, timezone
from videoInsertPlaylist import auth, playlistInsert

# Custom requestHandler class for handling requests - inherits from the BaseHTTPRequestHandler class
class RequestHandler(BaseHTTPRequestHandler):
    # Class vidIDMemory attribute used to store IDs of videos that have been received in order to make sure they are not
    # output to the console more than once
    vidIDMemory = set()
    # Overridden do_GET method which runs when server receives a GET request
    def do_GET(self):
        # Storing the GET request URL sent to this server
        GET_URL = self.path
        # Parsing the URL into its separate elements
        parsedURL = urlparse(GET_URL)
        # Storing the query element of the URL
        queryString = parsedURL.query
        # Parsing the query into a dictonary with the query parameters as keys
        queryParamDict = parse_qs(queryString)
        # Trying to save the hub challenge string query parameter and encoding it as utf-8 binary to use as a response
        # for verification
        try:
            hubChallengeString = queryParamDict['hub.challenge'][0].encode('utf-8')
            # Sending response code
            self.send_response(200)
            # Sending header
            self.send_header('content-type', 'text/plain; charset=utf-8')
            # Adds a blank line indicating the end of the HTTP headers in the response to the headers buffer and calls 
            # flush_headers() which finally sends the headers to the output stream and flushes the internal headers buffer
            self.end_headers()
            # Sending encoded hub challenge string as a response
            self.wfile.write(hubChallengeString)
        # Otherwise sending a 400 response (which would occur if 'hub.challenge' was not a query parameter in the URL)
        except:
            self.send_response(400)
            self.end_headers()

    # Overridden do_POST method which runs when server receives a POST request
    def do_POST(self):
        # Checks if the POST request received does not have 'application/atom+xml' content type
        if self.headers.get_content_type() != 'application/atom+xml':
            # Sends a 400 response if this was the case
            self.send_response(400)
            return self.end_headers()
        # Otherwise sends a 200 response
        self.send_response(200)
        self.end_headers()
        # Reading the XML string data in the body
        xmlStringData = self.rfile.read().decode('utf-8')
        # Parsing the XML data to a dictionary for easier usability 
        dictData = xmltodict.parse(xmlStringData, encoding='utf-8')
        # Saving and printing the video data only if there is a video entry in the dictionary data and the video ID has
        # not been received before
        if 'entry' in dictData['feed'] and dictData['feed']['entry']['yt:videoId'] not in RequestHandler.vidIDMemory:
            RequestHandler.vidIDMemory.add(dictData['feed']['entry']['yt:videoId'])
            vidTitle = dictData['feed']['entry']['title']
            vidURL = dictData['feed']['entry']['link']['@href']
            vidID = dictData['feed']['entry']['yt:videoId']
            channelName = dictData['feed']['entry']['author']['name']
            channelURL = dictData['feed']['entry']['author']['uri']
            channelID = dictData['feed']['entry']['yt:channelId']
            # Formatting and converting the dates
            rawDatePublished = dictData['feed']['entry']['published']
            publishedDateObj = datetime.strptime(rawDatePublished, '%Y-%m-%dT%H:%M:%S%z')
            convPublishedDateObj = publishedDateObj.replace(tzinfo=timezone.utc).astimezone(tz=None)
            frmtdDatePublished = datetime.strftime(convPublishedDateObj, '%I:%M:%S%p %d/%m/%Y')
            print("========================================")
            print("Video Title: ", vidTitle)
            print("Video URL: ", vidURL)
            print("Video ID: ", vidID)
            print("Channel Name: ", channelName)
            print("Channel URL: ", channelURL)
            print("Channel ID: ", channelID)
            print("Date Published: ", frmtdDatePublished)

            # Attempting to save video to playlist
            try:
                playlistInsert(vidID)
                print("Saved video to playlist")
            except:
                print("Failed to save video to playlist")

    # Overridden log_message method used to disable outputting logs to the console
    def log_message(self, format, *args):
        pass

# Ngrok connection class
class NgrokConnection:
    # start method which starts the ngrok connection - it takes in a queue parameter to store the public ngrok URL in 
    # for later usage within the main thread outside the thread this method will be called in
    def start(self, queue_publicURL):
        conn = ngrok.connect(8000)
        # Printing the returned value (which shows the public ngrok URL and the localhost URL it is connected to)
        print(conn)
        # Storing the public ngrok URL in the queue
        queue_publicURL.put(conn.data['public_url'])

# main function
def main():
    # Calling load_dotenv from dotenv to load environment variables
    load_dotenv()
    # attempting to run the HTTP server, establish ngrok HTTP tunnel, and subscribe to the YouTube channel via Google's
    # Pubsubhubbub Hub
    try:
        # Running OAuth 2.0 authorisation function for YouTube API
        auth()
        # Instantiating a queue object to store the public ngrok URL in
        queue_publicURL = queue.Queue()
        # Setting the HTTP server port
        PORT = 8000
        # Storing Ngrok authentication token
        AUTH_TOKEN = os.getenv('AUTH_TOKEN')
        # Authenticating ngrok and configuring connection location
        ngrok.set_auth_token(AUTH_TOKEN)
        conf.get_default().region = "eu"

        # Instantiating the HTTP server
        server = HTTPServer(('', PORT), RequestHandler)
        # Instantiating NgrokConnection object
        ngrokConn = NgrokConnection()

        # Starting the HTTP server in a separate thread
        threadHttpServer = threading.Thread(target=server.serve_forever)
        threadHttpServer.start()
        print('HTTP server running on port %s' % PORT)

        # Starting the ngrok HTTP tunnel in a separate thread
        threadNgrokConn = threading.Thread(target=ngrokConn.start, args=(queue_publicURL,))
        threadNgrokConn.start()
        # Storing the public ngrok URL
        publicURL = queue_publicURL.get()
        
        # Setting POST request query parameters for subscription to Google's Pubsubhubbub Hub
        parameters = {
            'hub.mode': 'subscribe',
            'hub.topic': 'https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC9-y-6csu5WGm29I7JiwpnA',
            'hub.callback': publicURL
        }
        # Sending POST request
        requests.post('https://pubsubhubbub.appspot.com/subscribe', data=parameters)

        # Continuously running the HTTP server and ngrok tunnel until user enters 'server.quit' or 'ngrok.quit' to 
        # terminate them respectively, or 'quit' to exit the whole program
        isServerDown = False
        isNgrokDown = False
        while True:
            command = str(input())
            if command == 'server.quit':
                server.shutdown()
                print("Local server has been shut down")
                isServerDown = True
            if command == 'ngrok.quit':
                ngrok.kill()
                print("Ngrok tunnel has been shut down")
                isNgrokDown = True
            if command == 'quit':
                if not isNgrokDown:
                    ngrok.kill()
                    print("Ngrok tunnel has been shut down")
                if not isServerDown:
                    server.shutdown()
                    print("Local server has been shut down")
                break
            if isServerDown and isNgrokDown:
                break
    # Exits the program in case of error or keyboard interrupt signal (such as from 'CTRL + C')
    except:
        ngrok.kill()
        print("Ngrok tunnel has been shut down")
        server.shutdown()
        print("Local server has been shut down")

if __name__ == '__main__':
    main()
