from planetwars import BaseBot, Game
from planetwars.universe3 import Universe3
from planetwars.planet import Planet
from planetwars.player import PLAYER1, PLAYER2, NOBODY
from planetwars.planet2 import Planet2, getLogger
from planetwars.universe import player, Fleet
from logging import getLogger
import planetwars.planet
from math import ceil
from copy import copy
import random

HORIZON_FIRST = 40
HORIZON = 40
ATTACK_SCORE_THRESHOLD_FIRST = 0
ATTACK_SCORE_THRESHOLD = 140
ATTACK_SCORE_ENEMY_MULTIPLIER = 2

log = getLogger(__name__)

def zeros(rows,cols):
    row = []
    data = []
    for i in range(cols):
        row.append(0)
    for i in range(rows):
        data.append(row[:])
    return data

# v = list of item values or profit
# w = list of item weight or cost
# W = max weight or max cost for the knapsack
def zeroOneKnapsack(v, w, W):
    # c is the cost matrix
    c = []
    n = len(v)
    c = zeros(n,W+1)
    for i in range(0,n):
        #for ever possible weight
        for j in range(0,W+1):
                    #can we add this item to this?
            if (w[i] > j):
                c[i][j] = c[i-1][j]
            else:
                c[i][j] = max(c[i-1][j],v[i] +c[i-1][j-w[i]])
    return [c[n-1][W], getUsedItems(w,c)]

# w = list of item weight or cost
# c = the cost matrix created by the dynamic programming solution
def getUsedItems(w,c):
    # item count
    i = len(c)-1
    currentW =  len(c[0])-1
    # set everything to not marked
    marked = []
    for i in range(i+1):
        marked.append(0)
    while (i >= 0 and currentW >=0):
        if (i==0 and c[i][currentW] >0 )or c[i][currentW] != c[i-1][currentW]:
            marked[i] =1
            currentW = currentW-w[i]
        i = i-1
    return marked

class Move(object):
    def __init__(self, source, target, turn, ship_count):
        self.source = source
        self.target = target
        self.turn = turn
        self.ship_count = int(ship_count)

    def __repr__(self):
        return "Move from %s to %s at turn %s with %s ships" % (self.source, self.target, self.turn, self.ship_count)

