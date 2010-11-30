from planetwars import BaseBot, Game
from planetwars.universe2 import Universe2
from planetwars.planet import Planet
from planetwars.planet2 import Planet2
from planetwars.universe import player, Fleet
from logging import getLogger, sys
import copy
from copy import copy
import planetwars.planet
import planetwars.planet
import time
import random

log = getLogger(__name__)

ATTACK_PROXIMITY_RATIO = 1.2

# Planet score function adjustment
#   Simulation based on distance, growth and cost - X turns ahead?
#   Raise score of neutrals attacked by enemy first?
# Is multi-attack worth it?
# Move ships to the front lines!
# Slow growth if enemy home nearby
# Smart calculation if to attack neutral (can enemy steal it without losing)
# Strategy adjustment depending on my vs enemy ship count/production
#   Currently over-expanding with no need to

class MyBot(BaseBot):

    def closest_enemy_planet_distance(self, p):
        return min((lambda ep:ep.distance(p))(ep) for ep in self.universe.enemy_planets)

    def average_enemy_planet_distance(self, p):
        distance_sum = sum( [ planet.distance(p) for planet in self.universe.enemy_planets ] )
        if len(self.universe.enemy_planets) == 0:
            return -1
        return distance_sum/len(self.universe.enemy_planets)

    def com_enemy_planet_distance(self, p):
        return self.enemy_com.distance(p)

    def closest_my_planet_distance(self, p):
        return min((lambda mp:mp.distance(p))(mp) for mp in self.universe.my_planets)

    def closest_my_planet_distance(self, p):
        return min((lambda mp:mp.distance(p) if self.ships_available[mp] >0 else 1000000)(mp) for mp in self.universe.my_planets)

    def max_turns_remaining(self, fleets):
        return -1 if len(fleets) == 0 else max((lambda f:f.turns_remaining)(f) for f in fleets)

    def enemy_fleets_attacking(self, planet):
        return sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner in player.NOT_ME ] )

    def my_fleets_attacking(self, planet):
        return sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner == player.ME] )

    def calc_home_dist(self):
        self.my_home = list(self.universe.my_planets)[0]
        self.enemy_home = list(self.universe.enemy_planets)[0]
        self.home_dist = self.my_home.distance(self.enemy_home)

    def get_best_planets_to_attack(self, count=1, turns=30, prod_turns=100):
        planet_score = {}
        #log.info("Score eval for %s planets" % len(self.universe.not_my_planets))
        for planet_to_attack in self.universe.not_my_planets:
            log.info("Score eval for %s" % planet_to_attack)
            planet_score[planet_to_attack] = 0

            planet_to_attack_future = planet_to_attack.in_future(turns)
            if planet_to_attack_future.owner == player.ME:
                continue

            my_nearest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(planet_to_attack) + p.id/1000000.0)
            for source in my_nearest_planets:
                log.info("Score eval source %s" % source)
                distance = source.distance(planet_to_attack)
                if self.ships_available[source] <= 0 or distance >= turns:
                    continue
                if planet_to_attack.owner == player.NOBODY and \
                   distance > (self.closest_enemy_planet_distance(planet_to_attack) * ATTACK_PROXIMITY_RATIO):
                    continue

                fleet_to_send = Fleet(self.universe,12345,1, self.ships_available[source], source.id, planet_to_attack.id, distance, distance)
                planet_to_attack_future = planet_to_attack.in_future(turns, fleet_to_send)
                if planet_to_attack_future.owner != player.ME:
                    continue

                min_ships_to_send = 1
                if len(planet_to_attack.attacking_fleets) == 0:
                    min_ships_to_send = planet_to_attack.ship_count+1

                for ships_to_send in range(1, self.ships_available[source]+1, 1):
                    fleet_to_send = Fleet(self.universe,12345,1, ships_to_send, source.id, planet_to_attack.id, distance, distance)
                    planet_to_attack_future = planet_to_attack.in_future(turns, fleet_to_send)
                    if planet_to_attack_future.owner == player.ME:
                        planet_score[planet_to_attack] = planet_to_attack_future.ship_count - ships_to_send + (prod_turns-distance)*planet_to_attack.growth_rate
                        break
                if planet_score[planet_to_attack] > 0:
                    break
        sorted_planets = sorted(self.universe.not_my_planets, key=lambda p : planet_score[p] + p.id/1000000.0, reverse=True)
        result = sorted_planets[:count] if count < len(sorted_planets) else sorted_planets
        filtered_result = []
        for p in result:
            if planet_score[p] > 0:
                filtered_result.append(p)
        for p in filtered_result:
            if planet_score[p] > 0:
                log.info("Score for %s is %s" % (p,planet_score[p]))

        log.info("Score eval done: %s planets" % len(result))
        return filtered_result

    def weakest_not_my_planets_distance_based(self, count=1):
        sorted_planets = sorted(self.universe.not_my_planets, \
          key=lambda p : (1.0+p.growth_rate)/(1.0+p.ship_count)/self.closest_my_planet_distance(p)+p.id/1000000.0, reverse=True)
        return sorted_planets[:count] if count < len(sorted_planets) else sorted_planets

    def total_fleet_count_enroute(self, owner, planet):
        return sum( [ fleet.ship_count for fleet in self.universe.find_fleets(owner, destination = planet) ] )

    def effective_fleet_ship_count_enroute(self, owner, planet):
        result = 0
        for fleet in self.universe.find_fleets(destination = planet):
            if fleet.owner == owner:
                result += fleet.ship_count
            else:
                result -= fleet.ship_count
        return result

    def total_fleet_ship_count(self, owner):
        return sum( [ fleet.ship_count for fleet in self.universe.find_fleets(owner) ] )


    def weakest_not_my_planets_effective(self, count=1):
        sorted_planets = sorted(self.universe.not_my_planets, \
          key=lambda p : (1.0+p.growth_rate)/(1.0+p.ship_count-self.total_fleet_count_enroute(player.ME, p)+self.total_fleet_count_enroute(player.NOT_ME, p)) + p.id/1000000.0, reverse=True)
        return sorted_planets[:count] if count < len(sorted_planets) else sorted_planets

    def invert_owner(self, owner):
        if owner == player.ME:
            return player.NOT_ME
        else:
            return player.ME

    # calculate how many ships are available or needed for each of my and enemy planets
    def doPrep(self):
        log.info("Prep phase")

        # calculate current high level metrics
        self.my_total_ships_available = 0
        self.my_total_ships = 0
        self.my_total_growth_rate = 0
        self.enemy_total_ships_available = 0
        self.enemy_total_ships = 0
        self.enemy_total_growth_rate = 0
        self.ships_available = {}
        self.ships_needed = {}
        for planet in self.universe.my_planets | self.universe.enemy_planets:
            if len(planet.attacking_fleets) == 0:
                self.ships_available[planet] = planet.ship_count
                self.ships_needed[planet] = 0
            else:
                simulation_distance = self.max_turns_remaining(planet.attacking_fleets | planet.reinforcement_fleets)
                planet_timeline = planet.in_future_timeline(simulation_distance)
                max_needed = 0
                min_available = 1000000
                log.info("timeline for %s: %s" % (planet, planet_timeline))
                for step in planet_timeline:
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



        self.my_total_ships += self.total_fleet_ship_count(player.ME)
        self.enemy_total_ships += self.total_fleet_ship_count(player.NOT_ME)

        # calculate enemy's center of mass
        weighted_x = 0
        weighted_y = 0
        div = 0
        for planet in self.universe.enemy_planets:
            weighted_x += planet.position.x * self.ships_available[planet]
            weighted_y += planet.position.y * self.ships_available[planet]
            div += self.ships_available[planet]
        if div == 0:
            div = 1

        self.enemy_com = Planet(self.universe, 666, weighted_x/div, weighted_y/div, 2, 0, 0)

        log.info("MY STATUS: %s/%s - %s available" % (self.my_total_ships, self.my_total_growth_rate, self.my_total_ships_available))
        log.info("ENEMY STATUS: %s/%s - %s available" % (self.enemy_total_ships, self.enemy_total_growth_rate, self.enemy_total_ships_available))
        log.info("ENEMY COM: %s, %s" % (self.enemy_com.position.x, self.enemy_com.position.y))

    def doDefense(self):
        log.info("Defense phase")
        prioritized_planets_to_defend = sorted(self.universe.my_planets, key=lambda p : p.growth_rate + p.id/1000000.0, reverse=True)
        for planet_to_defend in prioritized_planets_to_defend:
            if self.ships_needed[planet_to_defend] > 0:
                current_ships_needed = self.ships_needed[planet_to_defend]
                log.info("Planet %s needs %s ships!" % (planet_to_defend, current_ships_needed))
                # send reinforcements from closest planets
                my_closest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(planet_to_defend) + p.id/1000000.0)

                for source in my_closest_planets:
                    if source.id != planet_to_defend.id and self.ships_available[source] > 0:
                        ships_to_send = min(current_ships_needed, self.ships_available[source])
                        source.send_fleet(planet_to_defend, ships_to_send)
                        self.ships_available[source] -= ships_to_send
                        self.ships_needed[planet_to_defend] -= ships_to_send
                        current_ships_needed -= ships_to_send
                        if current_ships_needed <= 0:
                            break


    def doOffense(self):
        log.info("Offense phase")
        #weakest_planets = self.universe.weakest_planets(player.NOT_ME,10)
        #weakest_planets = self.weakest_not_my_planets_effective(10)
        weakest_planets = self.get_best_planets_to_attack(10,15,50)
        #weakest_planets = self.weakest_not_my_planets_distance_based(10)
        #log.info("Weakest planets: %s" % weakest_planets)

        for planet_to_attack in weakest_planets:
            log.info("Evaluating attack on %s" % planet_to_attack)
            my_nearest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(planet_to_attack) + p.id/1000000.0)
            for source in my_nearest_planets:
                if self.ships_available[source] <= 0:
                    continue
                attack_distance = source.distance(planet_to_attack)

                # see if we can steal
                steal = False
                if planet_to_attack.owner == player.NOBODY and self.enemy_fleets_attacking(planet_to_attack) == 1 and \
                   self.my_fleets_attacking(planet_to_attack) == 0:
                    enemy_fleet = list(self.universe.find_fleets(player.NOT_ME, destination = planet_to_attack))[0]
                    if attack_distance == (enemy_fleet.turns_remaining+1) and self.ships_available[source]>=(planet_to_attack.growth_rate+2) and \
                       enemy_fleet.ship_count == (planet_to_attack.ship_count+1):
                        log.info("Need to steal %s, fleet inbound %s" % (planet_to_attack,enemy_fleet))
                        steal = True
                    else:
                        continue

                if planet_to_attack.owner == player.NOBODY and \
                   steal == False and \
                   attack_distance > (self.closest_enemy_planet_distance(planet_to_attack) * ATTACK_PROXIMITY_RATIO):
                    continue

                simulation_distance = attack_distance
                if planet_to_attack.owner == player.NOBODY:
                    simulation_distance = max(attack_distance, self.max_turns_remaining(planet_to_attack.attacking_fleets))
                planet_to_attack_future = planet_to_attack.in_future(simulation_distance)
                current_ships_needed = planet_to_attack_future.ship_count + 1
                # we currently attack from a single planet within one move
                log.info("Future eval for %s is %s, simul dist %s" % (planet_to_attack_future.owner,current_ships_needed, simulation_distance))
                if planet_to_attack_future.owner != player.ME:
                    if planet_to_attack.owner == player.NOBODY:
                        if current_ships_needed <= self.ships_available[source]:
                            source.send_fleet(planet_to_attack, current_ships_needed)
                            self.ships_available[source] -= current_ships_needed
                            break
                    else:
                        if current_ships_needed <= self.ships_available[source]:
                            source.send_fleet(planet_to_attack, current_ships_needed)
                            self.ships_available[source] -= current_ships_needed
                            break

    def doPostOffense(self):
        log.info("Post-Offense phase")
        if len(self.universe.enemy_planets) == 0:
            return

        # cache closest and com enemy planet distances
        closest_enemy_planet_distance_map = {}
        com_enemy_planet_distance_map = {}
        for planet in self.universe.my_planets:
            closest_enemy_planet_distance_map[planet] = self.closest_enemy_planet_distance(planet)
            com_enemy_planet_distance_map[planet] = self.com_enemy_planet_distance(planet)

        for source_planet in self.universe.my_planets:
            if self.ships_available[source_planet] > 0:
                log.info("Post-Offense for %s" % source_planet)
                my_nearest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(source_planet) +  p.id/1000000.0)
                for dest_planet in my_nearest_planets:
                    distance = source_planet.distance(dest_planet)
                    if distance > 0 and closest_enemy_planet_distance_map[dest_planet] <= closest_enemy_planet_distance_map[source_planet]:
                        if com_enemy_planet_distance_map[dest_planet] < com_enemy_planet_distance_map[source_planet]:
                            source_planet.send_fleet(dest_planet, self.ships_available[source_planet])
                            self.ships_available[source_planet] = 0
                            break


    def do_turn(self):
        if len(self.universe.my_planets) == 0 or len(self.universe.enemy_planets) == 0:
            return

        self.doPrep()
        self.doDefense()
        self.doOffense()
        self.doPostOffense()


Game(MyBot, universe_class=Universe2, planet_class=Planet2)
