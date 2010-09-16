from planetwars.planet import Planet
from planetwars.player import PLAYER_MAP
from copy import copy
import player

class Planet2(Planet):
    def in_future(self, turns=1):
        """Calculates state of planet in `turns' turns."""
        planet = copy(self)

        arriving_fleets = self.universe.find_fleets(destination=self)

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

#                if count > 0:
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