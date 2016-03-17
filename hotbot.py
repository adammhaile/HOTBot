from __future__ import print_function
import httplib2
import os
import sys
import dateutil.parser as dateparse

try:
    from apiclient import discovery
    import oauth2client
    from oauth2client import client
    from oauth2client import tools
except ImportError:
    print("""
Google API Modules are required:
pip install --upgrade google-api-python-client
Then visit the link below and follow the instructions to setup your API credentials:
https://developers.google.com/google-apps/calendar/quickstart/python
client_secret.json should be placed in ~/.hotbot
    """)

import datetime
import readline
import argparse
from jsonconf import jsonconf
import uuid
from random import randint
from croniter import croniter

import logging

log = logging.getLogger(name='__name__')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
log.addHandler(handler)
log.setLevel(logging.INFO)

# pip install --upgrade google-api-python-client
# https://console.developers.google.com/start/api?id=calendar
# https://console.developers.google.com/apis/

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'HOTBot'


def get_short_unique():
    return str(uuid.uuid4())[:8]


def default_input(prompt, default=None):
    # https://chistera.yi.org/~dato/blog/entries/2008/02/14/python_raw_input_with_an_editable_default_value_using_readline.html
    if not default:
        default = ""

    def pre_input_hook():
        readline.insert_text(default)
        readline.redisplay()

    prompt += ": "
    readline.set_pre_input_hook(pre_input_hook)
    try:
        return raw_input(prompt)
    finally:
        readline.set_pre_input_hook(None)


def number_ordinal(n):
    # http://stackoverflow.com/questions/9647202/ordinal-numbers-replacement/20007730#20007730
    return "%d%s" % (n, "tsnrhtdd"[(n/10 % 10 != 1)*(n % 10 < 4) * n % 10::4])