class MyBot(BaseBot):

    def __init__(self, universe):
        self.universe = universe
        self.scheduled_moves_at_turn= {}

    def total_fleet_ship_count(self, owner):
        return sum( [ fleet.ship_count for fleet in self.universe.find_fleets(owner) ] )

    def get_neutrals_under_player_attack(self, player):
        result = []
        for planet in self.nobodies_planets:
            if sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner == player ] ) > 0:
                result.append(planet)
        return result

    def get_available_ships_within_distance(self, planet_to_attack, player, distance):
        result = 0
        for planet in (list(self.universe.find_planets(player)) + self.get_neutrals_under_player_attack(player)):
            if planet.id != planet_to_attack.id and planet.distance(planet_to_attack) <= distance and self.ships_needed[planet] == 0:
                ships_avail = self.ships_available_at_turn[planet][distance-planet.distance(planet_to_attack)]
                result += ships_avail
        return result

    def get_attack_score(self, planet_to_attack, future_owner, distance):
        turns = self.max_distance_between_planets - distance + HORIZON
        attack_score = turns * planet_to_attack.growth_rate
        if future_owner in player.ENEMIES:
            attack_score *= ATTACK_SCORE_ENEMY_MULTIPLIER
        return attack_score

    def get_scheduled_fleets_to(self, planet):
        result = []
        for moves in self.scheduled_moves_at_turn.values():
            for move in moves:
                if move.target == planet:
                    distance = move.source.distance(move.target)
                    turns_remaining = distance + (move.turn - self.universe.game.turn_count)
                    fleet = Fleet(self.universe,random.randint(1,1000000),1, move.ship_count, move.source.id, move.target.id, distance, turns_remaining)
                    result.append(fleet)
        return result

    def get_scheduled_fleets_from(self, planet):
        result = []
        for moves in self.scheduled_moves_at_turn.values():
            for move in moves:
                if move.source == planet:
                    turns_remaining = move.turn - self.universe.game.turn_count
                    fleet = Fleet(self.universe,random.randint(1,1000000),1, move.ship_count, move.source.id, move.target.id, turns_remaining, turns_remaining)
                    result.append(fleet)
        return result

    def get_attack_ship_count_first_turn(self, planet_to_attack, my_home, enemy_home):
        my_dist = my_home.distance(planet_to_attack)
        enemy_dist = enemy_home.distance(planet_to_attack)
        if my_dist < enemy_dist:
            return planet_to_attack.ship_count+1
        if my_dist == enemy_dist and planet_to_attack.ship_count <= planet_to_attack.growth_rate:
            return planet_to_attack.ship_count+1
        return 1000000

    def closest_enemy_planet(self, p):
        if len(self.enemy_planets) == 0:
            return None

        sorted_planets = sorted(self.enemy_planets, key=lambda ep : p.distance(ep) + ep.id/1000000.0)
        return sorted_planets[0]

    def closest_enemy_planet_distance(self, p):
        if len(self.enemy_planets) == 0:
            return 1000000
        return min((lambda ep:ep.distance(p))(ep) for ep in self.enemy_planets)

    def my_fleets_attacking(self, planet):
        return sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner == player.ME] )

    def closest_to_enemy_neutral_under_my_attack(self):
        best_distance = 1000000
        result_planet = None
        for planet in self.nobodies_planets:
            if self.my_fleets_attacking(planet) > 0 or planet in self.planets_attacked:
                distance = self.enemy_com.distance(planet)
                if distance < best_distance:
                    best_distance = distance
                    result_planet = planet
        return result_planet

    def decrease_ships_available(self, planet, start_turn, ship_count):
        for turn in range(start_turn, self.max_distance_between_planets + 21):
            self.ships_available_at_turn[planet][turn] -= ship_count

    def send_fleet(self, source, target, ship_count):
        if source.owner == PLAYER1 and ship_count > 0 and ship_count <= source.ship_count:
            source.send_fleet(target, ship_count)
        else:
            log.info("Error sending fleet from %s to %s with % ships" % (source, target, ship_count))

    def doScheduled(self):
        log.info("Scheduled move phase")

        # execute delayed moves first
        if self.scheduled_moves_at_turn.has_key(self.current_turn):
            for move in self.scheduled_moves_at_turn[self.current_turn]:
                if move.ship_count <= move.source.ship_count and move.ship_count > 0 and move.source.owner == PLAYER1 and move.source.ship_count >= move.ship_count:
                    self.send_fleet(move.source, move.target, move.ship_count)
                    self.decrease_ships_available(move.source, 0, move.ship_count)
                else:
                    log.info("Can't execute move: %s,  ships avail: %s" % (move, self.ships_available_at_turn[move.source][0]))
            del self.scheduled_moves_at_turn[self.current_turn]

    def doPrep(self):
        log.info("Prep phase")

        if self.current_turn == 1:
            self.my_home = list(self.my_planets)[0]
            self.enemy_home = list(self.enemy_planets)[0]

        self.max_distance_between_planets = 0
        for p1 in self.all_planets:
            for p2 in self.all_planets:
                self.max_distance_between_planets = max(self.max_distance_between_planets, p1.distance(p2))

        # calculate current high level metrics
        self.total_ships = {PLAYER1:0, PLAYER2:0}
        self.total_growth_rate = {PLAYER1:0, PLAYER2:0}
        self.ships_available_at_turn = {}
        self.ships_needed = {}
        self.ships_needed_at_turn = {}
        self.ships_needed_timeline = {}
        self.planet_timeline = {}

        for planet in self.all_planets:
            self.ships_available_at_turn[planet] = {}
            scheduled_fleets_to_planet = self.get_scheduled_fleets_to(planet)
            scheduled_fleets_from_planet = self.get_scheduled_fleets_from(planet)
            self.planet_timeline[planet] = planet.in_future_timeline(self.max_distance_between_planets + 20, scheduled_fleets_to_planet, scheduled_fleets_from_planet)
            need_help = False
            prev_owner = planet.owner
            for step in self.planet_timeline[planet]:
                owner = step[0]
                ship_count = step[1]
                if owner != prev_owner and prev_owner == planet.owner and prev_owner != NOBODY and not need_help:
                    self.ships_needed[planet] = ship_count
                    self.ships_needed_at_turn[planet] = self.planet_timeline[planet].index(step) + 1
                    need_help = True
                    self.ships_needed_timeline[planet] = [ship_count]
                    #log.info("Planet %s needs help %s at %s" % (planet, ship_count, self.ships_needed_at_turn[planet]))
                if need_help and owner == prev_owner:
                    delta = self.planet_timeline[planet].index(step) + 1 - self.ships_needed_at_turn[planet]
                    ships_needed_delta = ship_count - delta * 2 * planet.growth_rate
                    self.ships_needed_timeline[planet].append(ships_needed_delta)
                prev_owner = owner
            if not need_help:
                self.ships_needed[planet] = 0
                min_available = 1000000
                step_index = len(self.planet_timeline[planet])
                for step in reversed(self.planet_timeline[planet]):
                    ship_count = step[1]
                    min_available = min(min_available, ship_count)
                    if step[0] == NOBODY:
                        min_available = 0
                    if min_available < 0:
                        log.info("Negative min_available: %s for %s" % (min_available, planet))
                        min_available = 0
                    self.ships_available_at_turn[planet][step_index] = min_available
                    #log.info("avail for %s at %s: %s" % (planet, step_index, min_available))
                    step_index -= 1
                self.ships_available_at_turn[planet][0] = max(0,min(planet.ship_count, self.ships_available_at_turn[planet][1] - planet.growth_rate))
            else:
                for step_index in range(0, len(self.planet_timeline[planet])+1):
                    self.ships_available_at_turn[planet][step_index] = 0
            if planet.owner != NOBODY:
                self.total_ships[planet.owner] += planet.ship_count
                self.total_growth_rate[planet.owner] += planet.growth_rate
        self.total_ships[PLAYER1] += self.total_fleet_ship_count(PLAYER1)
        self.total_ships[PLAYER2] += self.total_fleet_ship_count(PLAYER2)

        for my_planet in [self.my_home]:
            for enemy_planet in [self.enemy_home]:
                if my_planet.owner != PLAYER1 or enemy_planet.owner != PLAYER2:
                    continue
                max_enemy_fleet = self.ships_available_at_turn[enemy_planet][0]
                distance = my_planet.distance(enemy_planet)
                ships_needed_for_safety = max_enemy_fleet-(self.planet_timeline[my_planet][distance-1][1] - my_planet.ship_count)
                if ships_needed_for_safety > (my_planet.ship_count - self.ships_available_at_turn[my_planet][0]):
                    deficit = ships_needed_for_safety - (my_planet.ship_count - self.ships_available_at_turn[my_planet][0])
                    #log.info("deficit for %s: %s, max enemy fleet %s" % (my_planet, deficit, max_enemy_fleet))
                    if deficit > self.ships_available_at_turn[my_planet][0]:
                        deficit = self.ships_available_at_turn[my_planet][0]
                    self.decrease_ships_available(my_planet, 0, deficit)
                    #log.info("final ships avail for %s: %s" % (my_planet, self.ships_available_at_turn[my_planet][0]))

        # calculate enemy's center of mass
        weighted_x = 0
        weighted_y = 0
        div = 0
        for planet in self.enemy_planets:
            weighted_x += planet.position.x * (self.ships_available_at_turn[planet][0] + planet.growth_rate)
            weighted_y += planet.position.y * (self.ships_available_at_turn[planet][0] + planet.growth_rate)
            div += self.ships_available_at_turn[planet][0] + planet.growth_rate
        if div == 0:
            div = 1

        self.enemy_com = Planet(self.universe, 666, weighted_x/div, weighted_y/div, 2, 0, 0)

        # For every planet/turn, calculate max aid each player can send
        self.max_aid_at_turn = {PLAYER1:{}, PLAYER2:{}}
        for player in (PLAYER1 | PLAYER2):
            source_planets = list(self.universe.find_planets(player)) + self.get_neutrals_under_player_attack(player)
            for planet in self.all_planets:
                self.max_aid_at_turn[player][planet] = {}
                for turn in range(1, self.max_distance_between_planets+21):
                    max_aid = 0
                    for source_planet in source_planets:
                        if source_planet.id != planet.id and planet.distance(source_planet) < turn:
                            source_planet_time_step = self.planet_timeline[source_planet][turn - planet.distance(source_planet) - 1]
                            if (source_planet_time_step[0] == player):
                                #log.info("Max aid by %s for %s from %s at %s: %s" % (player.id, planet.id, source_planet.id, turn, source_planet_time_step[1]))
                                max_aid += source_planet_time_step[1]
                        else:
                            if source_planet.id != planet.id and planet.distance(source_planet) == turn:
                                if (source_planet.owner == player):
                                    max_aid += source_planet.ship_count
                    self.max_aid_at_turn[player][planet][turn] = max_aid
                    #log.info("Max aid by %s for %s at %s: %s" % (player.id, planet.id, turn, self.max_aid_at_turn[player][planet][turn]))

        log.info("MY STATUS: %s/%s" % (self.total_ships[PLAYER1], self.total_growth_rate[PLAYER1]))
        log.info("ENEMY STATUS: %s/%s" % (self.total_ships[PLAYER2], self.total_growth_rate[PLAYER2]))

    def doDefense(self):
        log.info("Defense phase")

        planets_to_defend = list(self.universe.find_planets(PLAYER1)) + self.get_neutrals_under_player_attack(PLAYER1)
        for planet_to_defend in sorted(planets_to_defend, key=lambda p: p.growth_rate + p.id/1000000.0, reverse=True):
            ships_to_send = self.ships_needed[planet_to_defend]
            if ships_to_send <= 0:
                continue
            min_distance = self.max_distance_between_planets
            max_distance = self.ships_needed_at_turn[planet_to_defend]
            for my_planet in self.my_planets:
                distance = my_planet.distance(planet_to_defend)
                min_distance = min(min_distance, distance)
            min_distance = max(min_distance, 1)
            timeline = [elem for elem in self.ships_needed_timeline[planet_to_defend] if elem > 0]
            ship_counts_to_attempt = sorted(list(set(timeline)), key=lambda p : p, reverse=True)
            #log.info("evaluating defense for %s needed %s" % (planet_to_defend, ship_counts_to_attempt))
            defended = False

            avail_ships_within_distance = {}
            for ships_to_send in ship_counts_to_attempt:
                for distance in range(min_distance, max_distance+1):
                    # calculate if we can get enough ships from my planets to planet_to_defend within 'distance' turns
                    ships_avail_to_defend = 0
                    if avail_ships_within_distance.has_key((planet_to_defend, distance)):
                        ships_avail_to_defend = avail_ships_within_distance[(planet_to_defend, distance)]
                    else:
                        ships_avail_to_defend = self.get_available_ships_within_distance(planet_to_defend, PLAYER1, distance)
                        avail_ships_within_distance[(planet_to_defend, distance)] = ships_avail_to_defend
                    #log.info("Ships avail to defend %s within %s dist: %s" % (planet_to_defend, distance, ships_avail_to_defend))
                    if ships_avail_to_defend >= ships_to_send:
                        ships_left_to_send = ships_to_send
                        for source_planet in sorted(list(self.my_planets) + self.get_neutrals_under_player_attack(PLAYER1), key=lambda p : p.distance(planet_to_defend) + p.id/1000000.0):
                            if self.ships_needed[source_planet] > 0:
                                continue
                            #log.info("evaluating for D: %s" % (source_planet))
                            current_distance = source_planet.distance(planet_to_defend)
                            ships_avail = self.ships_available_at_turn[source_planet][distance-current_distance]
                            if source_planet.id != planet_to_defend.id and ships_avail > 0:
                                #log.info("Ships avail from %s: %s  at dist %s, dist = %s" % (source_planet, ships_avail, current_distance, distance))
                                ships_to_send = min(ships_left_to_send, ships_avail)
                                if current_distance == distance:
                                    #log.info("defending avail from %s: %s  at dist %s" % (source_planet, ships_to_send, current_distance))
                                    self.send_fleet(source_planet, planet_to_defend, ships_to_send)
                                if current_distance < distance:
                                    future_turn = self.current_turn + (distance - current_distance)
                                    future_move = Move(source_planet, planet_to_defend, future_turn, ships_to_send)
                                    log.info("Scheduled move: %s" % future_move)
                                    if not self.scheduled_moves_at_turn.has_key(future_turn):
                                        self.scheduled_moves_at_turn[future_turn] = []
                                    self.scheduled_moves_at_turn[future_turn].append(future_move)
                                ships_left_to_send -= ships_to_send
                                self.decrease_ships_available(source_planet, 0, ships_to_send)
                                if ships_left_to_send == 0:
                                    defended = True
                                    break
                    if defended:
                        break
                if defended:
                    break

    def doFirstTurnOffense(self):
        candidates = []
        candidate_map = {}
        home_planet_distance = self.my_home.distance(self.enemy_home)
        ships_available = min(self.my_home.ship_count, self.my_home.growth_rate * (home_planet_distance+0))

        i = 0
        max_attack_distance=0
        for p in sorted(self.nobodies_planets, key=lambda p : self.get_attack_ship_count_first_turn(p, self.my_home, self.enemy_home) + p.id/1000000.0):
          if p.distance(self.my_home) < p.distance(self.enemy_home) or p.distance(self.my_home) == p.distance(self.enemy_home):
            if p.distance(self.my_home) == p.distance(self.enemy_home) and p.ship_count > 10:
                continue
            candidates.append(p)
            candidate_map[i] = p
            max_attack_distance = max(max_attack_distance, p.distance(self.my_home))
            i += 1

        weights = []
        profits = []
        for c in candidates:
            weight = self.get_attack_ship_count_first_turn(c, self.my_home, self.enemy_home)
            attack_score = (self.max_distance_between_planets - c.distance(self.my_home) + HORIZON_FIRST) * c.growth_rate - (weight - 1)
            if attack_score < ATTACK_SCORE_THRESHOLD_FIRST:
                attack_score = 0
            weights.append(weight)
            profits.append(attack_score)
            #log.info("candidate %s: score %s, weight %s" % (c, attack_score, weight))

        best_planets_to_attack = zeroOneKnapsack(profits,weights,ships_available)
        #log.info("best planets: %s, ships_avail: %s" % (best_planets_to_attack,ships_available))

        sorted_moves = []
        for i in range(len(best_planets_to_attack[1])):
            if (best_planets_to_attack[1][i] != 0):
                planet_to_attack = candidate_map[i]
                ships_to_send = planet_to_attack.ship_count+1
                self.send_fleet(self.my_home, planet_to_attack, ships_to_send)
                self.decrease_ships_available(self.my_home, 0, ships_to_send)
                self.planets_attacked.append(planet_to_attack)

    def doOffense(self):
        log.info("Offense phase")
        if self.current_turn == 1:
            self.doFirstTurnOffense()
            return

        best_planet_to_attack = None
        while True:
            best_planet_to_attack = None
            best_planet_to_attack_score = 0
            best_planet_to_attack_distance = 0
            best_planet_to_attack_ships_to_send = 0
            for planet_to_attack in self.all_planets:
                if planet_to_attack in self.planets_attacked:
                    continue
                min_distance = self.max_distance_between_planets
                max_distance = 0
                for my_planet in self.my_planets:
                    distance = my_planet.distance(planet_to_attack)
                    min_distance = min(min_distance, distance)
                    max_distance = max(max_distance, distance)
                for fleet in self.universe.find_fleets(owner=PLAYER2, destination=planet_to_attack):
                    max_distance = max(max_distance, fleet.turns_remaining)
                #log.info("Max distance for %s: %s" % (planet_to_attack, max_distance))
                min_distance = max(min_distance, 1)
                for distance in range(min_distance, max_distance+1):
                    # calculate how many ships we need to get from my planets to planet_to_attack within 'distance' turns
                    planet_to_attack_future = self.planet_timeline[planet_to_attack][distance-1]
                    planet_to_attack_future_owner = planet_to_attack_future[0]
                    if planet_to_attack_future_owner == PLAYER1:
                        break
                    cost_to_conquer = 0 if planet_to_attack_future_owner == PLAYER2 else -1
                    time_to_profit = 0
                    if planet_to_attack_future_owner == player.NOBODY:
                        cost_to_conquer = planet_to_attack_future[1]
                        time_to_profit = int(ceil((cost_to_conquer+0.001)/planet_to_attack.growth_rate)) if planet_to_attack.growth_rate > 0 else 1000000
                        if planet_to_attack_future_owner == NOBODY and self.enemy_com.distance(planet_to_attack) < distance:
                            break
                    #log.info("Time to profit for %s is %s" % (planet_to_attack, time_to_profit))

                    can_hold = True
                    for turn in range(distance, min(distance+time_to_profit+1, self.max_distance_between_planets + 20)):
                        enemy_max_aid = self.max_aid_at_turn[PLAYER2][planet_to_attack][turn]
                        if planet_to_attack_future_owner == player.PLAYER2:
                            enemy_max_aid += self.planet_timeline[planet_to_attack][turn+time_to_profit-1][1]
                        my_max_aid = self.max_aid_at_turn[PLAYER1][planet_to_attack][turn] - cost_to_conquer + planet_to_attack.growth_rate * (turn-distance)
                        if enemy_max_aid > my_max_aid:
                            can_hold = False
                            #log.info("can't hold %s at turn %s, enemy %s, me %s" % (planet_to_attack, turn, enemy_max_aid, my_max_aid))
                            break
                    if not can_hold:
                        continue

                    simulation_distance = min(distance+time_to_profit, self.max_distance_between_planets + 20)
                    if simulation_distance <= 0:
                        continue
                    enemy_max_aid = self.max_aid_at_turn[PLAYER2][planet_to_attack][simulation_distance]
                    if planet_to_attack_future_owner == player.PLAYER2:
                        enemy_max_aid += self.planet_timeline[planet_to_attack][simulation_distance-1][1]
                    my_max_aid = self.max_aid_at_turn[PLAYER1][planet_to_attack][simulation_distance] - (cost_to_conquer + 1) if planet_to_attack_future_owner == NOBODY else 0
                    if planet_to_attack_future_owner == NOBODY and self.closest_enemy_planet_distance(planet_to_attack) > distance:
                        ships_to_send = cost_to_conquer + 1
                    else:
                        ships_to_send = cost_to_conquer + max(enemy_max_aid - my_max_aid, 0) + 1
                    #log.info("aids for %s at distance %s: enemy %s , me %s, cost %s" % (planet_to_attack, distance, enemy_max_aid, my_max_aid, cost_to_conquer))

                    # calculate if we can get enough ships from my planets to planet_to_attack within 'distance' turns
                    ships_avail_to_attack = self.get_available_ships_within_distance(planet_to_attack, PLAYER1, distance)
                    #log.info("avail to attack: %s, need to send %s" % (ships_avail_to_attack, ships_to_send))
                    if ships_avail_to_attack >= ships_to_send:
                        if self.planet_timeline[planet_to_attack][distance-1][0] in player.ENEMIES and self.planet_timeline[planet_to_attack][distance-2][0] == player.NOBODY:
                            continue

                        attack_score = self.get_attack_score(planet_to_attack, planet_to_attack_future_owner, distance)
                        #log.info("Attack score of %s at dist %s is: %s - %s ships, cost %s" % (planet_to_attack, distance, attack_score, ships_to_send, cost_to_conquer))
                        if planet_to_attack_future_owner in player.ENEMIES or (attack_score-cost_to_conquer) >= ATTACK_SCORE_THRESHOLD:
                            if attack_score > best_planet_to_attack_score:
                                best_planet_to_attack_score = attack_score
                                best_planet_to_attack = planet_to_attack
                                best_planet_to_attack_distance = distance
                                best_planet_to_attack_ships_to_send = ships_to_send
                        break


            if best_planet_to_attack is None:
                return

            log.info("Best planet to attack: %s at dist %s with score %s" % (best_planet_to_attack, best_planet_to_attack_distance, best_planet_to_attack_score))

            ships_left_to_send = best_planet_to_attack_ships_to_send
            source_planets = list(self.my_planets) + self.get_neutrals_under_player_attack(PLAYER1)
            for source_planet in sorted(source_planets, key=lambda p : p.distance(best_planet_to_attack) + p.id/1000000.0):
                distance = source_planet.distance(best_planet_to_attack)
                if distance > best_planet_to_attack_distance:
                    continue
                ships_avail = self.ships_available_at_turn[source_planet][best_planet_to_attack_distance-distance]
                #log.info("ships avail to attack from %s at dist %s: %s" % (source_planet, best_planet_to_attack_distance-distance, ships_avail))
                if self.ships_needed[source_planet] > 0:
                    ships_avail = 0
                if source_planet.id != best_planet_to_attack.id and ships_avail > 0:
                    ships_to_send = min(ships_left_to_send, ships_avail)
                    #log.info("ships to send from %s: %s" % (source_planet, ships_to_send))
                    if distance == best_planet_to_attack_distance and source_planet.owner == PLAYER1:
                        self.send_fleet(source_planet, best_planet_to_attack, ships_to_send)
                    if distance < best_planet_to_attack_distance:
                        future_turn = self.current_turn + (best_planet_to_attack_distance - distance)
                        future_move = Move(source_planet, best_planet_to_attack, future_turn, ships_to_send)
                        log.info("Scheduled move: %s" % future_move)
                        if not self.scheduled_moves_at_turn.has_key(future_turn):
                            self.scheduled_moves_at_turn[future_turn] = []
                        self.scheduled_moves_at_turn[future_turn].append(future_move)
                    ships_left_to_send -= ships_to_send
                    self.decrease_ships_available(source_planet, 0, ships_to_send)
                    if ships_left_to_send == 0:
                        break
            self.planets_attacked.append(best_planet_to_attack)

    def doPostOffense(self):
        log.info("Post-Offense phase")
        if len(self.enemy_planets) == 0:
            return

        planets_to_send_to = copy(self.my_planets)
        neutral_candidate = self.closest_to_enemy_neutral_under_my_attack()
        if neutral_candidate is not None:
            planets_to_send_to = planets_to_send_to | neutral_candidate

        for source_planet in self.my_planets:
            closest_enemy_planet = self.closest_enemy_planet(source_planet)
            #log.info("Eval Post-Offense for %s: closest enemy is %s" % (source_planet, closest_enemy_planet))
            min_distance_to_enemy = 1000000
            dest_planet = None
            for planet_to_send_to in sorted(planets_to_send_to, key=lambda p : p.id if p.id != source_planet.id else 1000000):
                if source_planet.distance(planet_to_send_to) < source_planet.distance(closest_enemy_planet) \
                  and planet_to_send_to.distance(closest_enemy_planet) < min_distance_to_enemy:
                    min_distance_to_enemy = planet_to_send_to.distance(closest_enemy_planet)
                    dest_planet = planet_to_send_to
            if dest_planet is not None and source_planet.id != dest_planet.id and self.ships_available_at_turn[source_planet][0] > 0:
                ships_to_send = min(self.ships_available_at_turn[source_planet][0], source_planet.ship_count)
                self.send_fleet(source_planet, dest_planet, ships_to_send)
                self.decrease_ships_available(source_planet, 0, ships_to_send)

    def do_turn(self):
        self.all_planets = self.universe.all_planets
        self.my_planets = self.universe.my_planets
        self.enemy_planets = self.universe.enemy_planets
        self.nobodies_planets = self.universe.nobodies_planets
        self.not_my_planets = self.universe.not_my_planets
        self.current_turn = self.universe.game.turn_count
        self.planets_attacked = []

        if len(self.my_planets) == 0:
            return

        self.doPrep()
        self.doScheduled()
        self.doDefense()
        self.doOffense()
        self.doPostOffense()


Game(MyBot, universe_class=Universe3, planet_class=Planet2)
