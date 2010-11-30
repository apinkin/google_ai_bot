from planetwars import BaseBot, Game
from planetwars.universe2 import Universe2
from planetwars.planet import Planet
from planetwars.planet2 import Planet2
from planetwars.universe import player, Fleet
from logging import getLogger
import planetwars.planet
from math import ceil
from copy import copy


log = getLogger(__name__)

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
        return min((lambda ep:ep.distance(p))(ep) for ep in self.enemy_planets)

    def my_fleets_attacking(self, planet):
        return sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner == player.ME] )

    def enemy_fleets_latest_attacking(self, planet):
        result = 0
        for fleet in planet.attacking_fleets:
            if fleet.owner in player.NOT_ME:
                result = max(result, fleet.turns_remaining)
        return result
        
    def closest_to_enemy_neutral_under_my_attack(self):
        best_distance = 1000000
        result_planet = None
        for planet in self.nobodies_planets:
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

    def get_neutrals_under_enemy_attack(self):
        result = []
        for planet in self.nobodies_planets:
            if sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner in player.NOT_ME ] ) > 0:
                result.append(planet)
        return result

    def get_neutrals_under_my_attack(self):
        result = []
        for planet in self.nobodies_planets:
            if sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner == player.ME ] ) > 0:
                result.append(planet)
        return result

    def doPrep(self):
        log.info("Prep phase")

        self.max_distance_between_planets = 0
        for p1 in self.all_planets:
            for p2 in self.all_planets:
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
        self.ships_needed_turn = {}
        self.planet_timeline = {}
        for planet in self.all_planets:
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
                prev_owner = planet.owner
                #log.info("timeline for %s: %s" % (planet, self.planet_timeline[planet]))
                for step in self.planet_timeline[planet]:
                    owner = step[0]
                    ship_count = step[1]
                    if owner != prev_owner and prev_owner == player.ME:
                        if ship_count > max_needed:
                            max_needed = ship_count
                            self.ships_needed_turn[planet] = self.planet_timeline[planet].index(step)+1
                    else:
                        if owner == planet.owner:
                            min_available = min(min_available, ship_count)
                    prev_owner = owner
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
            if (planet.owner in player.ENEMIES):
                self.enemy_total_ships_available += self.ships_available[planet]
                self.enemy_total_growth_rate += planet.growth_rate
                self.enemy_total_ships += planet.ship_count
            #log.info("avail ships for %s: %s" % (planet, self.ships_available[planet]))

        # prevent initial overexpansion
        if self.universe.game.turn_count <= 2:
            for my_planet in self.my_planets:
                for enemy_planet in self.enemy_planets:
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
        for planet in self.enemy_planets:
            weighted_x += planet.position.x * (self.ships_available[planet] + planet.growth_rate)
            weighted_y += planet.position.y * (self.ships_available[planet] + planet.growth_rate)
            div += self.ships_available[planet] + planet.growth_rate
        if div == 0:
            div = 1

        self.enemy_com = Planet(self.universe, 666, weighted_x/div, weighted_y/div, 2, 0, 0)

        # For every planet, and every turn, calculate how many ships the enemy CAN sent to it's aid
        self.max_aid_at_turn = {}
        enemy_planets_incl_candidates = list(self.enemy_planets) + self.get_neutrals_under_enemy_attack()
        for planet in self.all_planets:
            self.max_aid_at_turn[planet] = {}
            for turn in range(1, self.max_distance_between_planets+1):
                max_aid = 0
                #for enemy_planet in self.all_planets:
                for enemy_planet in enemy_planets_incl_candidates:
                    if enemy_planet.id != planet.id and planet.distance(enemy_planet) < turn:
                        enemy_planet_time_step = self.planet_timeline[enemy_planet][turn - planet.distance(enemy_planet)]
                        if (enemy_planet_time_step[0] in player.ENEMIES):
                            max_aid += enemy_planet_time_step[1]
                            #max_aid = max(max_aid, enemy_planet_time_step[1])
                            #log.info("adding to max aid: %s" %  enemy_planet_time_step[1])
                    else:
                        if enemy_planet.id != planet.id and planet.distance(enemy_planet) == turn:
                            enemy_planet_time_step = self.planet_timeline[enemy_planet][0]
                            if (enemy_planet_time_step[0] in player.ENEMIES):
                                max_aid += enemy_planet.ship_count
                                #max_aid = max(max_aid, enemy_planet.ship_count)
                if self.planet_timeline[planet][turn-1][0] in player.ENEMIES:
                    max_aid += self.planet_timeline[planet][turn-1][1]
                    #max_aid = max(max_aid, self.planet_timeline[planet][turn-1][1])
                    #log.info("self aid: %s" % self.planet_timeline[planet][turn-1][1])
                self.max_aid_at_turn[planet][turn] = max_aid
                #log.info("Max aid for %s at %s: %s" % (planet.id, turn, self.max_aid_at_turn[planet][turn]))
        #log.info("Max aid: %s" % self.max_aid_at_turn)

        # For every planet, and every turn, calculate how many ships I CAN send to its aid
        self.my_max_aid_at_turn = {}
        self.my_max_aid_at_turn_single = {}
        my_planets_incl_candidates = list(self.my_planets) + self.get_neutrals_under_my_attack()
        for planet in self.all_planets:
            self.my_max_aid_at_turn[planet] = {}
            self.my_max_aid_at_turn_single[planet] = {}
            for turn in range(1, self.max_distance_between_planets+1):
                max_aid = 0
                max_aid_single = 0
                #for my_planet in self.my_planets:
                for my_planet in my_planets_incl_candidates:
                    if my_planet.id != planet.id and planet.distance(my_planet) < turn:
                        my_planet_time_step = self.planet_timeline[my_planet][turn - planet.distance(my_planet)]
                        if (my_planet_time_step[0] == player.ME):
                            max_aid += my_planet_time_step[1]
                            max_aid_single = max(max_aid_single, my_planet_time_step[1])
                            #log.info("adding to my max aid: %s" %  my_planet_time_step[1])
                    else:
                        if my_planet.id != planet.id and planet.distance(my_planet) == turn:
                            my_planet_time_step = self.planet_timeline[my_planet][0]
                            if (my_planet_time_step[0] == player.ME):
                                max_aid += my_planet.ship_count
                                max_aid_single = max(max_aid_single, my_planet.ship_count)
                #if self.planet_timeline[planet][turn-1][0] == player.ME:
                    #max_aid += self.planet_timeline[planet][turn-1][1]
                    #log.info("self aid: %s" % self.planet_timeline[planet][turn-1][1])
                self.my_max_aid_at_turn[planet][turn] = max_aid
                self.my_max_aid_at_turn_single[planet][turn] = max_aid_single
                #log.info("My Max aid for %s at %s: %s" % (planet.id, turn, self.my_max_aid_at_turn[planet][turn]))
        #log.info("My Max aid: %s" % self.my_max_aid_at_turn)

        log.info("MY STATUS: %s/%s - %s available" % (self.my_total_ships, self.my_total_growth_rate, self.my_total_ships_available))
        log.info("ENEMY STATUS: %s/%s - %s available" % (self.enemy_total_ships, self.enemy_total_growth_rate, self.enemy_total_ships_available))
        #log.info("ENEMY COM: %s, %s" % (self.enemy_com.position.x, self.enemy_com.position.y))

    def doDefenseOffense(self):
        log.info("Offense/Defense phase")

        possible_moves = []
        for my_planet in self.my_planets:
            for planet_to_attack in self.all_planets:
                if planet_to_attack.id == my_planet.id:
                    continue
                attack_distance = my_planet.distance(planet_to_attack)
                #simulation_distance = max(attack_distance,self.enemy_fleets_latest_attacking(planet_to_attack))
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

                can_hold = True
                for turn in range(attack_distance,attack_distance+time_to_profit):
                    max_aid = self.max_aid_at_turn[planet_to_attack][turn]
                    my_max_aid = self.my_max_aid_at_turn[planet_to_attack][turn] - (cost_to_conquer + 1)
                    if max_aid > my_max_aid:
                        can_hold = False
                        break
                if not can_hold:
                    continue

                max_aid = self.max_aid_at_turn[planet_to_attack][attack_distance+time_to_profit]
                my_max_aid = self.my_max_aid_at_turn_single[planet_to_attack][attack_distance+time_to_profit] - (cost_to_conquer + 1)
                if planet_to_attack_future_owner == player.NOBODY and attack_distance < self.enemy_com.distance(planet_to_attack):
                    my_max_aid = self.my_max_aid_at_turn[planet_to_attack][attack_distance+time_to_profit] - (cost_to_conquer + 1)

                if planet_to_attack_future_owner in player.ENEMIES:
                    my_max_aid = 0
                ships_to_send = cost_to_conquer + max(max_aid - my_max_aid, 0) + 1
                #log.info("Evaluating attack of %s from %s, max %s, mymax %s, cost %s, ships %s" % (planet_to_attack, my_planet, max_aid, my_max_aid, cost_to_conquer, ships_to_send))
                if planet_to_attack_future_owner != player.ME and ships_to_send > 0 and ships_to_send <= self.ships_available[my_planet]:
                    if self.planet_timeline[planet_to_attack][attack_distance-1][0] in player.ENEMIES and self.planet_timeline[planet_to_attack][attack_distance-2][0] == player.NOBODY:
                        continue
                    attack_score = (self.max_distance_between_planets - attack_distance + 40) * planet_to_attack.growth_rate
                    if planet_to_attack_future_owner in player.ENEMIES:
                        attack_score *= 2

                    can_defend_source = True
                    for enemy_planet in self.enemy_planets:
                        dist = enemy_planet.distance(my_planet)
                        max_aid = self.max_aid_at_turn[my_planet][dist]
                        my_max_aid = self.my_max_aid_at_turn[my_planet][dist] + (my_planet.ship_count-ships_to_send) + my_planet.growth_rate*dist
                        if attack_distance*2<dist and planet_to_attack_future_owner == player.NOBODY:
                            my_max_aid += (dist-attack_distance*2) * planet_to_attack.growth_rate
                        if my_max_aid < max_aid:
                            can_defend_source = False
                            break

                    # let's make sure we are not letting enemy to get a better planet
                    can_enemy_attack_a_better_planet = False
                    for enemy_planet in self.enemy_planets:
                        for planet_to_attack_for_enemy in self.nobodies_planets:
                            if planet_to_attack_for_enemy.id == enemy_planet.id:
                                continue
                            attack_distance = enemy_planet.distance(planet_to_attack_for_enemy)
                            planet_to_attack_for_enemy_future = self.planet_timeline[planet_to_attack_for_enemy][attack_distance-1]
                            planet_to_attack_for_enemy_future_owner =  planet_to_attack_for_enemy_future[0]
                            cost_to_conquer = -1
                            time_to_profit = 0
                            if planet_to_attack_for_enemy_future_owner == player.NOBODY:
                                cost_to_conquer = planet_to_attack_for_enemy_future[1]
                                if planet_to_attack_for_enemy.growth_rate > 0:
                                    time_to_profit = int(ceil((cost_to_conquer+0.001)/planet_to_attack_for_enemy.growth_rate))
                                else:
                                    time_to_profit = 1000000
                                if (time_to_profit+attack_distance) >= self.max_distance_between_planets:
                                    time_to_profit = self.max_distance_between_planets - attack_distance
                            else:
                                if planet_to_attack_for_enemy_future_owner == player.ME:
                                    cost_to_conquer = 0

                            my_max_aid = self.my_max_aid_at_turn[planet_to_attack_for_enemy][attack_distance+time_to_profit] - ships_to_send
                            enemy_max_aid = self.max_aid_at_turn[planet_to_attack_for_enemy][attack_distance+time_to_profit] - (cost_to_conquer + 1)

                            if planet_to_attack_for_enemy_future_owner == player.ME:
                                enemy_max_aid = 0
                            ships_to_send_for_enemy = cost_to_conquer + max(my_max_aid - enemy_max_aid, 0) + 1
                            log.info("Enemy can potentially attack a better planet! %s ships %s" % (planet_to_attack_for_enemy, ships_to_send_for_enemy))
                            #if ships_to_send_for_enemy > 0 and ships_to_send_for_enemy <= (self.ships_available[enemy_planet]+(self.planet_timeline[enemy_planet][0][1]-enemy_planet.ship_count)):
                            if ships_to_send_for_enemy > 0 and ships_to_send_for_enemy <= (self.ships_available[enemy_planet]):
                                enemy_attack_score = (self.max_distance_between_planets - attack_distance + 40) * planet_to_attack_for_enemy.growth_rate
                                if enemy_attack_score > attack_score:
                                    can_enemy_attack_a_better_planet = True
                                    log.info("Enemy can attack a better planet! %s score = %s" % (ships_to_send_for_enemy, enemy_attack_score))
                                    break
                        if can_enemy_attack_a_better_planet:
                            break

                    if (not can_enemy_attack_a_better_planet and can_defend_source):
                        possible_moves.append((my_planet, planet_to_attack, ships_to_send, attack_score))


                    #log.info("Attack score of %s from %s is: %s - %s ships" % (planet_to_attack, my_planet, attack_score, ships_to_send))

        # execute the best moves
        planets_attacked = []
        sorted_moves = sorted(possible_moves, key=lambda m : m[3] + m[1].growth_rate/1000.0 + m[1].id/1000000.0, reverse=True)
        log.info("Best moves: %s" % len(sorted_moves))

        if self.universe.game.turn_count == 1:
            candidates = []
            candidate_map = {}
            my_home = list(self.my_planets)[0]
            enemy_home = list(self.enemy_planets)[0]
            home_planet_distance = my_home.distance(enemy_home)
            ships_available = min(my_home.ship_count, my_home.growth_rate * home_planet_distance)

            i = 0
            max_attack_distance=0
            for p in sorted(self.nobodies_planets, key=lambda p : self.get_attack_ship_count_first_turn(p, my_home, enemy_home) + p.id/1000000.0):
              if p.distance(my_home) < p.distance(enemy_home) or p.distance(my_home) == p.distance(enemy_home):
                if p.distance(my_home) == p.distance(enemy_home) and p.ship_count > 10:
                    continue
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

            best_planets_to_attack = self.zeroOneKnapsack(profits,weights,ships_available)
            #log.info("best planets: %s" % best_planets_to_attack)

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
        #log.info("my current planets: %s" % self.my_planets)

    def doPostOffense(self):
        log.info("Post-Offense phase")
        if len(self.enemy_planets) == 0:
            return

        planets_to_send_to = copy(self.my_planets)
        neutral_candidate = self.closest_to_enemy_neutral_under_my_attack()
        if neutral_candidate is not None and neutral_candidate.ship_count <= 10:
           planets_to_send_to |= neutral_candidate

        # cache closest and com enemy planet distances
        closest_enemy_planet_distance_map = {}
        com_enemy_planet_distance_map = {}
        for planet in planets_to_send_to:
            closest_enemy_planet_distance_map[planet] = self.closest_enemy_planet_distance(planet)
            com_enemy_planet_distance_map[planet] = self.enemy_com.distance(planet)

        my_nearest_to_enemy_planets = sorted(planets_to_send_to, key=lambda p : p.distance(self.enemy_com) +  p.id/1000000.0)

        for source_planet in self.my_planets:
            if self.ships_available[source_planet] > 0:
                log.info("Post-Offense for %s" % source_planet)
                for dest_planet in my_nearest_to_enemy_planets:
                    distance = source_planet.distance(dest_planet)
                    if distance > 0 and distance < com_enemy_planet_distance_map[source_planet]:
                        if com_enemy_planet_distance_map[dest_planet] < com_enemy_planet_distance_map[source_planet] and \
                          closest_enemy_planet_distance_map[dest_planet] <= closest_enemy_planet_distance_map[source_planet]:
                            source_planet.send_fleet(dest_planet, self.ships_available[source_planet])
                            self.ships_available[source_planet] = 0
                            break


    def doDefense(self):
        log.info("Defense phase")
        my_planets_incl_candidates = list(self.my_planets) + self.get_neutrals_under_my_attack()
        prioritized_planets_to_defend = sorted(my_planets_incl_candidates, key=lambda p : p.growth_rate + p.id/1000000.0, reverse=True)
        for planet_to_defend in prioritized_planets_to_defend:
            if self.ships_needed[planet_to_defend] > 0:
                current_ships_needed = self.ships_needed[planet_to_defend]
                #log.info("Planet %s needs %s ships!" % (planet_to_defend, current_ships_needed))
                # send reinforcements from closest planets
                my_closest_planets = sorted(self.my_planets, key=lambda p : p.distance(planet_to_defend) + p.id/1000000.0)

                for source in my_closest_planets:
                    if source.id != planet_to_defend.id and self.ships_available[source] > 0 and source.distance(planet_to_defend) <= self.ships_needed_turn[planet_to_defend]:
                        ships_to_send = min(current_ships_needed, self.ships_available[source])
                        source.send_fleet(planet_to_defend, ships_to_send)
                        self.ships_available[source] -= ships_to_send
                        self.ships_needed[planet_to_defend] -= ships_to_send
                        current_ships_needed -= ships_to_send
                        if current_ships_needed <= 0:
                            break

    def do_turn(self):
        self.all_planets = self.universe.all_planets
        self.my_planets = self.universe.my_planets
        self.enemy_planets = self.universe.enemy_planets
        self.nobodies_planets = self.universe.nobodies_planets

        if len(self.my_planets) == 0:
            return

        self.doPrep()
        self.doDefense()
        self.doDefenseOffense()
        self.doPostOffense()


Game(MyBot, universe_class=Universe2, planet_class=Planet2)
