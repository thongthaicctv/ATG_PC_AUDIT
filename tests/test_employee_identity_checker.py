import unittest
from core.employee_identity_checker import find_employee_identity_conflicts


class EmployeeIdentityTests(unittest.TestCase):
    def test_same_code_different_names_is_conflict(self):
        rows=[{"employee_code":"NV01","assigned_user":"Nguyễn A","asset_code":"PC1"},{"employee_code":"nv01","assigned_user":"Nguyễn B","asset_code":"PC2"}]
        self.assertEqual(len(find_employee_identity_conflicts(rows)),1)

    def test_same_employee_can_use_multiple_machines(self):
        rows=[{"employee_code":"NV01","assigned_user":"Nguyễn A","asset_code":"PC1"},{"employee_code":"NV01","assigned_user":"Nguyễn A","asset_code":"PC2"}]
        self.assertEqual(find_employee_identity_conflicts(rows),[])


if __name__=="__main__":unittest.main()
