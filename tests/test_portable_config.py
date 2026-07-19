import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from core.resource_utils import resource_path


class PortableConfigTests(unittest.TestCase):
    def test_portable_config_next_to_frozen_exe_has_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);exe=root/"ATG_PC_AUDIT.exe";config=root/"data"/"config"/"app_config.json";config.parent.mkdir(parents=True);config.write_text(json.dumps({"portable":True}),encoding="utf-8")
            with patch.object(sys,"frozen",True,create=True),patch.object(sys,"executable",str(exe)):
                selected=resource_path("config/app_config.json")
                self.assertTrue(json.loads(selected.read_text(encoding="utf-8"))["portable"])


if __name__=="__main__":unittest.main()
