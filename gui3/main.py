# main.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
# this is the auto-generated file from Qt Designer
from mainwindow import MainWindow
import logging
logging.basicConfig(level=logging.DEBUG)  # or INFO
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()  # should be a proper QMainWindow subclass
        window.show()
        logger.debug("MainWindow launched successfully.")
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        logger.error("Exception occurred during startup:\n" +
                     traceback.format_exc())
