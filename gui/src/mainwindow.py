from PySide6.QtWidgets import QMainWindow, QFileDialog, QInputDialog, QMessageBox, QLineEdit
from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction
from ui.ui_mainwindow import Ui_MainWindow  # Auto-generated from Qt Designer
from sensor import Sensor  # Your custom QWidget for GPS sensor tabs
import os


class MainWindow(QMainWindow):
    pandarview_path = "/home/Downloads/PandarView2"
    recording_path = "/home/Desktop/AT"
    password = ""
    ntrip_details = {
        "username": "",
        "password": "",
        "ip": "",
        "port": "",
        "mountpoint": ""
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.load_settings()

        # Connect actions
        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self.show_about)
        self.ui.actionPandarView_Path.triggered.connect(
            self.set_pandarview_path)
        self.ui.actionRecording_Path.triggered.connect(self.set_recording_path)
        self.ui.actionSet_Password.triggered.connect(self.set_password)
        self.ui.addSensor.clicked.connect(self.add_sensor_tab)
        self.ui.tabWindow.tabCloseRequested.connect(self.close_tab)

    def load_settings(self):
        settings = QSettings("AT", "ATgui")
        MainWindow.pandarview_path = settings.value(
            "pandarview_path", MainWindow.pandarview_path)
        MainWindow.recording_path = settings.value(
            "recording_path", MainWindow.recording_path)
        MainWindow.password = settings.value("password", MainWindow.password)
        MainWindow.ntrip_details = settings.value(
            "ntrip_details", MainWindow.ntrip_details)

    def save_settings(self):
        settings = QSettings("AT", "ATgui")
        settings.setValue("pandarview_path", MainWindow.pandarview_path)
        settings.setValue("recording_path", MainWindow.recording_path)
        settings.setValue("password", MainWindow.password)
        settings.setValue("ntrip_details", MainWindow.ntrip_details)

    def close_tab(self, index):
        reply = QMessageBox.question(
            self, "Confirmation Close Tab", "Are you sure you want to close this tab?")
        if reply == QMessageBox.Yes:
            self.ui.tabWindow.removeTab(index)

    def add_sensor_tab(self):
        sensor_tab = Sensor(self)
        tab_index = self.ui.tabWindow.addTab(
            sensor_tab, f"GPS {self.ui.tabWindow.count() + 1}")
        self.ui.tabWindow.setCurrentIndex(tab_index)

    def show_about(self):
        QMessageBox.about(self, "Active Transportation Recording",
                          "This is a GUI Program to record GPS and IMU data with ease.\n"
                          "Currently running version 1.0.0.\n"
                          "Credits: Krupal Shah, Jaspreet Singh Chhabra")

    def set_pandarview_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select PandarView Directory")
        if directory:
            MainWindow.pandarview_path = directory
            print("PandarView path set to:", MainWindow.pandarview_path)
            self.save_settings()

    def set_recording_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Recording Directory")
        if directory:
            MainWindow.recording_path = directory
            print("Recording path set to:", MainWindow.recording_path)
            self.save_settings()

    def set_password(self):
        password, ok = QInputDialog.getText(self, "Authentication", "Enter your password:",
                                            QLineEdit.Password)
        if ok and password:
            print("Password entered:", password)
            MainWindow.password = password
            self.save_settings()
        else:
            print("Password input cancelled or empty.")

    def set_ntrip_details(self):
        
