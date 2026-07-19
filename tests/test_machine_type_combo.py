import os,unittest
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PyQt5.QtWidgets import QApplication,QComboBox
from ui.main_window import MainWindow

class MachineTypeComboTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_machine_type_has_exact_three_choices(self):
        window=MainWindow();field=window.fields["asset_code"]
        self.assertIsInstance(field,QComboBox)
        self.assertEqual([field.itemText(i) for i in range(field.count())],["Bộ PC","Laptop","Máy tính bảng"])
        self.assertGreater(window.fields["department"].count(),1)
        self.assertEqual(window.template_button.text(),"CÀI ĐẶT BIỂU MẪU")
        field.setCurrentText("Máy tính bảng");self.assertEqual(window.metadata()["asset_code"],"Máy tính bảng")
        window.close()

if __name__=="__main__":unittest.main()
