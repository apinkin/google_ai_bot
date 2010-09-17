from planetwars import BaseBot, Game
from planetwars.universe2 import Universe2
from planetwars.planet2 import Planet2
from planetwars.universe import player
from logging import getLogger, sys
import copy
from copy import copy

log = getLogger(__name__)

ATTACK_PROXIMITY_RATIO = 1.2

# Try to steal neutrals
# Is multi-attack worth it?
# Move ships to the front lines!
# Slow growth if enemy home nearby
# Smart calculation if to attack neutral (can enemy steal it without losing)
# Strategy adjustment depending on my vs enemy ship count/production

class MyBot(BaseBot):

    def closest_enemy_planet_distance(self, p):
        return min((lambda ep:ep.distance(p))(ep) for ep in self.universe.enemy_planets)

    def max_turns_remaining(self, fleets):
        return -1 if len(fleets) == 0 else max((lambda f:f.turns_remaining)(f) for f in fleets)

    def calc_home_dist(self):
        if self.universe.game.turn_count == 1:
            for p in self.universe.my_planets:
                self.my_home = p
            for p in self.universe.enemy_planets:
                self.enemy_home = p
            self.home_dist = self.my_home.distance(self.enemy_home)

    def do_turn(self):
        log.info("I'm starting my turn %s" % self.universe.game.turn_count)

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
                ships_needed[planet] = int(0)
            else:
                simulation_distance = self.max_turns_remaining(planet.attacking_fleets | planet.reinforcement_fleets)
                planet_future = planet.in_future(simulation_distance)
                if planet_future.owner != player.ME:
                    # do we bail if we are going to lose this planet anyway?
                    ships_available[planet] = 0
                    ships_needed[planet] = planet_future.ship_count
                else:
                    ships_available[planet] = planet_future.ship_count
                    ships_needed[planet] = 0
        #log.info("ships_available %s" % ships_available)
        #log.info("ships_needed %s" % ships_needed)


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
        weakest_planets = self.universe.weakest_planets(player.NOT_ME,10)
        if len(weakest_planets) == 0:
            return
            
        for planet_to_attack in weakest_planets:
            #log.info("Evaluating attack on %s" % planet_to_attack)
            my_nearest_planets = sorted(self.universe.my_planets, key=lambda p : p.distance(planet_to_attack))
            for source in my_nearest_planets:
                if ships_available[source] <= 0:
                    continue
                attack_distance = source.distance(planet_to_attack)
                if planet_to_attack.owner == player.NOBODY and len(self.universe.enemy_planets) > 0 and attack_distance > (self.closest_enemy_planet_distance(planet_to_attack)*1.2):
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



Game(MyBot, universe_class=Universe2, planet_class=Planet2)
