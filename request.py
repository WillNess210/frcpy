from tbapy import TBA
from . import Event, Team
import math
from datetime import datetime

def teamsDictToList(teams):
    return [teams[team] for team in teams]
def teamsListToDict(teams_list):
    teams = {}
    for team in teams_list:
        teams[team.key] = team
    return teams
def getCurrentDate():
    return datetime.today().strftime('%Y-%m-%d')

class TBA_Request:

    def __init__(self, tba_auth_key, year=None):
        self.tba = TBA(tba_auth_key)
        self.all_teams = self.getAllTeams(year=year)
        self.events = {}

    def getAllTeams(self, year=None):
        
        tba_teams = self.tba.teams(year=year, simple=True)
        teams = {} # team key -> Team
        alert_indicies = [math.floor(j * len(tba_teams) * 0.1) for j in list(range(11))]
        for i, tba_team in enumerate(tba_teams):
            team = Team(tba_team.team_number)
            team.loadTBAData(tba_team)
            teams[team.key] = team
            if i in alert_indicies or i + 1 == len(tba_teams):
                print("{}% teams loaded.".format(int((i + 1)/len(tba_teams)*100)))
        return teams

    def getEventsKeys(self, year, current_only=False, must_include_teams = None):
        events = self.tba.events(year, simple = True)
        event_keys = [event.key for event in events]
        if current_only:
            event_keys = [event.key for event in events if event.start_date <= getCurrentDate() and event.end_date >= getCurrentDate()]
        if must_include_teams:
            n_event_keys = []
            for event_key in event_keys:
                event_team_keys = self.tba.event_teams(event_key, keys=True)
                if any([team in must_include_teams for team in event_team_keys]):
                    n_event_keys.append(event_key)
            event_keys = n_event_keys
        return event_keys

    def getEvents(self, year, current_only=False, must_include_teams = None):
        event_keys = self.getEventsKeys(year, current_only=current_only, must_include_teams=must_include_teams)
        return [self.getEvent(event_key) for event_key in event_keys]

    def getEvent(self, event_key):
        ev = Event(event_key)
        ev.loadTBA(self.tba, self.all_teams)
        return ev
        

    def filterTeamList(self, team_dict = None, state=None, country=None, min_number=None, max_number=None, event_code=None):
        if team_dict == None:
            team_dict = self.all_teams
        team_list = teamsDictToList(team_dict)
        if state != None:
            team_list = [team for team in team_list if team.state == state]
        if country != None:
            team_list = [team for team in team_list if team.country == country]
        if min_number != None:
            team_list = [team for team in team_list if team.team_number >= min_number]
        if max_number != None:
            team_list = [team for team in team_list if team.team_number <= max_number]
        if event_code != None:
            event_team_keys = self.tba.event_teams(event_code, keys=True)
            team_list = [team for team in team_list if team.key in event_team_keys]
        return teamsListToDict(team_list)

    def initTeamAttribute(self, key, value):
        for team in self.all_teams:
            self.all_teams[team].attrs[key] = value

    def getRankedTeamListByAttr(self, key, reverse = True, n=10):
        return [v for k, v in sorted(self.all_teams.items(), key = lambda team: team[1].attrs[key], reverse=reverse)][:min(len(self.all_teams), n)]