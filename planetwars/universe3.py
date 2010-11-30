# vim:ts=4:shiftwidth=4:et

from planetwars.universe2 import Universe2
from planetwars.util import ParsingException, _make_id, SetDict
from planetwars.fleet import Fleet, Fleets
from planetwars.planet import Planet, Planets
from planetwars import player
from planetwars.player import Players
from logging import getLogger

log = getLogger(__name__)

class Universe3(Universe2):
    def send_fleet(self, source, destination, ship_count):
        log.debug("Sending fleet of %d from %s to %s." % (ship_count, source, destination))
        if isinstance(destination, set):
            new_fleets = Fleets()
            for target in destination:
                source.ship_count -= ship_count
                self.game.send_fleet(source.id, target.id, ship_count)
                trip_length = source.distance(target)
                #new_fleets.add(self._add_fleet(player.ME.id, ship_count, source.id, target.id, trip_length, trip_length))
            return new_fleets
        else:
            source.ship_count -= ship_count
            self.game.send_fleet(source.id, destination.id, ship_count)
            trip_length = source.distance(destination)
            #return self._add_fleet(player.ME.id, ship_count, source.id, destination.id, trip_length, trip_length)
            return None
