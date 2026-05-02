from src.occupancy import OccupancyMap


class TestOccupancyMap:
    def test_initially_empty(self):
        occ = OccupancyMap()
        assert occ.is_available("101", "월", {4, 5, 6}) is True

    def test_occupy_and_check_conflict(self):
        occ = OccupancyMap()
        occ.occupy("101", "월", {4, 5, 6})
        assert occ.is_available("101", "월", {6, 7, 8}) is False

    def test_no_conflict_different_day(self):
        occ = OccupancyMap()
        occ.occupy("101", "월", {4, 5, 6})
        assert occ.is_available("101", "화", {4, 5, 6}) is True

    def test_no_conflict_different_room(self):
        occ = OccupancyMap()
        occ.occupy("101", "월", {4, 5, 6})
        assert occ.is_available("102", "월", {4, 5, 6}) is True

    def test_adjacent_periods_no_conflict(self):
        occ = OccupancyMap()
        occ.occupy("101", "월", {4, 5, 6})
        assert occ.is_available("101", "월", {7, 8}) is True

    def test_exact_overlap(self):
        occ = OccupancyMap()
        occ.occupy("101", "월", {4, 5, 6})
        assert occ.is_available("101", "월", {4, 5, 6}) is False
