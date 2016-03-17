# HOTBot
HOTBot is designed to automate the process of randomly selecting an event location from a pre-defined list and then sending out Google Calendar invites to a list of guests. It is very bare-bones and excepted to either be run manually or as a cron job for full automation. 

# Installation

Currently, installation is just downloading the [source zip](https://github.com/adammhaile/HOTBot/archive/master.zip) and then installing the dependencies via:

```pip install -r requirements.txt```

**Note**: Currently only Linux is supported.

# Google API Key Creation

Before completing setup, you must follow the instructions here: https://developers.google.com/google-apps/calendar/quickstart/python

This will walk you through the process of creating an API key to use with HOTBot.

You will need to place the generated client_secrets.json file into ~/.hotbot/ on the system HOTBot is running on and for the user which will run HOTBot.

# First Auth

After unzipping the files, run the script with:

```python hotbot.py --event EVENT_NAME```

If you are running it in a remote console, be sure to use the ```--noauth_local_webserver``` option during the first run. This will prevent the authentication process from trying to open a browser to complete the authentication.

Authenticate against the Google account you would like to use to host your even calendar. After authenticating, you will need to run the script again with the same command. Now it will automatically ask you to choose the calendar which HOTBot should use. The main calendar on your account will always be named whatever your google email address is, but you can choose any of those listed.

# Calendar Selection

On the first run after authentication, it will automatically ask you to select the calendar you wish to use. You can also do this again at any time by calling with the ```--select-cal``` flag like this:

```python hotbot.py --event EVENT_NAME --select-cal```

# Calendar Setup

HOTBot looks for specially named events in the given calendar. They should be named ```[EVENT_NAME]``` or ```[EVENT_NAME:LOCATION_TAG]```. On each run, HOTBot will search 7 days into the future (modifiable with the ```--days``` option) to find any calendar events that have this naming scheme. 

**Note:** It is *not* recommended to use the recurring event feature in Google Calendar. This makes creating the event placeholders a lot quicker, but if this option is used event attendees will be asked if they want to RSVP to the current event or the entire series. In most cases you do not want attendees responding to the entire series, because the rest of the series is not yet defined. Instead, create the initial event placeholder and than duplicate it as many times as you desire.

# Location Setup

Run the following command:

``````python hotbot.py --event EVENT_NAME --edit-loc```

You be presented with an interactive entry form for the event locations. When adding a new or editing an existing location, you will be given the following fields:

- **Name**: Event location name.
- **Location**: Address or other geographic location identifier. Anything supported by Google Maps.
- **Phone**: Phone number of venue, if any.
- **Website**: Website for venue, if any.
- **Tag**: Location tag for event filtering, more details below.
- **Takes Reservations**: Free-form field to enter info about venue's reservation policy.

#### Location Tags

It may be desireable to only select specific locations out of the full list at times. For example: There is a weekly event called HOT (Hang Out Time) that is normally in the Raleigh, NC area. But every first event of the month should be in the Durham, NC area. 

You can tag one or more locations with "Durham" but leave all the other location tags empty. Then, in Google Calendar, name the first events of each month [HOT:Durham] instead of [HOT]. This will tell HOTBot to only choose from the locations tagged with "Durham".

Note that the tags are purely exclusive. Locations with a tag will *never* be selected unless that tag is specified in the event placeholder name. Conversely, events without a tag will *only* be selected on event placeholders without a tag.

##### Location History

As each location is selected, it is added to a history file. The next time HOTBot runs, it will exclude the events in the history from its selection. If, however, there are no more locations that are *not* in the history, it will automatically clear the history and start over with the full list.

As tagged locations are exlusive, the history is also exclusive to each tag. So, the history for a specific tag may rollover before all of the untagged locations are used.

This behavior cannot currently be changed.

# Guest Setup

Run the following command:

``````python hotbot.py --event EVENT_NAME --edit-guests```

You be presented with an interactive entry form for the event guests. When adding a new or editing an existing guest, you will be given the following fields:

- **Guest Name**: Can be anything. Purely for identification.
- **Guest email**: The email address for the user.

email addresses need not be Google/GMail accounts. While the integration when using Google/GMail accounts is much tighter, guests that use other mail/calendar applications like Outlook or Thunderbird will work fine.

##### Google Sub-Calendars

If using a Google/GMail address, the invite will be sent to the primary calendar on that guest's account. It is, however, possible to send the invite directly to a sub-calendar. In Google Calendar go to [Gear Icon] > Settings > Calendars Tab, then click the name of the desired sub-calendar. Look for the "Calendar Address" section and you will see a "Calendar ID" field that looks like this: ```um12345c678abcde3b7b6ajng@group.calendar.google.com```

If you use this sub-calendar ID as the "Guest email" entry, the invite will go directly to that sub-calendar. 

**Warning**: In the event details visible to all guests, the guest name when using a sub-calendar will be whatever that guest named the sub-calendar. This may make it hard to determine who the guest actually is.


