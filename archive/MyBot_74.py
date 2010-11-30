from planetwars import BaseBot, Game
from planetwars.universe2 import Universe2
from planetwars.planet2 import Planet2
from planetwars.universe import player, Fleet
from logging import getLogger, sys
import copy
from copy import copy

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

    def closest_my_planet_distance(self, p):
        return min((lambda mp:mp.distance(p))(mp) for mp in self.universe.my_planets)

    def closest_my_planet_distance(self, p, available_ships):
        return min((lambda mp:mp.distance(p) if available_ships[mp] >0 else 1000000)(mp) for mp in self.universe.my_planets)

    def max_turns_remaining(self, fleets):
        return -1 if len(fleets) == 0 else max((lambda f:f.turns_remaining)(f) for f in fleets)

    def enemy_fleets_attacking(self, planet):
        return sum( [ 1 for fleet in planet.attacking_fleets if fleet.owner in player.NOT_ME ] )

    def calc_home_dist(self):
        self.my_home = list(self.universe.my_planets)[0]
        self.enemy_home = list(self.universe.enemy_planets)[0]
        self.home_dist = self.my_home.distance(self.enemy_home)

    def get_best_planets_to_attack(self, ships_available, count=1, turns=30):
        planet_score = {}
        #log.info("Score eval for %s planets" % len(self.universe.not_my_planets))
        for planet_to_attack in self.universe.not_my_planets:
            log.info("Score eval for %s" % planet_to_attack)
            planet_score[planet_to_attack] = 0

            planet_to_attack_future = planet_to_attack.in_future(turns)
            if planet_to_attack_future.owner == player.ME:
                continue

            my_nearest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(planet_to_attack))
            for source in my_nearest_planets:
                log.info("Score eval source %s" % source)
                distance = source.distance(planet_to_attack)
                if ships_available[source] <= 0 or distance >= turns:
                    continue

                fleet_to_send = Fleet(self.universe,12345,1, ships_available[source], source.id, planet_to_attack.id, distance, distance)
                planet_to_attack_future = planet_to_attack.in_future(turns, fleet_to_send)
                if planet_to_attack_future.owner != player.ME:
                    break

                for ships_to_send in range(1,ships_available[source]+1,10):
                    fleet_to_send = Fleet(self.universe,12345,1, ships_to_send, source.id, planet_to_attack.id, distance, distance)
                    planet_to_attack_future = planet_to_attack.in_future(turns, fleet_to_send)
                    if planet_to_attack_future.owner == player.ME:
                        planet_score[planet_to_attack] = max(planet_score[planet_to_attack], planet_to_attack_future.ship_count - ships_to_send)
                        break
                if planet_score[planet_to_attack] > 0:
                    break
        sorted_planets = sorted(self.universe.not_my_planets, key=lambda p : planet_score[p], reverse=True)
        result = sorted_planets[:count] if count < len(sorted_planets) else sorted_planets
        for p in result:
            if planet_score[p] > 0:
                log.info("Score for %s is %s" % (p,planet_score[p]))

        log.info("Score eval done: %s planets" % len(result))
        return result

    def weakest_not_my_planets_distance_based(self, ships_available, count=1):
        sorted_planets = sorted(self.universe.not_my_planets, \
          key=lambda p : (1.0+p.growth_rate)/(1.0+p.ship_count)/self.closest_my_planet_distance(p, ships_available), reverse=True)
        return sorted_planets[:count] if count < len(sorted_planets) else sorted_planets
        
    def do_turn(self):

        my_planets = self.universe.my_planets
        if len(my_planets) == 0:
            return

        log.info("Prep phase")
        # estimate how many ships are available for each of my planets
        ships_available = {}
        ships_needed = {}
        for planet in my_planets:
            if len(planet.attacking_fleets) == 0:
                ships_available[planet] = planet.ship_count
                ships_needed[planet] = 0
            else:
                simulation_distance = self.max_turns_remaining(planet.attacking_fleets | planet.reinforcement_fleets)
                planet_future = planet.in_future(simulation_distance)
                if planet_future.owner != player.ME:
                    # do we bail if we are going to lose this planet anyway?
                    ships_available[planet] = 0
                    ships_needed[planet] = planet_future.ship_count
                else:
                    ships_available[planet] = planet_future.ship_count - planet.growth_rate * simulation_distance
                    ships_needed[planet] = 0
        log.info("ships_available %s" % ships_available)
        log.info("ships_needed %s" % ships_needed)


        log.info("Defense phase")
        prioritized_planets_to_defend = sorted(self.universe.my_planets, key=lambda p : p.growth_rate, reverse=True)
        for planet_to_defend in prioritized_planets_to_defend:
            if ships_needed[planet_to_defend] > 0:
                current_ships_needed = ships_needed[planet_to_defend]
                log.info("Planet %s needs %s ships!" % (planet_to_defend, current_ships_needed))
                # send reinforcements from closest planets
                my_closest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(planet_to_defend))

                for source in my_closest_planets:
                    if source.id != planet_to_defend.id and ships_available[source] > 0:
                        ships_to_send = min(current_ships_needed, ships_available[source])
                        source.send_fleet(planet_to_defend, ships_to_send)
                        ships_available[source] -= ships_to_send
                        ships_needed[planet_to_defend] -= ships_to_send
                        current_ships_needed -= ships_to_send
                        if current_ships_needed <= 0:
                            break


        log.info("Offense phase")
        # skip one turn if home planets are too close
