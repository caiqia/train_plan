"""
    Coding test: Bookings report for a transportation operator

    Our revenue management solution CAYZN extracts from an inventory system the transport plan of an operator (trains,
    flights or buses with their itineraries, stops and timetable) and allows our users to analyze sales, forecast the
    demand and optimize their pricing.

    In this project you will manipulate related concepts to build a simple report. We will assess your ability to read
    existing code and understand the data model in order to develop new features. Two items are essential: the final
    result, and the quality of your code.

    Questions and example data are at the bottom of the script.

    Good luck!
"""

import datetime

from itertools import islice, groupby
from typing import Iterator, List, Mapping, Tuple


class Service:
    """A service is a facility transporting passengers between two or more stops at a specific departure date.

    A service is uniquely defined by its number and a departure date. It is composed of one or more legs (which
    represent its stops and its timetable), which lead to multiple Origin-Destination (OD) pairs, one for each possible
    trip that a passenger can buy.
    """

    def __init__(self, name: str, departure_date: datetime.date):
        self.name = name
        self.departure_date = departure_date
        self.legs: List[Leg] = []
        self.ods: Mapping[Tuple[Station, Station], OD] = {}

    @property
    def day_x(self):
        """Number of days before departure.

        In revenue management systems, the day-x scale is often preferred because it is more convenient to manipulate
        compared to dates."""
        return (datetime.date.today() - self.departure_date).days

    def load_itinerary(self, itinerary: List["Station"]) -> None:
        """Helper to initialize a Service's `legs` and `ods` attributes"""
        for i, station in enumerate(itinerary):
            if i == 0:
                # This is easier than starting at index 1 and managing an offset
                continue

            for prev in islice(itinerary, i):
                self.ods[(prev, station)] = (OD(self, prev, station))

            # prev == itinerary[i - 1]
            self.legs.append(Leg(self, prev, station))

    def load_passenger_manifest(self, passengers: List["Passenger"]) -> None:
        """Helper to initialize the `passengers` attribute of a Service's `ods`"""
        for passenger in passengers:
            od = self.ods[(passenger.origin, passenger.destination)]
            od.passengers.append(passenger)


class Station:
    """A station is where a service can stop to let passengers board or disembark."""

    def __init__(self, name: str):
        self.name = name


class Leg:
    """A leg is a set of two consecutive stops.

    Example: a service whose itinerary is A-B-C has two legs: A-B and B-C.
    """

    def __init__(self, service: Service, origin: Station, destination: Station):
        self.service = service
        self.origin = origin
        self.destination = destination

    @property
    def passengers(self) -> List["Passenger"]:
        """List of passengers on board (for this leg)"""
        passengers = []
        for od in self.service.ods.values():
            if self not in od.legs:
                continue

            passengers.extend(od.passengers)
        return passengers


class OD:
    """An Origin-Destination (OD) represents the transportation facility between two stops, bought by a passenger.

    Example: a service whose itinerary is A-B-C has up to three ODs: A-B, B-C and A-C.
    """

    def __init__(self, service: Service, origin: Station, destination: Station):
        self.service = service
        self.origin = origin
        self.destination = destination
        self.passengers: List[Passenger] = []

    def _legs(self) -> Iterator[Leg]:
        legs = iter(self.service.legs)

        for leg in legs:
            if leg.origin == self.origin:
                yield leg
                break

        for leg in legs:
            if leg.origin == self.destination:
                break
            yield leg

    @property
    def legs(self) -> List[Leg]:
        """Legs that are contained by an OD

        Example: with a service whose itinerary is A-B-C, the OD A-C contains:
                 A-B and A-C
        """
        return list(self._legs())

    def _history(self) -> Iterator[Tuple[int, int, int]]:
        head_count = wallet = 0
        passengers = sorted(self.passengers, key=lambda p: p.sale_day_x)
        for day_x, passengers in groupby(passengers, lambda p: p.sale_day_x):
            for passenger in passengers:
                head_count += 1
                wallet += passenger.price

            yield day_x, head_count, wallet

    def history(self) -> List[Tuple[int, int, int]]:
        """Return a history of sales as a list of triplets

        Each triplet is of the form: (day_x, total_seats_sold, total_money_made)
        """
        return list(self._history())

    def forecast(
            self,
            pricing: Mapping[int, int],
            demand_matrix: Mapping[int, Mapping[int, int]]
    ) -> Iterator[Tuple[int, int, int]]:
        """Compute and yield a day to day forecast of sales

        Each forecast is of the form: (day_x, total_seats_sold, total_money_made)
        """
        # Let's assume `pricing` and `demand_matrix` have their keys sorted
        # Note: since python 3.7 dict behaves like an OrderedDict

        money = sum(passenger.price for passenger in self.passengers)
        head_count = len(self.passengers)

        for day, demand in demand_matrix.items():
            sold = 0
            for price, count in pricing.items():
                _sold = min(demand[price] - sold, count)
                if _sold <= 0:
                    # XXX: if it was guarantee that the higher the price, the
                    #      less the forecast demand, we could stop right here.
                    continue
                pricing[price] -= _sold
                sold += _sold
                money += price * _sold

            # XXX: we could pop prices from `pricing` as soon as the seat count
            #      goes down to 0. This would avoid iterating over a useless
            #      price again and again.

            head_count += sold
            yield day, head_count, money


class Passenger:
    """A passenger that has a booking on a seat for a particular origin-destination."""

    def __init__(self, origin: Station, destination: Station, sale_day_x: int, price: float):
        self.origin = origin
        self.destination = destination
        self.sale_day_x = sale_day_x
        self.price = price


