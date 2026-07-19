import unittest

from core.profile_validator import normalize_employee_code,validate_required_profile_fields,valid_employee_code


class ProfileValidatorTests(unittest.TestCase):
    def test_employee_code_is_trimmed_and_uppercased(self):
        self.assertEqual(normalize_employee_code(" nv-001 "),"NV-001")

    def test_employee_code_format(self):
        self.assertTrue(valid_employee_code("NV_01.2"))
        self.assertFalse(valid_employee_code("NV 01"))
        self.assertFalse(valid_employee_code("NHÂNVIÊN"))

    def test_all_required_fields_are_reported_together(self):
        result=validate_required_profile_fields({"asset_code":"A1","employee_code":"NV 01"})
        self.assertFalse(result["is_valid"])
        self.assertGreaterEqual(len(result["missing_fields"]),4)
        self.assertEqual(result["invalid_fields"][0]["key"],"employee_code")


if __name__=="__main__":unittest.main()
