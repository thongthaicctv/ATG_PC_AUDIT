import tempfile,time,unittest
from core.admin_auth import AdminSession,change_password,set_password,validate_password,verify_password

class AdminAuthTests(unittest.TestCase):
    def test_password_hash_change_lockout_and_expiry(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=set_password("Secure123",tmp);text=p.read_text();self.assertNotIn("Secure123",text);self.assertTrue(verify_password("Secure123",tmp));self.assertFalse(verify_password("wrong",tmp))
            change_password("Secure123","NewSecure456",tmp);self.assertTrue(verify_password("NewSecure456",tmp))
            s=AdminSession(lock_seconds=1,session_seconds=1)
            for _ in range(5):s.login("bad",tmp)
            self.assertGreater(s.remaining_lock(),0);s.locked_until=time.time()-1;self.assertTrue(s.login("NewSecure456",tmp)[0]);s.last_activity=time.time()-2;self.assertFalse(s.is_active())

    def test_password_policy(self):
        self.assertFalse(validate_password("short1")[0]);self.assertFalse(validate_password("abcdefgh")[0]);self.assertFalse(validate_password("12345678")[0]);self.assertTrue(validate_password("Valid123")[0])

if __name__=="__main__":unittest.main()