# Let's create a service to represent a train going from Paris to Marseille with Lyon as intermediate stop. This service
# has two legs and sells three ODs.

ply = Station("ply")  # Paris Gare de Lyon
lpd = Station("lpd")  # Lyon Part-Dieu
msc = Station("msc")  # Marseille Saint-Charles
service = Service("7601", datetime.date.today() + datetime.timedelta(days=7))
leg_ply_lpd = Leg(service, ply, lpd)
leg_lpd_msc = Leg(service, lpd, msc)
service.legs = [leg_ply_lpd, leg_lpd_msc]
od_ply_lpd = OD(service, ply, lpd)
od_ply_msc = OD(service, ply, msc)
od_lpd_msc = OD(service, lpd, msc)
# XXX: this is now broken, but it does not really matter
service.ods = [od_ply_lpd, od_ply_msc, od_lpd_msc]

# 1. Add a property named `legs` in `OD` class, that returns legs that are crossed by a passenger travelling with
# this OD.

assert od_ply_lpd.legs == [leg_ply_lpd]
assert od_ply_msc.legs == [leg_ply_lpd, leg_lpd_msc]
assert od_lpd_msc.legs == [leg_lpd_msc]

# 2. Creating every leg and OD for a service is not convenient, to simplify this step, add a method in `Service` class
# to create legs and ODs associated to list of stations. The signature of this method should be:
# load_itinerary(self, itinerary: List["Station"]) -> None:

itinerary = [ply, lpd, msc]
service = Service("7601", datetime.date.today() + datetime.timedelta(days=7))
service.load_itinerary(itinerary)
assert len(service.legs) == 2
assert service.legs[0].origin == ply
assert service.legs[0].destination == lpd
assert service.legs[1].origin == lpd
assert service.legs[1].destination == msc
assert len(service.ods) == 3
od_ply_lpd = service.ods[(ply, lpd)]
od_ply_msc = service.ods[(ply, msc)]
od_lpd_msc = service.ods[(lpd, msc)]

# 3. Create a method in `Service` class that reads a passenger manifest (a list of all bookings made for this service)
# and that allocates bookings across ODs. When called, it should fill the `passengers` attribute of each OD instances
# belonging to the service. The signature of this method shoud be:
# load_passenger_manifest(self, passengers: List["Passenger"]) -> None:

service.load_passenger_manifest(
    [
        Passenger(ply, lpd, -30, 20),
        Passenger(ply, lpd, -25, 30),
        Passenger(ply, lpd, -20, 40),
        Passenger(ply, lpd, -20, 40),
        Passenger(ply, msc, -10, 50),
    ]
)
assert len(od_ply_lpd.passengers) == 4
assert len(od_ply_msc.passengers) == 1
assert len(od_lpd_msc.passengers) == 0

# 4. Write a property named `passengers` in `Leg` class that returns passengers occupying a seat on this leg.

assert len(service.legs[0].passengers) == 5
assert len(service.legs[1].passengers) == 1

# 5. We want to generate a report about sales made each day, write a `history()` method in `OD` class that returns a
# list of tuples, each tuple should have three elements: (day_x, cumulative number of bookings, cumulative revenue).

history = od_ply_lpd.history()
assert len(history) == 3
assert history[0] == (-30, 1, 20)
assert history[1] == (-25, 2, 50)
assert history[2] == (-20, 4, 130)

# 6. We want to add to our previous report some forecasted data, meaning how many bookings and revenue are forecasted
# for next days. In revenue management, a number of seats is allocated for each prive level. Let's say we only have 5
# price levels from 10€ to 50€. The following variable represents how many seats are available (values of the
# dictionary) at a given price (keys of the dictionary):

pricing = {10: 0, 20: 2, 30: 5, 40: 5, 50: 5}

# We have 2 seats at 20€, 5 at 30€ etc. To forecast our bookings, a deep learning algorithm has outputed for each day-x
# and each price level the number of bookings to expect per day at this price. This is called the demand matrix:

demand_matrix = {
    -7: {10: 5, 20: 1, 30: 0, 40: 0, 50: 0},
    -6: {10: 5, 20: 2, 30: 1, 40: 1, 50: 1},
    -5: {10: 5, 20: 4, 30: 3, 40: 2, 50: 1},
    -4: {10: 5, 20: 5, 30: 4, 40: 3, 50: 1},
    -3: {10: 5, 20: 5, 30: 5, 40: 3, 50: 2},
    -2: {10: 5, 20: 5, 30: 5, 40: 4, 50: 3},
    -1: {10: 5, 20: 5, 30: 5, 40: 5, 50: 4},
    0: {10: 5, 20: 5, 30: 5, 40: 5, 50: 5}
}

# 5 days before departure (D-5), if our price is 20€ then 4 bookings will be made that day. Note that if demand cannot
# be fulfilled for a particular price, all seats available are sold and demand for new price can is used minus bookings
# already made that day. Write a forecast(pricing, demand_matrix) method in OD class to forecast bookings and revenue
# per day-x based on current pricing and demand matrix.

forecast = list(od_ply_lpd.forecast(pricing, demand_matrix))
assert len(forecast) == 8
assert forecast[0] == (-7, 5, 150.0)
assert forecast[1] == (-6, 6, 170.0)
assert forecast[2] == (-5, 9, 260.0)
assert forecast[3] == (-4, 12, 360.0)
assert forecast[4] == (-3, 15, 480.0)
assert forecast[5] == (-2, 18, 620.0)
assert forecast[6] == (-1, 21, 770.0)
assert forecast[7] == (0, 21, 770.0)
