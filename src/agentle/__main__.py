"""Agentle desktop entry point."""

import os
import sys
from pathlib import Path


def main() -> int:
    from PyQt6.QtWidgets import QApplication, QMessageBox

    from agentle.app import AppConfiguration, runtime_factory
    from agentle.gui.bridge import QtRuntimeClient
    from agentle.gui.main_window import MainWindow

    application = QApplication(sys.argv)
    try:
        configuration = AppConfiguration.from_environment(
            os.environ, current_directory=Path.cwd()
        )
    except ValueError as error:
        QMessageBox.critical(None, "Agentle configuration", str(error))
        return 2
    bridge = QtRuntimeClient(runtime_factory(configuration, os.environ))
    window = MainWindow(bridge)
    window.show()
    window.start()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