#        if self.universe.game.turn_count == 1:
#            self.calc_home_dist()
#            if self.home_dist <= 5:
#                return

        #weakest_planets = self.get_best_planets_to_attack(ships_available,10,30)
        weakest_planets = self.universe.weakest_planets(player.NOT_ME,10)
        #weakest_planets = self.weakest_not_my_planets_distance_based(ships_available, 10)
        if len(weakest_planets) == 0:
            return
            
        for planet_to_attack in weakest_planets:
            #log.info("Evaluating attack on %s" % planet_to_attack)
            my_nearest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(planet_to_attack))
            for source in my_nearest_planets:
                if ships_available[source] <= 0:
                    continue
                attack_distance = source.distance(planet_to_attack)
                if planet_to_attack.owner == player.NOBODY and len(self.universe.enemy_planets) > 0 and \
                   attack_distance > (self.closest_enemy_planet_distance(planet_to_attack) * ATTACK_PROXIMITY_RATIO):
                    continue

                simulation_distance = attack_distance
                if planet_to_attack.owner == player.NOBODY:
                    simulation_distance = max(attack_distance, self.max_turns_remaining(planet_to_attack.attacking_fleets))
                planet_to_attack_future = planet_to_attack.in_future(simulation_distance)
                current_ships_needed = planet_to_attack_future.ship_count + 1
                # we currently attack from a single planet within one move
                if planet_to_attack_future.owner != player.ME and current_ships_needed <= ships_available[source]:
                    source.send_fleet(planet_to_attack, current_ships_needed)
                    ships_available[source] -= current_ships_needed
                    break

        log.info("Post-offense phase")
        for source in self.universe.my_planets:
            if ships_available[source] > 0:
                enemy_planets = list(self.universe.find_planets(player.ENEMIES, set([5,4])))
                if len(enemy_planets) > 0:
                    nearest_enemy_planets = sorted(enemy_planets, key=lambda p : p.distance(source))
                    planet_to_attack = nearest_enemy_planets[0]
                    ships_to_send = ships_available[source] / 10
                    if ships_to_send > 0:
                        log.info("Post-offense on %s with %s ships!" % (planet_to_attack, ships_to_send))
                        source.send_fleet(planet_to_attack, ships_to_send)
                        ships_available[source] -= ships_to_send


Game(MyBot, universe_class=Universe2, planet_class=Planet2)
