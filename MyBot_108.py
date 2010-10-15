from planetwars import BaseBot, Game
from planetwars.universe2 import Universe2
from planetwars.planet import Planet
from planetwars.planet2 import Planet2
from planetwars.universe import player, Fleet
from logging import getLogger, sys
import planetwars.planet
from math import ceil

log = getLogger(__name__)

# map 46 is non-deterministic against 104
# linear programming to pick best moves
# attack from multiple planets
# defend from multiple planets
# scoring function to 200 turns?
# scoring function needs to take planet's neighbours into account
# overestimating max_aid?
# performance issue
class MyBot(BaseBot):

    def zeros(self,rows,cols):
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
    def zeroOneKnapsack(self, v, w, W):
        # c is the cost matrix
        c = []
        n = len(v)
        c = self.zeros(n,W+1)
        for i in range(0,n):
            #for ever possible weight
            for j in range(0,W+1):
                        #can we add this item to this?
                if (w[i] > j):
                    c[i][j] = c[i-1][j]
                else:
                    c[i][j] = max(c[i-1][j],v[i] +c[i-1][j-w[i]])
        return [c[n-1][W], self.getUsedItems(w,c)]

    # w = list of item weight or cost
    # c = the cost matrix created by the dynamic programming solution
    def getUsedItems(self,w,c):
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

    def total_fleet_ship_count(self, owner):
        return sum( [ fleet.ship_count for fleet in self.universe.find_fleets(owner) ] )

    def closest_enemy_planet_distance(self, p):
        return min((lambda ep:ep.distance(p))(ep) for ep in self.universe.enemy_planets)

    def enemy_ships_reinforcing(self, planet, turn):
        return sum( [ fleet.ship_count for fleet in planet.reinforcement_fleets if fleet.owner in player.NOT_ME and fleet.turns_remaining <= turn ] )

    def my_fleets_attacking(self, planet):
        return sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner == player.ME] )

    def closest_to_enemy_neutral_under_my_attack(self):
        best_distance = 1000000
        result_planet = None
        for planet in self.universe.nobodies_planets:
            if self.my_fleets_attacking(planet) > 0:
                distance = self.enemy_com.distance(planet)
                if distance < best_distance:
                    best_distance = distance
                    result_planet = planet
        return result_planet

    def get_attack_ship_count_first_turn(self, planet_to_attack, my_home, enemy_home):
        my_dist = my_home.distance(planet_to_attack)
        enemy_dist = enemy_home.distance(planet_to_attack)
        #log.info("Distances for %s are %s %s" % (planet_to_attack, my_dist, enemy_dist))
        if my_dist < enemy_dist:
            return planet_to_attack.ship_count+1
        if my_dist == enemy_dist and planet_to_attack.ship_count <= planet_to_attack.growth_rate:
            return planet_to_attack.ship_count+1
        return 1000000

    def doPrep(self):
        log.info("Prep phase")

        self.max_distance_between_planets = 0
        for p1 in self.universe.all_planets:
            for p2 in self.universe.all_planets:
                self.max_distance_between_planets = max(self.max_distance_between_planets, p1.distance(p2))
        #log.info("Max distance: %s" % self.max_distance_between_planets)


        # calculate current high level metrics
        self.my_total_ships_available = 0
        self.my_total_ships = 0
        self.my_total_growth_rate = 0
        self.enemy_total_ships_available = 0
        self.enemy_total_ships = 0
        self.enemy_total_growth_rate = 0
        self.ships_available = {}
        self.ships_needed = {}
        self.planet_timeline = {}
        for planet in self.universe.all_planets:
            if len(planet.attacking_fleets) == 0:
                self.ships_available[planet] = planet.ship_count
                self.ships_needed[planet] = 0
                simulation_distance = self.max_distance_between_planets
                self.planet_timeline[planet] = planet.in_future_timeline(simulation_distance)
            else:
                simulation_distance = self.max_distance_between_planets
                self.planet_timeline[planet] = planet.in_future_timeline(simulation_distance)
                max_needed = 0
                min_available = 1000000
                #log.info("timeline for %s: %s" % (planet, self.planet_timeline[planet]))
                for step in self.planet_timeline[planet]:
                    owner = step[0]
                    ship_count = step[1]
                    if owner != planet.owner:
                        max_needed = max(max_needed, ship_count)
                    else:
                        min_available = min(min_available, ship_count)
                if max_needed > 0:
                    # do we bail if we are going to lose this planet anyway?
                    self.ships_available[planet] = 0
                    self.ships_needed[planet] = max_needed
                else:
                    self.ships_available[planet] = min_available
                    self.ships_needed[planet] = 0

            if (planet.owner == player.ME):
                self.my_total_ships_available += self.ships_available[planet]
                self.my_total_growth_rate += planet.growth_rate
                self.my_total_ships += planet.ship_count
            else:
                self.enemy_total_ships_available += self.ships_available[planet]
                self.enemy_total_growth_rate += planet.growth_rate
                self.enemy_total_ships += planet.ship_count
            #log.info("avail ships for %s: %s" % (planet, self.ships_available[planet]))

        # prevent initial overexpansion
        if self.universe.game.turn_count <= 2:
            for my_planet in self.universe.my_planets:
                for enemy_planet in self.universe.enemy_planets:
                    max_enemy_fleet = self.ships_available[enemy_planet]
                    distance = my_planet.distance(enemy_planet)
                    ships_needed_for_safety = max_enemy_fleet-distance*my_planet.growth_rate
                    if ships_needed_for_safety > (my_planet.ship_count - self.ships_available[my_planet]):
                        deficit = ships_needed_for_safety - (my_planet.ship_count - self.ships_available[my_planet])
                        #log.info("deficit for %s: %s" % (my_planet, deficit))
                        if deficit > self.ships_available[my_planet]:
                            deficit = self.ships_available[my_planet]

                        self.ships_available[my_planet] -= deficit
                        self.my_total_ships_available -= deficit
            
        self.my_total_ships += self.total_fleet_ship_count(player.ME)
        self.enemy_total_ships += self.total_fleet_ship_count(player.NOT_ME)

        # calculate enemy's center of mass
        weighted_x = 0
        weighted_y = 0
        div = 0
        for planet in self.universe.enemy_planets:
            weighted_x += planet.position.x * (self.ships_available[planet] + planet.growth_rate)
            weighted_y += planet.position.y * (self.ships_available[planet] + planet.growth_rate)
            div += self.ships_available[planet] + planet.growth_rate
        if div == 0:
            div = 1

        self.enemy_com = Planet(self.universe, 666, weighted_x/div, weighted_y/div, 2, 0, 0)

        # For every planet, and every turn, calculate how many ships the enemy CAN sent to it's aid
        self.max_aid_at_turn = {}
        for planet in self.universe.all_planets:
            self.max_aid_at_turn[planet] = {}
            for turn in range(1, self.max_distance_between_planets+1):
                max_aid = 0
                #for enemy_planet in self.universe.all_planets:
                for enemy_planet in self.universe.enemy_planets:
                    if enemy_planet.id != planet.id and planet.distance(enemy_planet) < turn:
                        enemy_planet_time_step = self.planet_timeline[enemy_planet][turn - planet.distance(enemy_planet)]
                        if (enemy_planet_time_step[0] in player.ENEMIES):
                            max_aid += enemy_planet_time_step[1]
                            #log.info("adding to max aid: %s" %  enemy_planet_time_step[1])
                    else:
                        if enemy_planet.id != planet.id and planet.distance(enemy_planet) == turn:
                            enemy_planet_time_step = self.planet_timeline[enemy_planet][0]
                            if (enemy_planet_time_step[0] in player.ENEMIES):
                                max_aid += enemy_planet.ship_count
                if self.planet_timeline[planet][turn-1][0] in player.ENEMIES:
                    max_aid += self.planet_timeline[planet][turn-1][1]
                    #log.info("self aid: %s" % self.planet_timeline[planet][turn-1][1])
                self.max_aid_at_turn[planet][turn] = max_aid
                #log.info("Max aid for %s at %s: %s" % (planet.id, turn, self.max_aid_at_turn[planet][turn]))
        #log.info("Max aid: %s" % self.max_aid_at_turn)

        log.info("MY STATUS: %s/%s - %s available" % (self.my_total_ships, self.my_total_growth_rate, self.my_total_ships_available))
        log.info("ENEMY STATUS: %s/%s - %s available" % (self.enemy_total_ships, self.enemy_total_growth_rate, self.enemy_total_ships_available))
        #log.info("ENEMY COM: %s, %s" % (self.enemy_com.position.x, self.enemy_com.position.y))

    def doDefenseOffense(self):
        log.info("Offense/Defense phase")

        possible_moves = []
        for my_planet in self.universe.my_planets:
            for planet_to_attack in self.universe.all_planets:
                if planet_to_attack.id == my_planet.id:
                    continue
                attack_distance = my_planet.distance(planet_to_attack)
                planet_to_attack_future = self.planet_timeline[planet_to_attack][attack_distance-1]
                planet_to_attack_future_owner = planet_to_attack_future[0]
                cost_to_conquer = -1
                time_to_profit = 0
                if planet_to_attack_future_owner == player.NOBODY:
                    cost_to_conquer = planet_to_attack_future[1]
                    if planet_to_attack.growth_rate > 0:
                        time_to_profit = int(ceil((cost_to_conquer+0.001)/planet_to_attack.growth_rate))
                    else:
                        time_to_profit = 1000000
                    if (time_to_profit+attack_distance) >= self.max_distance_between_planets:
                        time_to_profit = self.max_distance_between_planets - attack_distance
                    #log.info("Time to profit for %s is %s" % (planet_to_attack, time_to_profit))
                else:
                    if planet_to_attack_future_owner in player.ENEMIES:
                        cost_to_conquer = 0

                max_aid = self.max_aid_at_turn[planet_to_attack][attack_distance+time_to_profit]
                ships_to_send = cost_to_conquer + max_aid + 1
                if planet_to_attack_future_owner == player.NOBODY and planet_to_attack.distance(self.enemy_com) > planet_to_attack.distance(my_planet) and \
                  (planet_to_attack.distance(self.enemy_com) - planet_to_attack.distance(my_planet)) >= time_to_profit:
                    ships_to_send = cost_to_conquer + 1
                if planet_to_attack_future_owner != player.ME and ships_to_send > 0 and ships_to_send <= self.ships_available[my_planet]:
                    if self.planet_timeline[planet_to_attack][attack_distance-1][0] in player.ENEMIES and self.planet_timeline[planet_to_attack][attack_distance-2][0] == player.NOBODY:
                        continue
                    attack_score = (self.max_distance_between_planets - attack_distance + 40) * planet_to_attack.growth_rate
                    possible_moves.append((my_planet, planet_to_attack, ships_to_send, attack_score))
                    log.info("Attack score of %s from %s is: %s - %s ships" % (planet_to_attack, my_planet, attack_score, ships_to_send))

        # execute the best moves
        planets_attacked = []
        sorted_moves = sorted(possible_moves, key=lambda m : m[3] + m[1].growth_rate/1000.0 + m[1].id/1000000.0, reverse=True)
        log.info("Best moves: %s" % len(sorted_moves))

        if self.universe.game.turn_count == 1:
            candidates = []
            candidate_map = {}
            my_home = list(self.universe.my_planets)[0]
            enemy_home = list(self.universe.enemy_planets)[0]
            home_planet_distance = my_home.distance(enemy_home)
            ships_available = min(my_home.ship_count, my_home.growth_rate * home_planet_distance)

            i = 0
            max_attack_distance=0
            for p in sorted(self.universe.nobodies_planets, key=lambda p : self.get_attack_ship_count_first_turn(p, my_home, enemy_home) + p.id/1000000.0):
              if p.distance(my_home) < p.distance(enemy_home) or p.distance(my_home) == p.distance(enemy_home):
                candidates.append(p)
                candidate_map[i] = p
                max_attack_distance = max(max_attack_distance, p.distance(my_home))
                i += 1

            weights = []
            profits = []
            for c in candidates:
                attack_score = (self.max_distance_between_planets - c.distance(my_home) + 40) * c.growth_rate
                weight = self.get_attack_ship_count_first_turn(c, my_home, enemy_home)
                weights.append(weight)
                profits.append(attack_score)

            log.info("weights: %s" % weights)
            log.info("profits: %s" % profits)
            log.info("available: %s" % ships_available)

            best_planets_to_attack = self.zeroOneKnapsack(profits,weights,ships_available)
            log.info("best planets: %s" % best_planets_to_attack)

            sorted_moves = []
            for i in range(len(best_planets_to_attack[1])):
                if (best_planets_to_attack[1][i] != 0):
                    planet_to_attack = candidate_map[i]
                    sorted_moves.append((my_home, planet_to_attack, planet_to_attack.ship_count+1, 0))

        for move in sorted_moves:
            ships_to_send = move[2]
            planet_to_attack = move[1]
            my_planet = move[0]
            if ships_to_send <= self.ships_available[my_planet] and planet_to_attack not in planets_attacked:
                my_planet.send_fleet(planet_to_attack, ships_to_send)
                self.ships_available[my_planet] -= ships_to_send
                planets_attacked.append(planet_to_attack)

    def doPostOffense(self):
        log.info("Post-Offense phase")
        if len(self.universe.enemy_planets) == 0:
            return

        planets_to_send_to = self.universe.my_planets
        neutral_candidate = self.closest_to_enemy_neutral_under_my_attack()
        if neutral_candidate is not None:
           planets_to_send_to |= neutral_candidate

        # cache closest and com enemy planet distances
        closest_enemy_planet_distance_map = {}
        com_enemy_planet_distance_map = {}
        for planet in planets_to_send_to:
            closest_enemy_planet_distance_map[planet] = self.closest_enemy_planet_distance(planet)
            com_enemy_planet_distance_map[planet] = self.enemy_com.distance(planet)

        my_nearest_to_enemy_planets = sorted(planets_to_send_to, key=lambda p : p.distance(self.enemy_com) +  p.id/1000000.0)

        for source_planet in self.universe.my_planets:
            if self.ships_available[source_planet] > 0:
                #log.info("Post-Offense for %s" % source_planet)
                for dest_planet in my_nearest_to_enemy_planets:
                    distance = source_planet.distance(dest_planet)
                    if distance > 0 and distance < com_enemy_planet_distance_map[source_planet]:
                        if com_enemy_planet_distance_map[dest_planet] < com_enemy_planet_distance_map[source_planet]:
                            source_planet.send_fleet(dest_planet, self.ships_available[source_planet])
                            self.ships_available[source_planet] = 0
                            break


    def do_turn(self):
        if len(self.universe.my_planets) == 0:
            return

        self.doPrep()
        self.doDefenseOffense()
        self.doPostOffense()


Game(MyBot, universe_class=Universe2, planet_class=Planet2)
