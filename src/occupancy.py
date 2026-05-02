from collections import defaultdict


class OccupancyMap:
    def __init__(self):
        self._map: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))

    def occupy(self, room_code: str, day: str, periods: set[int]) -> None:
        self._map[room_code][day] |= periods

    def is_available(self, room_code: str, day: str, periods: set[int]) -> bool:
        return not (self._map[room_code][day] & periods)
