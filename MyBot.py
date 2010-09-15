from planetwars import BaseBot, Game
from planetwars.universe2 import Universe2
from planetwars.planet2 import Planet2
from planetwars.universe import player
from logging import getLogger

log = getLogger(__name__)

# DONE send as many ships as needed
# DONE send only if my planet is not endangered
# DONE defense first
# DONE neutral planets close distance only
# BUG D bug - sometimes bailing before impact..
# BUG sudden losses to bully and random (1-2 turns?)
# BUG sending multiple attacks due to shorter distance than fleet in flight
# Pre-calc all endangered, required re-inforcements and ships to spair
# Test performance with many fleets in flight
class MyBot(BaseBot):

    def max_turns_remaining(self, fleets):
        ret = -1
        for fleet in fleets:
            ret = max(ret, fleet.turns_remaining)
        return ret

    def endangered(self, p, threshold):
        if len(p.attacking_fleets) == 0:
            return (False,0)

        maxdist = self.max_turns_remaining(p.attacking_fleets | p.reinforcement_fleets)
        #maxdist = self.max_turns_remaining(p.attacking_fleets)

        fp = p.in_future(maxdist)

        if fp.owner != player.ME or fp.ship_count <= threshold:
            log.info("Endangered %s" % p)
            return (True, fp.ship_count)
        else:
            return (False,0)

    def do_turn(self):
        log.info("I'm starting my turn")

        mp = self.universe.my_planets
        if len(mp) == 0:
            return

        log.info("Defense")
        for dest in mp:
            se = self.endangered(dest, 0)
            if se[0]:
                ships_needed = se[1]
                msp = sorted(self.universe.my_planets, key=lambda p : p.distance(dest))

                for source in msp:
                    if source.id != dest.id and ships_needed > 0 and ships_needed <= source.ship_count and (not self.endangered(source, source.ship_count - ships_needed)[0]):
                        source.send_fleet(dest, ships_needed)
                        break

        log.info("Offense")
        ewp = self.universe.weakest_planets(player.NOT_ME,10)
        if len(ewp) > 0:
            for dest in ewp:
                msp = sorted(self.universe.my_planets, key=lambda p : p.distance(dest))
                for source in msp:
                    dist = source.distance(dest)
                    if dest.owner == player.NOBODY and len(self.universe.enemy_planets) > 0 and dist > (dest.distance(self.universe.enemies_strongest_planet)*1.2):
                        continue

                    dest_dist = dist
                    #dest_dist = max(dist, self.max_turns_remaining(dest.attacking_fleets | dest.reinforcement_fleets))
                    #dest_dist = max(dist, self.max_turns_remaining(dest.reinforcement_fleets))
                    fdest = dest.in_future(dest_dist)
                    ships_needed = fdest.ship_count + 1
                    if fdest.owner != player.ME and ships_needed <= source.ship_count and (not self.endangered(source, source.ship_count - ships_needed)[0]):
                        source.send_fleet(dest, ships_needed)
                        break



Game(MyBot, universe_class=Universe2, planet_class=Planet2)