class HOTBot(object):
    guest_values = [
        ('displayName', 'Guest Name'),
        ('email', 'Guest email')]

    location_values = [
        ('name', 'Name'),
        ('location', 'Location'),
        ('phone', 'Phone'),
        ('website', 'Website'),
        ('tag', 'Tag (optional)'),
        ('reservation', 'Takes reservations')]

    event_message_fields = [
        ('event', 'HOT'),
        ('day', 10),
        ('day_ordinal', '10TH'),
        ('day_name', 'Thursday'),
        ('month', 2),
        ('month_ordinal', '3rd'),
        ('month_name', 'March'),
        ('year', 2016),
        ('guest_count', 8),
        ('name', "Cthulu's Pub"),
        ('location', "123 Ancient One Ave, R'lyeh, NY"),
        ('phone', '867-5309'),
        ('website', 'http://cthuluspub.hp'),
        ('start_time', '2016-03-10T19:00:00-05:00'),
        ('short_time', '7:00 PM')
    ]

    event_message_example = (
        "It has been decreed, that on {day_name}, the {day_ordinal} "
        "day of {month_name}, {year}, that {event} shall be held at "
        "{name}. The {guest_count} believers shall arrive at "
        "{location} promptly at {short_time}, or risk the wrath of the "
        " Ancient Ones.")

    def __init__(self, event, flags=None):
        self.flags = flags
        self.service = None
        self.event = event
        conf_dir = self.get_conf_dir()
        self.event_conf = jsonconf(os.path.join(conf_dir, self.event + ".json"))
        self.event_loc_history = jsonconf(os.path.join(conf_dir, self.event + "_history.json"))
        if not self.event_loc_history.locations:
            self.event_loc_history.locations = {}
            self.event_loc_history.save()
        self.authorized = False

    def get_conf_dir(self):
        home_dir = os.path.expanduser('~')
        conf_dir = os.path.join(home_dir, '.hotbot')
        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir)

        return conf_dir

    def get_credentials(self):
        conf_dir = self.get_conf_dir()
        credential_path = os.path.join(conf_dir, self.event + '_credentials.json')

        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            log.warn("No current valid Google credentials. Starting authentication flow...")
            flow = client.flow_from_clientsecrets(os.path.join(conf_dir, 'client_secret.json'),
                                                  'https://www.googleapis.com/auth/calendar')
            flow.user_agent = "HOTBot"
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else:  # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            log.info('Storing credentials to ' + credential_path)
        return credentials

    def authorize(self):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('calendar', 'v3', http=http)
        self.authorized = True

    def manage_locations(self):
        return self.manage_list('locations', HOTBot.location_values,
                                'Current Locations', 'name')

    def reset_loc_history(self, tag=None):
        if not tag:
            tag = '*'
        log.info("Resetting history for [{}] locations...".format(tag))
        del self.event_loc_history.locations[tag]
        self.event_loc_history.save()

    def add_loc_history(self, loc):
        if loc in self.event_conf.locations:
            l = self.event_conf.locations[loc]
            tag = l['tag'].strip().lower()
            if not tag:
                tag = '*'
            if tag not in self.event_loc_history.locations:
                self.event_loc_history.locations[tag] = []
            self.event_loc_history.locations[tag].append(loc)
            self.event_loc_history.save()

    def _get_loc_bins(self):
        # sort into bins exclusively
        bins = {'*': []}
        for k, l in self.event_conf.locations.iteritems():
            t = l['tag'].strip().lower()
            if not t:
                t = '*'
            if t not in bins:
                bins[t] = []

            if (t not in self.event_loc_history.locations or
                    k not in self.event_loc_history.locations[t]):
                bins[t].append(k)

        return bins

    def get_rand_location(self, start_time, tag=None):
        if tag:
            tag = tag.strip().lower()
        else:
            tag = '*'

        bins = self._get_loc_bins()
        if tag not in bins or len(bins[tag]) == 0:
            # we've used them all, try to reset history
            self.reset_loc_history(tag=tag)
            bins = self._get_loc_bins()
        if tag not in bins or len(bins[tag]) == 0:
            return None

        i = randint(0, len(bins[tag]) - 1)
        key = bins[tag][i]
        loc = self.event_conf.locations[bins[tag][i]]

        info = dict(loc)
        info['start_time'] = start_time
        time = dateparse.parse(start_time)
        info['day_name'] = time.strftime('%A')
        info['day'] = time.day
        info['day_ordinal'] = number_ordinal(time.day)
        info['year'] = time.year
        info['month'] = time.month
        info['month_name'] = time.strftime('%B')
        info['month_ordinal'] = number_ordinal(time.month)
        info['short_time'] = str(time.hour % 12) + time.strftime(':%M %p')
        info['event'] = self.event
        info['guest_count'] = len(self.event_conf.guests)

        return (key, loc, info)

    def insert_events(self):
        print('\nInsert event placeholders using cron format.'
              '\nSee https://en.wikipedia.org/wiki/Cron format for details.')

        loc_tag = default_input("Location Tag (enter for none)", default="")
        if not loc_tag:
            loc_tag = None

        fmt = '%Y-%m-%d'
        base = datetime.datetime.now()
        def_base = base_str = base.strftime(fmt)

        while True:
            base_str = default_input("Start Date", default=def_base)
            try:
                base = datetime.datetime.strptime(base_str, fmt)
            except:
                print("Invalid Date Format! Use YYYY-MM-DD")
                continue
            break

        count = def_count = 10
        while True:
            count = default_input("# Events to Insert", str(def_count))
            try:
                count = int(count)
                if count < 1:
                    raise Exception()  # lazy way to handle with less code
            except:
                print("Please enter a valid integer > 0!")
                continue
            break

        cron_fmt = None
        cron = None
        events = []
        event_objs = []
        while True:
            while True:
                cron_fmt = default_input("Cron Expression", default=cron_fmt)
                try:
                    cron = croniter(cron_fmt, start_time=base)
                except:
                    print('\nInvalid Cron Expression!'
                          '\nSee https://en.wikipedia.org/wiki/Cron format for examples.')
                    continue
                break

            events = []
            event_objs = []
            for _ in range(count):
                evt = cron.get_next(ret_type=datetime.datetime)
                event_objs.append(evt)
                events.append(evt.strftime(fmt + ' %H:%M'))
            print("Events to be inserted: \n" + ", ".join(events))
            resp = default_input("\nInsert Events (y) or Edit (e)?", default=None)
            if resp.lower().startswith('y'):
                break

        for evt in event_objs:
            self.inser_event_placeholder(evt, duration=120, loc_tag=loc_tag)

    def manage_messages(self):
        key = 'messages'

        fields = [f[0] for f in HOTBot.event_message_fields]
        field_dict = {f[0]: f[1] for f in HOTBot.event_message_fields}

        if not self.event_conf[key]:
            self.event_conf[key] = []

        def delete_item(i):
            opt = default_input('Confirm delete? (yes/no)').lower()
            if opt.startswith('y'):
                del self.event_conf[key][i]
                self.event_conf.save()

        def check_msg(msg):
            while True:
                try:
                    output = msg.format(**field_dict)
                    print('Rendered message: ' + output.replace("\\n", "\n").replace("\\t", "\t"))
                    opt = default_input("\ns (save), e (edit) ?").lower()
                    if opt.startswith('s'):
                        break
                    # continue for anything else, e is just for show
                except KeyError as e:
                    bad_key = e.args[0]
                    print("\nInvalid message field: " + bad_key)
                    print("\nAvailable message fields:\n" + ", ".join(fields))
                except IndexError:
                    print("Text replacement fields must contain a field name!")
                except ValueError as e:
                    print("Invalid formatting: " + e.args[0])
                msg = default_input("\nEdit Message: ", default=msg)
            return msg

        def edit_item(i):
            msg = self.event_conf[key][i]
            msg = default_input("Message", msg)
            msg = check_msg(msg)
            self.event_conf[key][i] = msg
            self.event_conf.save()

        def new_item():
            msg = default_input("New Message")
            msg = check_msg(msg)
            self.event_conf[key].append(msg)
            self.event_conf.save()

        def print_items():
            count = 1
            print('\nMessages for event: {}'.format(self.event))
            for msg in self.event_conf[key]:
                if len(msg) > 70:
                    msg = msg[:70] + "..."
                print('{}: {}'.format(count, msg))
                count += 1

        print("")
        print("Available message fields:\n" + ", ".join(fields))
        print("\nExample message:\n" + HOTBot.event_message_example)
        print("\nOutput:\n" + HOTBot.event_message_example.format(**field_dict))
        print("")

        while True:
            if len(self.event_conf[key]):
                num = len(self.event_conf[key])
                print_items()
                opt = default_input("\n1-{} (edit), n (new), d (delete), q (quit)".format(num)).lower()
                if opt.startswith('q'):
                    break
                elif opt.startswith('n'):
                    new_item()
                else:
                    delete = False
                    try:
                        if opt.startswith('d'):
                            delete = True
                            opt = default_input("(1-{}) select".format(num))
                        opt_i = int(opt)
                        opt_i -= 1
                        # purely to throw exception if out of bounds
                        self.event_conf[key][opt_i]
                    except (ValueError, IndexError):
                        print("Invalid selection. Must be 1-{} or n/d/q".format(num))
                        continue
                    if delete:
                        delete_item(opt_i)
                    else:
                        edit_item(opt_i)
            else:
                print("\nNo current entries. Please add one first...")
                new_item()

    def get_rand_message(self, info):
        messages = self.event_conf.messages
        if not messages:
            messages = [
                ("Phone: {phone}"
                 "\nWebsite: {website}"
                 "\nReservations: {reservation}"
                 )
            ]
        i = randint(0, len(messages) - 1)
        return messages[i].format(**info).replace("\\n", "\n").replace("\\t", "\t")

    def manage_guests(self):
        return self.manage_list('guests', HOTBot.guest_values,
                                'Current Guests', 'displayName')

    def manage_list(self, key, values, list_msg, list_field):
        if not self.event_conf[key]:
            self.event_conf[key] = {}

        def delete_item(i):
            item = self.event_conf[key][i]
            opt = default_input('Confirm delete {}? (yes/no)'.format(item[list_field])).lower()
            if opt.startswith('y'):
                del self.event_conf[key][i]
                self.event_conf.save()

        def edit_item(i):
            item = self.event_conf[key][i]
            for v in values:
                self.event_conf[key][i][v[0]] = default_input(v[1], item[v[0]])
            self.event_conf.save()

        def new_item():
            item = {}
            for v in values:
                item[v[0]] = default_input(v[1])
            u = get_short_unique()
            self.event_conf[key][u] = item
            self.event_conf.save()

        def print_items():
            count = 1
            print('\n{} for event: {}'.format(list_msg, self.event))
            self.key_map = []
            for i in self.event_conf[key]:
                print('{}: {}'.format(count, self.event_conf[key][i][list_field]))
                self.key_map.append(i)
                count += 1

        while True:
            if len(self.event_conf[key]):
                num = len(self.event_conf[key])
                print_items()
                opt = default_input("\n1-{} (edit), n (new), d (delete), q (quit)".format(num)).lower()
                if opt.startswith('q'):
                    break
                elif opt.startswith('n'):
                    new_item()
                else:
                    delete = False
                    try:
                        if opt.startswith('d'):
                            delete = True
                            opt = default_input("(1-{}) select".format(num))
                        opt_i = int(opt)
                        opt_i -= 1
                        # purely to throw exception if out of bounds
                        self.event_conf[key][self.key_map[opt_i]]
                        opt = self.key_map[opt_i]
                    except (ValueError, IndexError):
                        print("Invalid selection. Must be 1-{} or n/d/q".format(num))
                        continue
                    if delete:
                        delete_item(opt)
                    else:
                        edit_item(opt)
            else:
                print("\nNo current entries. Please add one first...")
                new_item()

    def get_calendars(self):
        if not self.authorized:
            self.authorize()

        cals = self.service.calendarList().list().execute()

        cal_list = {}
        for c in cals['items']:
            cal_list[c['id']] = c['summary']
        return cal_list

    def select_host_calendar(self):
        if not self.authorized:
            self.authorize()

        cals = self.get_calendars()
        print("\nSelect your host calendar for event: {}".format(self.event))
        id_list = []
        for c in cals:
            id_list.append(c)
            print("{}: {}".format(len(id_list), cals[c]))
        i = raw_input("Choice: ")
        try:
            i = int(float(i))
            cal_id = id_list[i - 1]
            self.event_conf.host_cal = cal_id
        except (ValueError, IndexError):
            print("Invalid selection! Must be a number between 1 and {}".format(
                len(id_list) - 1))
        self.event_conf.save()

    def get_cal_events(self, event=None, days_future=7, max_results=None):
        if not self.authorized:
            self.authorize()

        if not event:
            event = self.event

        now = datetime.datetime.utcnow()
        end = (now + datetime.timedelta(days=days_future)).isoformat() + 'Z'
        now = now.isoformat() + 'Z'

        result = self.service.events().list(
            calendarId=self.event_conf.host_cal, timeMin=now, timeMax=end,
            maxResults=None, singleEvents=True,
            orderBy='startTime').execute()
        events = result.get('items', [])
        event_list = []
        for e in events:
            if e['summary'].startswith('[' + self.event):
                event_list.append(e)

        return event_list

    def inser_event_placeholder(self, start, duration=120, loc_tag=None):
        if not self.authorized:
            self.authorize()

        tzone = self.service.settings().get(setting='timezone').execute()['value']

        fmt = '%Y-%m-%dT%H:%M:00'
        name = self.event
        if loc_tag:
            name += (":" + loc_tag)
        name = "[" + name + "]"

        end = start + datetime.timedelta(minutes=duration)

        event = {
            'summary': name,
            'start': {
                'dateTime': start.strftime(fmt),
                'timeZone': tzone,
            },
            'end': {
                'dateTime': end.strftime(fmt),
                'timeZone': tzone,
            }
        }

        print("Creating {}, {}...".format(name, start.strftime(fmt)))
        res = self.service.events().insert(calendarId=self.event_conf.host_cal,
                                           body=event).execute()
        print("Created: {}".format(res.get('htmlLink')))

    def update_event(self, event, name, description, location):
        if not self.authorized:
            self.authorize()

        cal_id = self.event_conf.host_cal
        event["summary"] = name
        event['attendees'] = []
        for _, g in self.event_conf.guests.iteritems():
            event['attendees'].append(g)
        event['location'] = location
        event["description"] = description

        result = None
        try:
            result = self.service.events().update(calendarId=cal_id, eventId=event['id'],
                                                  body=event, sendNotifications=True).execute()
        except:
            log.exception("Error updating event!")
        return result


