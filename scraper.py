#!/usr/bin/env python3
import requests, requests_cache
from queue import Queue
from threading import Thread, Lock
import pickle

# Used in parse_item() to go from slot IDs to slot names for self.fitting entries
SLOTS = ["low", "mid", "high"]


#TODO: Add a wrapper function for API requests that can do error handling
#TODO: OR, as an alternate, use the swagger-client library which will handle some
#       of that for me
#TODO: This is probably gonna just fall apart for T3Cs so let's cross our fingers
#       and pray that T3Cs will be a relatively small part of the data.
#       TBH this seems unlikely but yolo
#TODO: A lot of this can be made to go WAY faster by just downloading the eve SDE
#       and interfacing with the SQL server. This honestly should be like top priority.
#       I'm doing some local caching but it'll probably get super shitty if you
#       try to do this for a large number of killmails

class Killmail:

    def __init__(self):

        # Set these bad boys to -1 for that gucci error checking later
        self.points = -1
        self.value = -1
        self.damage_taken = -1
        self.ship = -1

        self.isk_destroyed = -1
        self.isk_lost = -1
        self.points_won = -1      # I'm sorry this breaks the naming convention
        self.points_lost = -1
        self.ships_destroyed = -1
        self.ships_lost = -1

        self.friendly_pilots = -1
        self.hostile_pilots = -1

        # I'm keeping cargo info saved so I can do fun stuff like analyze what
        #   the luckiest cargo is
        self.fitting = dict({"high":[], "mid":[], "low":[], "rigs":[], "drones":[], "cargo":[]})

        # Optimistic, but we'll go with it for now
        self.invalid = False

    def __repr__(self):
        repstr = \
        "Points: {points}\n\
Value: {value}\n\
Fitting:\
\n\tHigh:{high}\
\n\tMid:{mid}\
\n\tLow:{low}".format(\
        points =self.points,
        value =self.value,
        high =self.fitting["high" ],
        mid =self.fitting["mid" ],
        low =self.fitting["low"])

        return repstr



# Pull all the zKill kills for a certain day
# TODO: prob rework this into the above-mentioned wrapper tbh
def pull_date(date):

    r = requests.get('https://zkillboard.com/api/history/%s/' % date)
    json_data = r.json()

    return json_data


# Update the km object with the item added in the appropriate slot.
def parse_item(km, item):


    # Look up the item
    #https://esi.evetech.net/latest/universe/types/31011/?datasource=tranquility&language=en-us


    # It was here that I realized the JSON object returned will only contain a
    #    "quantity_destroyed" or "quantity_dropped" field if a nonzero amount
    #   was destroyed or dropped respectively, instead of just having the field
    #   with a value of 0.
    # Because this requires me to now check whether the field exists before just
    #   using it, I'm going to do that with a ternary out of spite.

    total_quantity = 0

    dropped = item['quantity_dropped'] if 'quantity_dropped' in item.keys() \
        else 0
    destroyed = item['quantity_destroyed'] if 'quantity_destroyed' in item.keys() \
        else 0

    total_quantity = dropped + destroyed

    # Slots 11-18 are lows, 19-26 are mids, and 27-34 are highs, so this works
    # If it's a low/mid/high/rig:
    if item['flag'] in range(11,35):
        slotID = (item['flag'] - 11) // 8
        # print("slotID is %d" % slotID)
        slot = SLOTS[slotID]

        # But check to see if this is ammo loaded in a mod, and ignore if so
        r = requests.get('https://esi.evetech.net/latest/universe/types/%s/?datasource=tranquility&language=en-us' % item['item_type_id'], timeout=5)
        r = r.json()

        # Check a few obvious ones
        name = r['name']
        if name == 'Nanite Repair Paste' or "Cap Booster" in name:
            return -1

        # This is a list of various attribute IDs that might indicate it's a
        #   charge. Super janky. Extend this if I find more.
        for attribute in r['dogma_attributes']:
            if attribute['attribute_id'] in [137]:
                return -1

    #TODO: Storing these in a dict would be better than having magic numbers
    #   pouring out of my ass like a 3 AM drunk Taco Bell run
    # There's 9000% a better way to do this, probably involving just converting
    #   the ID to a string and using that to index a dict but whatever
    # Could even just rename the drones and cargo fields to 87 and 5 or something

    # Fuck cargo
    elif item['flag'] == 9:
        slot = "rig"

    # Gallente master race
    elif item['flag'] == 87:
        slot = "drones"

    # Fuck cargo
    elif item['flag'] == 5:
        slot = "cargo"

    # If it's some other shit just don't worry about it
    else:
        return -1

    km.fitting[slot] += [item['item_type_id']] * total_quantity

    return 0


