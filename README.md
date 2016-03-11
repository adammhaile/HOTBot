# HOTBot
Dynamic, random, and automated event scheduler using Google Calendar

# Installation

Currently, installation is just downloading the [source zip](https://github.com/adammhaile/HOTBot/archive/master.zip) and then installing the dependencies via:

```pip install -r requirements.txt```

**Note**: Currently only Linux is supported.

# Google API Key Creation

Before completing setup, you must follow the instructions here: https://developers.google.com/google-apps/calendar/quickstart/python

This will walk you through the process of creating an API key to use with HOTBot.

You will need to place the generated client_secrets.json file into ~/.hotbot/ on the system HOTBot is running on and for the user which will run HOTBot.

# Setup

After unzipping the files, run the script with:

```python hotbot.py --event EVENT_NAME```

If you are running it in a remote console, be sure to use the ```--noauth_local_webserver``` option during the first run. This will prevent the authentication process from trying to open a browser to complete the authentication.

Authenticate against the Google account you would like to use to host your even calendar. After authenticating, you will need to run the script again with the same command. Now it will automatically ask you to choose the calendar which HOTBot should use. The main calendar on your account will always be named whatever your google email address is, but you can choose any of those listed.