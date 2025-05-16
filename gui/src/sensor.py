from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import QProcess, QUrl, Slot, QTimer
from PySide6.QtSerialPort import QSerialPortInfo
from PySide6.QtNetwork import QNetworkInterface
from PySide6.QtGui import QDesktopServices
from multiprocessing import Process, Queue
import numpy as np
import subprocess
import datetime
import shutil
import os

from src.serial.microstrain import Microstrain
from src.serial.witmotion import WitMotion
from src.serial.ublox import Ublox
from src.ui.ui_sensor import Ui_Sensor
from src.utils.helpers import Bridge


RAD_TO_DEG = 180.0 / np.pi


class Sensor(QWidget):
    def __init__(self, mainWindow, parent=None):
        super().__init__(parent)
        self.ui = Ui_Sensor()
        self.ui.setupUi(self)
        self.mainWindow = mainWindow  # reference to the main window

        # Set initial values
        self.ui.gpsSerial.addItem("None")
        self.ui.imuSerial.addItem("None")
        self.ui.ethernetPort.addItem("None")
        self.ui.gpsType.addItem("None")
        self.ui.imuType.addItem("None")

        self.ui.gpsType.addItem("2BPro")
        self.ui.gpsType.addItem("Fusion")
        self.ui.imuType.addItem("Microstrain CV7")
        self.ui.imuType.addItem("WitMotion")

        # Populate available serial ports
        for serial_port in QSerialPortInfo.availablePorts():
            self.ui.gpsSerial.addItem(serial_port.portName())
            self.ui.imuSerial.addItem(serial_port.portName())

        # Populate available ethernet interfaces
        for interface in QNetworkInterface.allInterfaces():
            # flags = interface.flags()
            # if flags & QNetworkInterface.IsUp and flags & QNetworkInterface.IsRunning and not flags & QNetworkInterface.IsLoopBack:
            self.ui.ethernetPort.addItem(interface.humanReadableName())

        self.gps_error_queue = Queue()
        self.imu_error_queue = Queue()

        self.error_timer = QTimer()
        self.error_timer.timeout.connect(self.check_error_queues)
        self.error_timer.start(1000)  # check every 1 second

    @Slot()
    def on_next_clicked(self):
        self.ui.stackedDisplay.setCurrentIndex(1)

    @Slot()
    def on_prev_clicked(self):
        self.ui.stackedDisplay.setCurrentIndex(0)

    @Slot()
    def on_btnLidarStatus_clicked(self):
        QDesktopServices.openUrl(QUrl("http://192.168.1.201"))

    @Slot()
    def on_recordingFolderbtn_clicked(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(
            self.mainWindow.recording_path))

    @Slot()
    def on_btnPandarView_clicked(self):
        process = QProcess(self)
        process.setWorkingDirectory(self.mainWindow.pandarview_path)
        command = f"echo '{self.mainWindow.password}' | sudo -S bash PandarView.sh"
        process.start("bash", ["-c", command])

        output = process.readAllStandardOutput().data().decode()
        error = process.readAllStandardError().data().decode()
        print("Output:", output)
        print("Error:", error)

    @Slot()
    def on_btnPtpd_clicked(self):
        ethernet_port = self.ui.ethernetPort.currentText()
        if not ethernet_port or ethernet_port == "None":
            print("Ethernet port not selected.")
            return

        result = subprocess.run(
            ["pgrep", "ptpd"], capture_output=True, text=True)
        if result.stdout.strip():
            print("ptpd is already running.")
            self.ui.btnPtpd.setEnabled(False)
            return

        command = f"echo '{self.mainWindow.password}' | sudo -S ptpd -M -i {ethernet_port}"
        subprocess.Popen(["bash", "-c", command])
        if not subprocess.run(["pgrep", "ptpd"], capture_output=True, text=True).stdout.strip():
            print("Failed to start ptpd.")
            self.ui.btnPtpd.setEnabled(True)
        else:
            print("ptpd started successfully.")
            self.ui.btnPtpd.setEnabled(False)

    @Slot()
    def on_btnIPV4_clicked(self):
        ethernet_port = self.ui.ethernetPort.currentText()
        if not ethernet_port or ethernet_port == "None":
            print("Ethernet port not selected.")
            return

        if not shutil.which("ifconfig"):
            print("ifconfig not installed.")
            return

        command = f"echo '{self.mainWindow.password}' | sudo -S ifconfig {ethernet_port} 192.168.1.100"
        print(command)
        subprocess.Popen(["bash", "-c", command])

        # TODO: Once set, if it reverts automate the process. (Timer)

    @Slot(dict)
    def displayIMUData(self, data):
        self.ui.systemTimeIMU.setPlainText(data.get("systemtime", ""))
        self.ui.TimeIMU.setPlainText(data.get("imutime", ""))
        self.ui.AccX.setPlainText(data.get("accX", ""))
        self.ui.AccY.setPlainText(data.get("accY", ""))
        self.ui.AccZ.setPlainText(data.get("accZ", ""))
        self.ui.gyroX.setPlainText(data.get("gyroX", ""))
        self.ui.gyroY.setPlainText(data.get("gyroY", ""))
        self.ui.gyroZ.setPlainText(data.get("gyroZ", ""))
        self.ui.roll.setPlainText(data.get("roll", ""))
        self.ui.pitch.setPlainText(data.get("pitch", ""))
        self.ui.yaw.setPlainText(data.get("yaw", ""))
        self.ui.quatX.setPlainText(data.get("qX", ""))
        self.ui.quatY.setPlainText(data.get("qY", ""))
        self.ui.quatZ.setPlainText(data.get("qZ", ""))
        self.ui.quatW.setPlainText(data.get("qW", ""))

    @Slot(dict)
    def displayGPSData(self, data):
        # TODO: Add Fusion IMU
        self.ui.systemTimeGPS.setPlainText(data.get("systemtime", ""))
        self.ui.GPSTime.setPlainText(data.get("gpstime", ""))
        self.ui.latitude.setPlainText(data.get("lat", ""))
        self.ui.longitude.setPlainText(data.get("lon", ""))
        self.ui.altitude.setPlainText(data.get("alt", ""))
        self.ui.heading.setPlainText(data.get("azimuth", ""))
        self.ui.fix.setPlainText(data.get("fix", ""))

        self.ui.diffAge.setPlainText(data.get("diffage", ""))
        self.ui.diffStation.setPlainText(data.get("diffstation", ""))

        self.ui.hAccu.setPlainText(data.get("2D hAcc", ""))
        self.ui.vAccu.setPlainText(data.get("2D vAcc", ""))
        self.ui.acc3D.setPlainText(data.get("3D Acc", ""))
        self.ui.GPSFix.setPlainText(data.get("gpsFix", ""))
        self.ui.numSat.setPlainText(data.get("numSV", ""))
        self.ui.HDOP.setPlainText(data.get("HDOP", ""))
        self.ui.VDOP.setPlainText(data.get("VDOP", ""))
        self.ui.PDOP.setPlainText(data.get("PDOP", ""))
        self.ui.fusionMode.setPlainText(data.get("fusionMode", ""))
        self.ui.imuStatus.setPlainText(data.get("imuStatus", ""))
        self.ui.rollAccu.setPlainText(data.get("rollAcc", ""))
        self.ui.pitchAccu.setPlainText(data.get("pitchAcc", ""))
        self.ui.yawAccu.setPlainText(data.get("yawAcc", ""))

        self.ui.calibGyroX.setPlainText(data.get("gyroX_calib", ""))
        self.ui.calibGyroY.setPlainText(data.get("gyroY_calib", ""))
        self.ui.calibGyroZ.setPlainText(data.get("gyroZ_calib", ""))
        self.ui.calibAccX.setPlainText(data.get("accZ_calib", ""))
        self.ui.calibAccY.setPlainText(data.get("accY_calib", ""))
        self.ui.calibAccZ.setPlainText(data.get("accZ_calib", ""))

    @Slot()
    def on_serialConnectionButton_clicked(self):
        gpsport = self.ui.gpsSerial.currentText()
        gpsbaud = int(self.ui.baudGPS.currentText())
        gpstype = self.ui.gpsType.currentText()

        imuport = self.ui.imuSerial.currentText()
        imubaud = int(self.ui.baudIMU.currentText())
        imutype = self.ui.imuType.currentText()

        save = self.ui.saveButton.isChecked()
        gps = imu = False
        ntrip_details = self.mainWindow.ntrip_details
        ntrip_details["start"] = self.ui.ntripConnection.isChecked()

        currentTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        recording_path = os.path.join(
            self.mainWindow.recording_path, currentTime)
        os.makedirs(recording_path, exist_ok=True)

        if gpsport != "None" and gpstype != "None" and gpsbaud != 0:
            gps = True
            gpsport = f"/dev/{gpsport}"
            self.gps_queue = Queue()
            self.gps_bridge = Bridge(self.gps_queue)
            self.gps_bridge.lastData.connect(self.displayGPSData)

            if gpstype == "Fusion":
                self.gps_process = Process(
                    target=Ublox,
                    kwargs={
                        "gps_port": gpsport,
                        "baud_rate": gpsbaud,
                        "fusion": True,
                        "save_data": save,
                        "save_path": recording_path,
                        "ntrip_details": self.mainWindow.ntrip_details,
                        "gps_queue": self.gps_queue,
                        "gps_error_queue": self.gps_error_queue,
                    }
                )
                self.gps_process.start()
            elif gpstype == "2BPro":
                self.gps_process = Process(
                    target=Ublox,
                    kwargs={
                        "gps_port": gpsport,
                        "baud_rate": gpsbaud,
                        "fusion": False,
                        "save_data": save,
                        "save_path": recording_path,
                        "ntrip_details": self.mainWindow.ntrip_details,
                        "gps_queue": self.gps_queue,
                        "gps_error_queue": self.gps_error_queue,
                    }
                )
                self.gps_process.start()

            else:
                print("Gps Type not found")
                gps = False

        if imuport != "None" and imutype != "None" and imubaud != 0:
            imu = True
            imuport = f"/dev/{imuport}"
            self.imu_queue = Queue()
            self.imu_bridge = Bridge(self.imu_queue)
            self.imu_bridge.lastData.connect(self.displayIMUData)

            if imutype == "WitMotion":
                self.imu_process = Process(
                    target=WitMotion,
                    kwargs={
                        "imu_port": imuport,
                        "baud_rate": imubaud,
                        "save_data": save,
                        "save_path": recording_path,
                        "imu_queue": self.imu_queue,
                        "imu_error_queue": self.imu_error_queue,
                    }
                )
                self.imu_process.start()
            elif imutype == "Microstrain CV7":
                self.imu_process = Process(
                    target=Microstrain,
                    kwargs={
                        "imu_port": imuport,
                        "baud_rate": imubaud,
                        "save_data": save,
                        "save_path": recording_path,
                        "imu_queue": self.imu_queue,
                        "imu_error_queue": self.imu_error_queue,
                    }
                )
                self.imu_process.start()
            else:
                print("IMU Type not found")
                imu = False

        if gps or imu:
            self.ui.serialConnectionButton.setEnabled(False)
            self.ui.serialTerminationButton.setEnabled(True)

    @Slot()
    def on_serialTerminationButton_clicked(self):
        # Terminate GPS process
        if hasattr(self, "gps_process") and self.gps_process.is_alive():
            print("Stopping GPS process...")
            self.gps_process.terminate()
            self.gps_process.join()
            print("GPS process stopped.")

        # Terminate IMU process
        if hasattr(self, "imu_process") and self.imu_process.is_alive():
            print("Stopping IMU process...")
            self.imu_process.terminate()
            self.imu_process.join()
            print("IMU process stopped.")

        # Clean up queues and bridges
        if hasattr(self, "gps_queue"):
            self.gps_queue.close()
            self.gps_queue.join_thread()
        if hasattr(self, "imu_queue"):
            self.imu_queue.close()
            self.imu_queue.join_thread()

        if hasattr(self, "gps_bridge"):
            self.gps_bridge.deleteLater()
        if hasattr(self, "imu_bridge"):
            self.imu_bridge.deleteLater()

        # UI buttons
        self.ui.serialConnectionButton.setEnabled(True)
        self.ui.serialTerminationButton.setEnabled(False)

    def check_error_queues(self):
        while not self.gps_error_queue.empty():
            err = self.gps_error_queue.get()
            print(err)  # or show in UI

        while not self.imu_error_queue.empty():
            err = self.imu_error_queue.get()
            print(err)  # or show in UI