# ZKill has a hidden endpoint at
#   https://zkillboard.com/api/related/[system]/[year month day 24h-time like 201811032300]/
#   which only works for minutes = 00. (Relatedly, wat? What's the logic there? I
#   guess it's just a dev feature for now)
# TODO: This is gonna get mega fucked by bad BRs, so figure out how to filter those
def get_fight_info(system, time, km, char):

    char_id = char
    # print("Looking at char %d" % char_id)

    related_request = requests.get(\
        'https://zkillboard.com/api/related/{sys}/{time}/'.format(\
        sys=system, time=time), timeout=5)

    related_data = related_request.json()

    # HACK: The following sections are unbelievably janky, but so is the zKill
    #   battle report API. Sometimes it returns an empty result, and querying a
    #   time somewhat nearby seems to mess with the caching and regenerate it.
    # Also, sometimes just adding more unnecessary 0s at the end whips it
    #   into shape.

    ########## Primary fallback ##########
    if related_data == []:
        raise Exception

        with requests_cache.disabled():
            # Add those unnecessary two zeros
            related_request = requests.get(\
                'https://zkillboard.com/api/related/{sys}/{time}/'.format(\
                sys=system, time=time + '00'), timeout=5)

            related_data = related_request.json()

    ########## Secondary fallback ##########
    if related_data == []:

        # Increment the hours by 1, and make another request. S U P E R dodgy
        #   solution because worst case you're just getting straight up different
        #   BRs.
        t2 = int(time[-4:-2])
        t2 = '{0:02d}'.format(t2 + 1) + '00'

        with requests_cache.disabled():
            related_request = requests.get(\
                'https://zkillboard.com/api/related/{sys}/{time}/'.format(\
                sys=system, time=time[:-4] + t2), timeout=5)

            related_data = related_request.json()

        if related_data == []:
            raise Exception

    # 1. Find which team  the ship we're looking at was on
    team = ''

    # TODO: This is super dumb and embarassing
    for combatant in related_data['summary']['teamA']['list']:

        # This avoids errors from NPCs
        if 'characterID' not in combatant.keys():
            continue

        if char_id == combatant['characterID'] and km.ship == combatant['shipTypeID']:
            team = 'teamA'

    if not team == 'teamA':
        team = 'teamB'

    # 2. Then find the isk won/lost, points won/lost for that team
    friendly = related_data['summary'][team]['totals']

    # I want you to know I actually chuckled out loud when I wrote this
    teams = {'teamA':'teamB','teamB':'teamA'}
    hostile = related_data['summary'][teams[team]]['totals']

    # I'm a bad coder, revel in it
    km.isk_destroyed = hostile['total_price']
    km.points_won = hostile['total_points']
    km.ships_destroyed = hostile['total_points']

    km.isk_lost = friendly['total_price']
    km.points_lost = friendly['total_points']
    km.ships_lost = friendly['total_points']

    km.friendly_pilots = friendly['pilotCount']
    km.hostile_pilots = hostile['pilotCount']

    return 0


