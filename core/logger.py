import logging
from core.storage_path_manager import active_storage


def configure_logging() -> None:
    log_dir = active_storage().logs_path
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(log_dir / "atg_pc_audit.log", encoding="utf-8")],
    )
