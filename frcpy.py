from datetime import datetime

WINS = 0
LOSSES = 1
TIES = 2

class Location:
    def __init__(self, city, state, country):
        self.city = city
        self.state = state
        self.country = country

    def getLocationString(self):
        return self.city + ", " + self.state + ", " + self.country

class Team(Location):
    def __init__(self, team_number):
        self.team_number = team_number
        self.key = "frc" + str(team_number)
        self.attrs = {}
        self.event_keys = []
        self.event_wlt = {} # event -> (# wins, # loss, # ties)
        self.event_wins = {} # year -> [event, ...]
        for year in range(1992, 2030):
            self.event_wins[year] = []

    def loadTBAData(self, team_tba_data):
        self.name = team_tba_data.name
        self.nickname = team_tba_data.nickname
        self.city = team_tba_data.city
        self.state = team_tba_data.state_prov
        self.country = team_tba_data.country

    def loadEventWLT(self, event):
        if event.key not in self.event_keys:
            self.event_keys.append(event.key)
        # WLT
        self.event_wlt[event.key] = [0, 0, 0]
        for match in event.matches.values():
            if not match.finished:
                continue
            if self.key in match.red_teams:
                self.event_wlt[event.key][0 if match.winning_alliance == 'red' else 1 if match.winning_alliance == 'blue' else 2] += 1
            elif self.key in match.blue_teams:
                self.event_wlt[event.key][0 if match.winning_alliance == 'blue' else 1 if match.winning_alliance == 'red' else 2] += 1
        # Event Win
        winning_alliance = event.getWinningAlliance()
        if winning_alliance == None:
            return
        if self.key in winning_alliance.team_keys:
            self.event_wins[event.year].append(event)


    def getTotalWLT(self, year=None, eventcode=None): #returns (w, l, t)
        if eventcode != None:
            events = [eventcode]
        else:
            events = [event for event in self.event_wlt]
            if year != None:
                events = [event for event in events if event[:4] == str(year)]
        w = 0
        l = 0
        t = 0
        for event in events:
            w += self.event_wlt[event][0]
            l += self.event_wlt[event][1]
            t += self.event_wlt[event][2]
        return (w, l, t)

    def getAttr(self, key):
        return self.attrs[key] if key in self.attrs else None

    def __str__(self):
        return "frcpy_frc" + str(self.team_number)

class Match:
    def __init__(self):
        self.red_teams = [] #team_keys
        self.blue_teams = [] #team_keys
        self.finished = False
        # used for discovery
        self.attrs = {}

    def loadTBAData(self, match_tba_data):
        self.event_key = match_tba_data.event_key
        self.comp_level = match_tba_data.comp_level
        self.match_number = match_tba_data.match_number
        self.set_number = match_tba_data.set_number if self.comp_level in ['qf', 'sf', 'f'] else None
        self.key = match_tba_data.key
        self.predicted_time = match_tba_data.predicted_time
        self.scheduled_time = match_tba_data.time
        self.finished = match_tba_data.winning_alliance in ['red', 'blue'] or match_tba_data.actual_time != None
        self.score_breakdown = match_tba_data.score_breakdown
        if 'alliances' in match_tba_data and all(color in match_tba_data['alliances'] for color in ['red', 'blue']) and all('team_keys' in match_tba_data['alliances'][color] for color in ['red', 'blue']):
            self.red_teams += match_tba_data['alliances']['red']['team_keys']
            self.blue_teams += match_tba_data['alliances']['blue']['team_keys']
        if self.finished:
            self.winning_alliance = match_tba_data.winning_alliance
            if 'alliances' in match_tba_data and all(color in match_tba_data['alliances'] for color in ['red', 'blue']) and all('score' in match_tba_data['alliances'][color] for color in ['red', 'blue']):
                self.blue_score = match_tba_data['alliances']['blue']['score']
                self.red_score = match_tba_data['alliances']['red']['score']
           # if 'alliances' in match_tba_data and all(color in match_tba_data['alliances'] for color in ['red', 'blue']) and all('team_keys' in match_tba_data['alliances'][color] for color in ['red', 'blue']):
            #    self.red_teams += match_tba_data['alliances']['red']['team_keys']
             #   self.blue_teams += match_tba_data['alliances']['blue']['team_keys']

    # returns (red_alliance, blue_alliance)
    # returns ([Team, ...], [Team, ...])
    def getTeamObjects(self, team_dict): #team_list = dict of Team objects
        red_teams = []
        blue_teams = []
        for team in self.red_teams:
            if team in team_dict:
                red_teams.append(team_dict[team])
        for team in self.blue_teams:
            if team in team_dict:
                blue_teams.append(team_dict[team])
        if len(red_teams) != len(self.red_teams) or len(blue_teams) != len(self.blue_teams):
            print("Beware", self.key, "couldn't load team objects correctly.")
        return red_teams, blue_teams

    def getAttr(self, key):
        return self.attrs[key] if key in self.attrs else None

