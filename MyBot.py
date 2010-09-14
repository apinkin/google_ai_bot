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
class MyBot(BaseBot):

    def endangered(self, p, threshold):
        maxdist = -1
        attackers = p.attacking_fleets
        if len(attackers) == 0:
            return (False,0)
        for a in attackers:
            maxdist = max(maxdist,a.turns_remaining)

        reinforcements = p.reinforcement_fleets
        for r in reinforcements:
            maxdist = max(maxdist,r.turns_remaining)

        fp = p.in_future(maxdist)

        if fp.owner != player.ME or fp.ship_count <= threshold:
            log.info("Endangered %s" % p)
            return (True, fp.ship_count)
        else:
            return (False,0)

    def do_turn(self):
        log.info("I'm starting my turn")

        log.info("Defense")
        mp = self.universe.my_planets
        if len(mp) > 0:
            for dest in mp:
                se = self.endangered(dest, 0)
                if se[0]:
                    ships_needed = se[1]
                    msp = sorted(self.universe.my_planets, key=lambda p : p.distance(dest))

                    for source in msp:
                        if source.id != dest.id and ships_needed <= source.ship_count and (not self.endangered(source, source.ship_count - ships_needed)):
                            source.send_fleet(dest, ships_needed)
                            break

        log.info("Offense")
        ewp = self.universe.weakest_planets(player.NOT_ME,10)
        if len(ewp) > 0:
            for dest in ewp:
                #msp = self.universe.my_strongest_planets(10)
                msp = sorted(self.universe.my_planets, key=lambda p : p.distance(dest))
                for source in msp:
                    dist = source.distance(dest)
                    if dest.owner == player.NOBODY and len(self.universe.enemy_planets) > 0 and dist > (dest.distance(self.universe.enemies_strongest_planet)*1.2):
                        continue

                    fdest = dest.in_future(dist)
                    ships_needed = fdest.ship_count + 1
                    if fdest.owner != player.ME and ships_needed <= source.ship_count and (not self.endangered(source, source.ship_count - ships_needed)[0]):
                        source.send_fleet(dest, ships_needed)
                        break



Game(MyBot, universe_class=Universe2, planet_class=Planet2)
