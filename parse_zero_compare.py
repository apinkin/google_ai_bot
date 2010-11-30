import urllib2
import sys
from BeautifulSoup import BeautifulSoup

PLAYER_NAMES = sys.argv[1:]
PLAYER_PAGE_URL = "http://zeroviz.us:8080/%s.html"

def parse_player(player):
    total_games = 0
    games_by_player = {}
    game_results_by_player = {}
    game_result_counts = {"win" : 0, "loss" : 0, "draw" : 0}

    page = urllib2.urlopen(PLAYER_PAGE_URL % player)
    soup = BeautifulSoup(page)

    table = soup.findAll( "table" )[0]
    rows = table( "tr" )
    for row in rows[1:]:
        player = row("td")[1]("a")[0].string
        map = row("td")[2]("a")[0].string
        result = row("td")[3]("span")[0]['class']
        #print player, map, result

        total_games += 1
        game_result_counts[result] += 1
        if games_by_player.has_key(player):
            games_by_player[player] += 1
            game_results_by_player[player][result] += 1
        else:
            games_by_player[player] = 1
            game_results_by_player[player] = {"win" : 0, "loss" : 0, "draw" : 0}
            game_results_by_player[player][result] += 1

    return (games_by_player, game_results_by_player, game_result_counts)

stats_games_by_player = {}
stats_game_results_by_player = {}
stats_game_result_counts = {}

for cplayer in PLAYER_NAMES:
    stats_games_by_player[cplayer], stats_game_results_by_player[cplayer], stats_game_result_counts[cplayer] = parse_player(cplayer)
    print "Statistics for %s: wins %s, losses %s, draws %s\n" % (cplayer, stats_game_result_counts[cplayer]["win"], stats_game_result_counts[cplayer]["loss"], stats_game_result_counts[cplayer]["draw"])

    for player in sorted(stats_game_results_by_player[cplayer].keys()):
        print "%s: wins %s, losses %s, draws %s" % (player, stats_game_results_by_player[cplayer][player]["win"], stats_game_results_by_player[cplayer][player]["loss"], stats_game_results_by_player[cplayer][player]["draw"])

# comparison if there are multiple player names
player_intersection = set(stats_game_results_by_player[PLAYER_NAMES[0]].keys())
if len(PLAYER_NAMES) > 1:
    for player in PLAYER_NAMES[1:]:
        player_intersection = player_intersection.intersection(set(stats_game_results_by_player[player].keys()))

    print "\nStats comparison:\n"

#    for player in sorted(player_intersection):
#        for cplayer in PLAYER_NAMES:
#            print "%s against %s: wins %s, losses %s, draws %s" % (cplayer, player, stats_game_results_by_player[cplayer][player]["win"], stats_game_results_by_player[cplayer][player]["loss"], stats_game_results_by_player[cplayer][player]["draw"])

    total_wins = {}
    total_losses = {}
    for cplayer in PLAYER_NAMES:
        total_wins[cplayer] = 0
        total_losses[cplayer] = 0

    for player in sorted(player_intersection):
        pstr = player + ": "
        for cplayer in PLAYER_NAMES:
            win = stats_game_results_by_player[cplayer][player]["win"]
            total_wins[cplayer] += win
            loss = stats_game_results_by_player[cplayer][player]["loss"]
            total_losses[cplayer] += loss
            wl_ratio = win*100/(win+loss)
            pstr = pstr + cplayer + ": " + str(wl_ratio) + " %, "
        print pstr

    print "\nTotals comparison:\n"
    for cplayer in PLAYER_NAMES:
        win = total_wins[cplayer]
        loss = total_losses[cplayer]
        wl_ratio = win*100/(win+loss)
        print "%s Totals: %s win ratio, %s wins, %s losses" % (cplayer, wl_ratio, win, loss)
        