class Alliance:
    def __init__(self, event_key, alliance_obj):
        self.team_keys = alliance_obj["picks"]
        if "status" in alliance_obj and isinstance(alliance_obj["status"],dict):
            self.status = alliance_obj["status"]["status"]
        else:
            self.status = None
        self.event_key = event_key

    def wonEvent(self):
        return self.status == "won"


class Event(Location):
    def __init__(self, key):
        self.key = key
        self.year = int(key[:4])
        self.matches = {} # match key -> match object
        self.teams = [] # team keys
        self.attrs = {}

    def getTeamObjects(self, team_list): #team_list = list of Team objects
        teams = []
        for team_obj in team_list:
            if team_obj.key in self.teams:
                teams.append(team_obj)
        if len(teams) != len(self.teams):
            print("Beware {} couldn't load correct number of teams.".format(self.key))
        return teams

    def loadTBA(self, tba, all_teams):
        self.loadTBAData(tba.event(self.key))
        # update alliances
        if self.hasEventFinished():
            self.updateAlliances(tba)
        else:
            self.alliances = []
        # update matches
        self.updateMatches(tba)
        # bring in team keys
        self.loadTeamKeys(tba)
        # update w/l/t
        for team_key in self.teams:
            if team_key in all_teams:
                all_teams[team_key].loadEventWLT(self)
        

    def updateAlliances(self, tba):
        self.alliances = []
        try:
            alliances = tba.event_alliances(self.key)
        except TypeError:
            alliances = None
        if alliances == None:
            return
        for alliance in alliances:
            if alliance != None:
                self.alliances.append(Alliance(self.key, alliance))
    
    def getWinningAlliance(self):
        if self.alliances == None or len(self.alliances) == 0:
            return None
        for alliance in self.alliances:
            if alliance.wonEvent():
                return alliance
        return None

    def updateMatches(self, tba):
        for match in tba.event_matches(self.key):
            match_obj = self.matches[match.key] if match.key in self.matches else Match()
            match_obj.loadTBAData(match)
            self.matches[match_obj.key] = match_obj

    def loadTBAData(self, event_tba_data):
        self.key = event_tba_data.key
        self.name = event_tba_data.name
        self.event_code = event_tba_data.event_code
        self.event_type = event_tba_data.event_type
        self.city = event_tba_data.city
        self.state = event_tba_data.state_prov
        self.country = event_tba_data.country
        self.start_date = event_tba_data.start_date
        self.end_date = event_tba_data.end_date
        self.year = event_tba_data.year
        self.short_name = event_tba_data.short_name
        self.event_type_string = event_tba_data.event_type_string
        self.week = event_tba_data.week
        self.location_name = event_tba_data.location_name
        self.playoff_type = event_tba_data.playoff_type
        self.playoff_type_string = event_tba_data.playoff_type_string

    def loadTeamKeys(self, tba):
        self.teams = tba.event_teams(self.key, keys=True)


    def hasEventStarted(self):
        return datetime.today().strftime('%Y-%m-%d') >= self.start_date
    
    def isEventGoingOn(self):
        return self.hasEventStarted() and not self.hasEventFinished()

    def hasEventFinished(self):
        return datetime.today().strftime('%Y-%m-%d') > self.end_date

    def isOfficial(self):
        return self.event_type <= 6
    
    def __str__(self):
        return "frcpy_" + str(self.key)

    def getAttr(self, key):
        return self.attrs[key] if key in self.attrs else None