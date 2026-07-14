import unittest
from core.duplicate_checker import find_duplicates
class DuplicateTests(unittest.TestCase):
    def test_duplicates_across_machines(self):
        rows=[{"machine_id":1,"asset_code":"A","serial_number":"S","uuid":"U","primary_mac":"AA","planned_ipv4":"10.0.0.1"},{"machine_id":2,"asset_code":"A","serial_number":"S","uuid":"U","primary_mac":"AA","planned_ipv4":"10.0.0.1"}]
        self.assertEqual({x["type"] for x in find_duplicates(rows)},{"Mã tài sản","Serial","UUID","MAC vật lý","IP dự kiến"})