# Pull the info for a kill, and break it down into a detailed entry
#   Specifically, we want to look at this kill and get things like shiptype,
#   bonuses, what was fit, and then some more specifics about the engagement.
#   The specifics about the engagement will come from zKill.
def get_kill_info(id, hash):

    # Wish I make get these this easily in Eve
    km = Killmail()


    # Pull various stats from zKill (points, ISK value)
    zkill_request = requests.get('https://zkillboard.com/api/killID/%s/' % id, timeout=5)
    zkill_data = zkill_request.json()[0]

    # If it was an awox, fuck this
    if zkill_data['zkb']['awox'] or zkill_data['zkb']:
        km.invalid = True

    km.value = zkill_data['zkb']['totalValue']
    km.points = zkill_data['zkb']['points']


    # Pull damage taken and items from the Eve API
    esi_request = requests.get(
        'https://esi.evetech.net/dev/killmails/%s/%s/?datasource=tranquility'
        % (id, hash), timeout=5)
    esi_data = esi_request.json()

    km.damage_taken = esi_data['victim']['damage_taken']
    km.ship  = esi_data['victim']['ship_type_id']

    # Parse the fitting
    items = esi_data['victim']['items']

    # ball out with your list comprehensions out
    [parse_item(km, item) for item in items]


    # If it's solo, skip all the related kills crap
    if zkill_data['zkb']['solo'] == True:
        #TODO: Someday
        pass

    else:

        # Get the time, and strip all the crap
        time = esi_data['killmail_time'][:-1]
        t2 = ''.join([x for x in time if x not in [":","T","Z","-"]])

        # Round the last digits in time. Minutes must be 00 for the API
        rounded_time = (t2[:10] + '00') if int(t2[10:12]) < 30\
            else (t2[:8] + '{0:02d}'.format(int(t2[8:10]) + 1) + '00')

        try:
            get_fight_info(esi_data['solar_system_id'], rounded_time,
                km, esi_data['victim']['character_id'])

        except KeyError:
            # The killmail was probably generated by a structure
            raise KeyError

        except Exception:
            # This error is generally propagated up from a bad request
            #   in get_fight_info. The BR's cache as empty results, and
            #   there's not much I can do about that.
            raise Exception

    return km


def process_ids(id_queue, kill_queue, key_errors, other_errors, json_data, lock):

    while not id_queue.empty():
        print("\rRemaining: %7d \tCompleted: %7d \tErrored: %7d" % (
            id_queue.qsize(), kill_queue.qsize(), other_errors[0]), end='')

        # Man I love doing tuple assignments like this
        (id,hash) = id_queue.get_nowait()

        # Analyze the KM
        try:
            kill = get_kill_info(id, hash)

        # This means it was a non-character on the killmail
        except KeyError:
            lock.acquire()
            key_errors[0] += 1
            lock.release()

        # This isn't great -- usually it's due to fight BRs not being generated.
        except Exception:
            lock.acquire()
            other_errors[0] += 1
            lock.release()

        else:
            kill_queue.put(kill)

            id_queue.task_done()
            pass
    return




# TODO: A lot of the flow of this main loop will be reworked, and is just
#   temporarily while I'm getting this working
if __name__=="__main__":

    # Initialize the cache so we don't shit up zKill with requests
    requests_cache.install_cache('zKill_cache')


    # Pull zKill data
    date = "20181103"
    print("Pulling kill data for %s" % date)
    json_data = pull_date(date)

    num_threads=500

    processed = 0
    # Store these in a list so they can be passed by reference to the thread
    key_errors, other_errors = [0], [0]

    # Use Queues to pass information in and out of threads
    kill_queue = Queue(maxsize=0)
    id_queue = Queue(maxsize=0)
    # yea i use list comprehensions as maps what're you gonna do about it
    [id_queue.put((id, json_data[id])) for id in list(json_data.keys())]

    lock = Lock()

    workers = []
    for i in range(num_threads):
        worker = Thread(target=process_ids,
            args=(id_queue,kill_queue, key_errors, other_errors, json_data, lock, ))
        worker.setDaemon(True)
        worker.start()
        workers.append(worker)

    # Wait for worker threads to terminate
    # I wasn't paying attention in CSCI 206 when we talked about deadlock so
    #   cross your fingers and hope for the best (half joking)
    for worker in workers:
        worker.join()

    print("\nAll kills parsed, reorganizing into list...")
    kills = []
    while not kill_queue.empty():
        kills.append(kill_queue.get())


    print("Corpus of kills generated.")

    # Store the finished result for that date
    print("Saving pickle")
    with open(date + '.pkl', 'wb') as outfile:
        pickle.dump(kills, outfile)
