from planetwars.planet import Planet
from planetwars.player import PLAYER_MAP
from copy import copy
from logging import log, getLogger
import player

log = getLogger(__name__)

class Planet2(Planet):
    def in_future(self, turns=1, fleet=None):
        """Calculates state of planet in `turns' turns."""
        planet = copy(self)

        arriving_fleets = self.universe.find_fleets(destination=self)
        if fleet is not None:
            arriving_fleets |= fleet

        for i in range(1, turns+1):
            # account planet growth
            if planet.owner != player.NOBODY:
                planet.ship_count = planet.ship_count + self.growth_rate

            # get fleets which will arrive in that turn
            fleets = [ x for x in arriving_fleets if x.turns_remaining == i ]

            # assuming 2-player scenario!
            ships = []
            for id in [1,2]:
                count = sum( [ x.ship_count for x in fleets if x.owner == PLAYER_MAP.get(int(id)) ] )
                if PLAYER_MAP[id] == planet.owner:
                    count += planet.ship_count

#            if count > 0:
                ships.append({'player':PLAYER_MAP.get(id), 'ships':count})

            # neutral planet has own fleet
            if planet.owner == player.NOBODY:
                ships.append({'player':player.NOBODY,'ships':planet.ship_count})

            # calculate outcome
            if len(ships) > 1:
                s = sorted(ships, key=lambda s : s['ships'], reverse=True)

                winner = s[0]
                second = s[1]

                if winner['ships'] == second['ships']:
                    planet.ship_count=0
                else:
                    planet.owner=winner['player']
                    planet.ship_count=winner['ships'] - second['ships']

        return planet

    def in_future_timeline(self, turns=1):
        """Calculates state of planet in `turns' turns."""
        result = []
        planet = copy(self)

        arriving_fleets = self.universe.find_fleets(destination=self)
        for i in range(1, turns+1):
            # account planet growth
            if planet.owner != player.NOBODY:
                planet.ship_count = planet.ship_count + self.growth_rate

            # get fleets which will arrive in that turn
            fleets = [ x for x in arriving_fleets if x.turns_remaining == i ]
            #log.info("arriving at %s: %s" % (i,fleets))

            # assuming 2-player scenario!
            ships = []
            for id in [1,2]:
                count = sum( [ x.ship_count for x in fleets if x.owner == PLAYER_MAP.get(int(id)) ] )
                if PLAYER_MAP[id] == planet.owner:
                    count += planet.ship_count

#            if count > 0:
                ships.append({'player':PLAYER_MAP.get(id), 'ships':count})

            # neutral planet has own fleet
            if planet.owner == player.NOBODY:
                ships.append({'player':player.NOBODY,'ships':planet.ship_count})

            # calculate outcome
            if len(ships) > 1:
                s = sorted(ships, key=lambda s : s['ships'], reverse=True)

                winner = s[0]
                second = s[1]

                if winner['ships'] == second['ships']:
                    planet.ship_count=0
                else:
                    planet.owner=winner['player']
                    planet.ship_count=winner['ships'] - second['ships']
            result.append((planet.owner, planet.ship_count))
        return result

    def in_future_timeline(self, turns=1, fleets=None, departingFleets=None):
        """Calculates state of planet in `turns' turns."""
        result = []
        planet = copy(self)

        arriving_fleets = list(self.universe.find_fleets(destination=self))
        if fleets is not None:
            arriving_fleets += fleets

        for i in range(1, turns+1):
            # account planet growth
            if planet.owner != player.NOBODY:
                planet.ship_count = planet.ship_count + self.growth_rate

            # get fleets which will arrive in that turn
            fleets = [ x for x in arriving_fleets if x.turns_remaining == i ]
#            if planet.id == 4:
#                log.info("arriving at %s fleets: %s" % (i,fleets))

            # assuming 2-player scenario!
            ships = []
            for id in [1,2]:
                count = sum( [ x.ship_count for x in fleets if x.owner == PLAYER_MAP.get(int(id)) ] )
                if PLAYER_MAP[id] == planet.owner:
                    count += planet.ship_count

#            if count > 0:
                ships.append({'player':PLAYER_MAP.get(id), 'ships':count})

            # neutral planet has own fleet
            if planet.owner == player.NOBODY:
                ships.append({'player':player.NOBODY,'ships':planet.ship_count})

            # calculate outcome
            if len(ships) > 1:
                s = sorted(ships, key=lambda s : s['ships'], reverse=True)

                winner = s[0]
                second = s[1]

                if winner['ships'] == second['ships']:
                    planet.ship_count=0
                else:
                    planet.owner=winner['player']
                    planet.ship_count=winner['ships'] - second['ships']

            # get fleets which will depart in that turn
            if departingFleets is not None:
                fleets = [ x for x in departingFleets if x.turns_remaining == i ]
                for fleet in fleets:
                    planet.ship_count -= fleet.ship_count

            result.append((planet.owner, planet.ship_count))
        return result