def main(flags=None):
    bot = HOTBot(event=flags.event, flags=flags)
    if not bot.event_conf.host_cal:
        log.info("No calendar selected. Loading options...")
        bot.select_host_calendar()

    if flags.edit_guests:
        bot.manage_guests()
    elif flags.edit_loc:
        bot.manage_locations()
    elif flags.edit_msg:
        bot.manage_messages()
    elif flags.select_cal:
        bot.select_host_calendar()
    elif flags.ins_events:
        bot.insert_events()
    else:
        events = bot.get_cal_events(days_future=flags.days)
        if len(events):
            evt = events[0]
            summary = evt['summary'].strip('[').strip(']').strip().split(':')
            tag = None
            if len(summary) > 1:
                tag = summary[1]
            summary = summary[0]
            loc = bot.get_rand_location(evt['start']['dateTime'], tag)

            if not loc:
                log.error("Unable to find location with given parameters!")
                sys.exit(1)
            else:
                key, loc, info = loc

                name = bot.event + " - " + loc['name']
                log.info("Creating event: " + name)
                description = bot.get_rand_message(info)
                location = loc['location']
                result = bot.update_event(evt, name, description, location)
                if not result:
                    log.error("There seems to have been an error updating the event. Try again later...")
                else:
                    bot.add_loc_history(key)
                    log.info("Event update success!")
        else:
            log.error(("No upcoming events found for {} in the next {} days. "
                       "Either create a placeholder in GCal or "
                       "search further into the future with the --days option.")
                      .format(bot.event, flags.days))
            sys.exit(1)

