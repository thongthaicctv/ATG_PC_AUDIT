import sys

from PyQt5.QtWidgets import QApplication,QDialog
from PyQt5.QtGui import QIcon

from core.logger import configure_logging
from ui.main_window import MainWindow
from core.resource_utils import resource_path
from core.storage_path_manager import program_data_root
from ui.first_run_storage_dialog import FirstRunStorageDialog
from core.device_id import collect_device_identity
from core.license_cache import LicenseCache
from core.license_client import load_license_config


def has_activated_admin_license(identity_provider=collect_device_identity,
                                cache_provider=LicenseCache,
                                config_provider=load_license_config) -> bool:
    """Only a locally activated Aggregate administrator needs storage setup.

    Startup intentionally reads the encrypted license cache instead of making a
    blocking network request.  A machine becomes an administrator machine after
    its Aggregate license has been checked/activated successfully in the app.
    Employee machines therefore never see the database setup dialog.
    """
    try:
        identity = identity_provider()
        config = config_provider()
        grace_days = int(config.get("offline_grace_days", 30))
        return bool(cache_provider().load(identity.device_id, grace_days).is_valid)
    except Exception:
        # License/cache errors must never prevent an employee from scanning.
        return False


def should_show_storage_setup(bootstrap_path=None) -> bool:
    bootstrap = bootstrap_path or (program_data_root()/"bootstrap.json")
    return not bootstrap.exists() and has_activated_admin_license()


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("ATG PC AUDIT")
    app.setApplicationDisplayName("ATG PC AUDIT")
    app.setWindowIcon(QIcon(str(resource_path("assets/app.ico"))))
    app.setStyle("Fusion")
    if should_show_storage_setup():
        if FirstRunStorageDialog().exec_()!=QDialog.Accepted:return 0
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
