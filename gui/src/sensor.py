# sensor.py

from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import QProcess, QThread, QUrl, Slot
from PySide6.QtSerialPort import QSerialPortInfo
from PySide6.QtNetwork import QNetworkInterface
from PySide6.QtGui import QDesktopServices
import subprocess
import datetime
import shutil
import os

from src.ui.ui_sensor import Ui_Sensor
from src.serial.microstrain import Microstrain
from src.serial.witmotion import WitMotion
from src.serial.ublox import Ublox


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
        self.ui.fusionMode.setPlainText(data.get("fusionMode", ""))
        self.ui.imuStatus.setPlainText(data.get("imuStatus", ""))
        self.ui.GPSFix.setPlainText(data.get("gpsFix", ""))
        self.ui.numSat.setPlainText(data.get("nvSat", ""))
        self.ui.GPSAccuH.setPlainText(data.get("gpsAcc", [""])[
                                      0])  # Handle list safely
        self.ui.GPSAccuV.setPlainText(data.get("gpsAcc", ["", ""])[
                                      1])  # Handle list safely
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

        currentTime = datetime.datetime.now()
        currentTime = currentTime.strftime("%Y-%m-%d_%H-%M-%S")

        recording_path = os.path.join(
            self.mainWindow.recording_path, currentTime)

        if not os.path.exists(recording_path):
            os.mkdir(recording_path)

        if gpsport != "None" and gpstype != "None" and gpsbaud != 0:
            gps = True
            self.gpsthread = QThread(self)
            gpsport = f"/dev/{gpsport}"
            if gpstype == "Fusion":
                self.gps = Ublox(gpsport, gpsbaud, fusion=True, save_data=save,
                                 save_path=recording_path)
                self.gps.moveToThread(self.gpsthread)

                self.gpsthread.started.connect(self.gps.start)
                self.gpsthread.finished.connect(self.gps.stop)
                self.gps.lastData.connect(self.displayGPSData)

                self.gpsthread.start()
            elif gpstype == "2BPro":
                self.gps = Ublox(gpsport, gpsbaud, fusion=False, save_data=save,
                                 save_path=recording_path)
                self.gps.moveToThread(self.gpsthread)

                self.gpsthread.started.connect(self.gps.start)
                self.gpsthread.finished.connect(self.gps.stop)
                self.gps.lastData.connect(self.displayGPSData)

                self.gpsthread.start()
            else:
                print("Gps Type not found")
                gps = False

        if imuport != "None" and imutype != "None" and imubaud != 0:
            imu = True
            self.imuthread = QThread(self)
            imuport = f"/dev/{imuport}"
            if imutype == "WitMotion":
                self.wit = WitMotion(imuport, imubaud, save,
                                     recording_path)

                self.wit.moveToThread(self.imuthread)

                self.imuthread.started.connect(self.wit.start)
                self.imuthread.finished.connect(self.wit.stop)
                self.wit.lastData.connect(self.displayIMUData)

                self.imuthread.start()
            elif imutype == "Microstrain CV7":
                pass
            else:
                print("IMU Type not found")
                imu = False

        if gps or imu:
            self.ui.serialConnectionButton.setEnabled(False)
            self.ui.serialTerminationButton.setEnabled(True)

    @Slot()
    def on_serialTerminationButton_clicked(self):
        try:
            if hasattr(self, 'imuthread'):
                self.wit.stop()
                self.imuthread.quit()
                self.imuthread.wait()
                del self.wit
                del self.imuthread
            if hasattr(self, 'gpsthread'):
                self.gps.stop()
                self.gpsthread.quit()
                self.gpsthread.wait()
                del self.gps
                del self.gpsthread

            self.ui.serialConnectionButton.setEnabled(True)
            self.ui.serialTerminationButton.setEnabled(False)

        except Exception as e:
            print(f"Error stopping threads: {e}")
            QMessageBox.critical(self, "Error", f"Error stopping threads: {e}")