if __name__ == '__main__':
    # can use --noauth_local_webserver to manually auth
    parser = argparse.ArgumentParser(description='HOTBot automated event scheduler',
                                     parents=[tools.argparser])
    parser.add_argument(
        "--event",
        required=True,
        help="Event name (used as key for calendar lookup)")
    parser.add_argument(
        "--days",
        help="Number of days in the future to look for events (default: 7)",
        type=int,
        default=7)
    parser.add_argument(
        "--edit-guests", dest='edit_guests',
        default=False, action='store_true',
        help="Edit guests for event")
    parser.add_argument(
        "--edit-loc", dest='edit_loc',
        default=False, action='store_true',
        help="Edit locations for event")
    parser.add_argument(
        "--edit-msg", dest='edit_msg',
        default=False, action='store_true',
        help="Edit possible messages for event")
    parser.add_argument(
        "--select-cal", dest='select_cal',
        default=False, action='store_true',
        help="Select host calendar")
    parser.add_argument(
        "--ins-events", dest='ins_events',
        default=False, action='store_true',
        help="Insert event placeholders into calendar with cron formatting")
    flags = parser.parse_args()

    try:
        main(flags)
    except SystemExit:
        pass
    except:
        log.exception("Fatal error occured in script: ")
    finally:
        logging.shutdown()
