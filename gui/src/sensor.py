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
import math
import sys
import os

from src.serial.microstrain import Microstrain
from src.serial.witmotion import WitMotion
from src.serial.ublox import Ublox
from src.ui.ui_sensor import Ui_Sensor
from src.utils.helpers import Bridge, PrintStream
from src.utils.bluetooth import Bluetooth
from PySide6.QtGui import QStandardItem, QStandardItemModel


RAD_TO_DEG = 180.0 / np.pi


class Sensor(QWidget):
    def __init__(self, mainWindow, parent=None):
        super().__init__(parent)
        self.ui = Ui_Sensor()
        self.ui.setupUi(self)
        self.mainWindow = mainWindow  # reference to the main window
        self.bluetooth = Bluetooth(self)
        #self.bluetooth.dataReceived.connect(self.handle_received_data)
        # self.mainWindow.displayBluetoothData)
        self.bluetooth.connectionStatus.connect(
            self.bleConnectionStatus)
        self.bluetooth.scan()
        #self.raw_queue() = Queue

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
            self.ui.gpsSerial.addItem(
                f"{serial_port.portName()} - {serial_port.manufacturer()}")
            self.ui.imuSerial.addItem(
                f"{serial_port.portName()} - {serial_port.manufacturer()}")

        # Populate available ethernet interfaces
        for interface in QNetworkInterface.allInterfaces():
            # flags = interface.flags()
            # if flags & QNetworkInterface.IsUp and flags & QNetworkInterface.IsRunning and not flags & QNetworkInterface.IsLoopBack:
            self.ui.ethernetPort.addItem(interface.humanReadableName())

        self.gps_error_queue = Queue()
        self.imu_error_queue = Queue()
        self.imu_queue = Queue()

        self.error_timer = QTimer()
        self.error_timer.timeout.connect(self.check_error_queues)
        self.error_timer.start(1000)  # check every 1 second

        self.printer = PrintStream(self.ui.outputScreen)

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
        self.printer.print(f"Output: {output}", "blue")
        self.printer.print(f"Error: {error}", "red")

    @Slot()
    def on_btnPtpd_clicked(self):
        ethernet_port = self.ui.ethernetPort.currentText()
        if not ethernet_port or ethernet_port == "None":
            self.printer.print(
                "Please select an ethernet port to start ptpd.", "red")
            return

        result = subprocess.run(
            ["pgrep", "ptpd"], capture_output=True, text=True)
        if result.stdout.strip():
            self.printer.print(
                "ptpd is already running.", "red")
            self.ui.btnPtpd.setEnabled(False)
            return

        command = f"echo '{self.mainWindow.password}' | sudo -S ptpd -M -i {ethernet_port}"
        subprocess.Popen(["bash", "-c", command])
        if not subprocess.run(["pgrep", "ptpd"], capture_output=True, text=True).stdout.strip():
            self.printer.print(
                "Failed to start ptpd. Please check your configuration.", "red")
            self.ui.btnPtpd.setEnabled(True)
        else:
            self.printer.print(
                "ptpd started successfully.", "green")
            self.ui.btnPtpd.setEnabled(False)

    @Slot()
    def on_btnIPV4_clicked(self):
        ethernet_port = self.ui.ethernetPort.currentText()
        if not ethernet_port or ethernet_port == "None":
            self.printer.print(
                "Please select an ethernet port to set IP address.", "red")
            return

        if not shutil.which("ifconfig"):
            self.printer.print(
                "ifconfig not installed. Please install net-tools.", "red")
            QMessageBox.critical(
                self, "Error", "ifconfig not installed. Please install net-tools.")
            return

        command = f"echo '{self.mainWindow.password}' | sudo -S ifconfig {ethernet_port} 192.168.1.100"
        self.printer.print(
            f"Setting IP address for {ethernet_port} to 192.168.1.100", "blue")
        subprocess.Popen(["bash", "-c", command])

        # TODO: Once set, if it reverts automate the process. (Timer)

    def format_float(value, precision=6):
        try:
            return f"{float(value):.{precision}f}"
        except (ValueError, TypeError):
            return ""

    @Slot(dict)
    def displayIMUData(self, data):

        def format_float(value, precision=6, radians_to_degrees=False):
            try:
                val = float(value)
                if radians_to_degrees:
                    val = math.degrees(val)
                return f"{val:.{precision}f}"
            except (ValueError, TypeError):
                return ""

        self.ui.systemTimeIMU.setPlainText(data.get("systemtime", ""))
        self.ui.TimeIMU.setPlainText(data.get("imutime", ""))
        self.ui.AccX.setPlainText(format_float(data.get("accX")))
        self.ui.AccY.setPlainText(format_float(data.get("accY")))
        self.ui.AccZ.setPlainText(format_float(data.get("accZ")))
        self.ui.gyroX.setPlainText(format_float(data.get("gyroX")))
        self.ui.gyroY.setPlainText(format_float(data.get("gyroY")))
        self.ui.gyroZ.setPlainText(format_float(data.get("gyroZ")))
        self.ui.roll.setPlainText(format_float(
            data.get("roll"), radians_to_degrees=True))
        self.ui.pitch.setPlainText(format_float(
            data.get("pitch"), radians_to_degrees=True))
        self.ui.yaw.setPlainText(format_float(
            data.get("yaw"), radians_to_degrees=True))
        self.ui.quatX.setPlainText(format_float(data.get("qX")))
        self.ui.quatY.setPlainText(format_float(data.get("qY")))
        self.ui.quatZ.setPlainText(format_float(data.get("qZ")))
        self.ui.quatW.setPlainText(format_float(data.get("qW")))

    @Slot(dict)
    def displayGPSData(self, data):
        # TODO: Add Fusion IMU

        def format_float(value, precision=6, radians_to_degrees=False):
            try:
                val = float(value)
                if radians_to_degrees:
                    val = math.degrees(val)
                return f"{val:.{precision}f}"
            except (ValueError, TypeError):
                return ""

        self.ui.systemTimeGPS.setPlainText(data.get("systemtime", ""))
        self.ui.GPSTime.setPlainText(data.get("gpstime", ""))
        self.ui.latitude.setPlainText(format_float(data.get("lat")))
        self.ui.longitude.setPlainText(format_float(data.get("lon")))
        self.ui.altitude.setPlainText(format_float(data.get("alt")))
        self.ui.heading.setPlainText(format_float(data.get("azimuth")))
        self.ui.fix.setPlainText(data.get("fix", ""))

        self.ui.diffAge.setPlainText(data.get("diffage", ""))
        self.ui.diffStation.setPlainText(data.get("diffstation", ""))

        self.ui.hAccu.setPlainText(format_float(data.get("2D hAcc")))
        self.ui.vAccu.setPlainText(format_float(data.get("2D vAcc")))
        self.ui.acc3D.setPlainText(format_float(data.get("3D Acc")))
        self.ui.GPSFix.setPlainText(data.get("gpsFix", ""))
        self.ui.numSat.setPlainText(data.get("numSV", ""))
        self.ui.HDOP.setPlainText(format_float(data.get("HDOP")))
        self.ui.VDOP.setPlainText(format_float(data.get("VDOP")))
        self.ui.PDOP.setPlainText(format_float(data.get("PDOP")))
        self.ui.fusionMode.setPlainText(data.get("fusionMode", ""))
        self.ui.imuStatus.setPlainText(data.get("imuStatus", ""))
        self.ui.rollAccu.setPlainText(format_float(data.get("rollAcc")))
        self.ui.pitchAccu.setPlainText(format_float(data.get("pitchAcc")))
        self.ui.yawAccu.setPlainText(format_float(data.get("yawAcc")))

        self.ui.calibGyroX.setPlainText(data.get("gyroX_calib", ""))
        self.ui.calibGyroY.setPlainText(data.get("gyroY_calib", ""))
        self.ui.calibGyroZ.setPlainText(data.get("gyroZ_calib", ""))
        self.ui.calibAccX.setPlainText(data.get("accZ_calib", ""))
        self.ui.calibAccY.setPlainText(data.get("accY_calib", ""))
        self.ui.calibAccZ.setPlainText(data.get("accZ_calib", ""))

    @Slot()
    def on_serialConnectionButton_clicked(self):
        gpsport = self.ui.gpsSerial.currentText().split('-')[0].strip()
        gpsbaud = int(self.ui.baudGPS.currentText())
        gpstype = self.ui.gpsType.currentText()

        imuport = self.ui.imuSerial.currentText().split('-')[0].strip()
        imubaud = int(self.ui.baudIMU.currentText())
        imutype = self.ui.imuType.currentText()

        save = self.ui.saveButton.isChecked()
        gps = imu = False
        ntrip_details = self.mainWindow.ntrip_details
        ntrip_details["start"] = self.ui.ntripConnection.isChecked()

        currentTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        recording_path = os.path.join(
            self.mainWindow.recording_path, currentTime)
        # os.makedirs(recording_path, exist_ok=True)

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
                        "display_timer": 0.1,
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
                        "display_timer": 0.1,

                    }
                )
                self.gps_process.start()

            else:
                self.printer.print(
                    "GPS Type not found", "red")
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
                        "display_timer": 0.1,

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
                        "display_timer": 0.1,

                    }
                )
                self.imu_process.start()
            else:
                self.printer.print(
                    "IMU Type not found", "red")
                imu = False

        if gps or imu:
            self.ui.serialConnectionButton.setEnabled(False)
            self.ui.serialTerminationButton.setEnabled(True)

    @Slot()
    def on_serialTerminationButton_clicked(self):
        # Terminate GPS process
        if hasattr(self, "gps_process") and self.gps_process.is_alive():
            self.printer.print(
                "Stopping GPS process...", "blue")
            self.gps_process.terminate()
            self.gps_process.join()
            self.printer.print(
                "GPS process stopped.", "green")

        # Terminate IMU process
        if hasattr(self, "imu_process") and self.imu_process.is_alive():
            self.printer.print(
                "Stopping IMU process...", "blue")
            print("Stopping IMU process...")
            self.imu_process.terminate()
            self.imu_process.join()
            self.printer.print(
                "IMU process stopped.", "green")

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
            if "Serial port error" in err:
                self.printer.print(err, "red")
            else:
                self.printer.print(err, "orange")

        while not self.imu_error_queue.empty():
            err = self.imu_error_queue.get()
            if "Serial port error" in err:
                self.printer.print(err, "red")
            else:
                self.printer.print(err, "orange")

    @Slot()
    def on_refreshBtn_clicked(self):
        self.bluetooth.scan()
        self.printer.print("Scanning for Bluetooth devices...", "blue")

    @Slot(str)
    def bleConnectionStatus(self, status):
        self.printer.print(status, "blue")
        if status == "Scan Finished":
            self.ui.bleDevice.clear()
            for address, device in self.bluetooth.devices.items():
                #print(address,device)
                self.ui.bleDevice.addItem(
                    f"{device.name()} - {address}")
        elif "not found" in status:
            self.printer.print(status, "red")
        elif "Connected" in status:
            self.printer.print("Bluetooth connection established.", "green")
            self.printer.print(
                f"{self.bluetooth.current_service_info.serviceName()} service found.", "green")
            currentTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            recording_path = os.path.join(
                self.mainWindow.recording_path, currentTime)
            self.imu_queue = Queue()
            self.imu_bridge = Bridge(self.imu_queue)
            self.imu_bridge.lastData.connect(self.displayIMUData)

            self.imu_process = Process(
                target=WitMotion,
                kwargs={
                    "socket": self.bluetooth.raw_queue,
                    "save_data": self.bluetooth.save,
                    "save_path": recording_path,
                    "imu_queue": self.imu_queue,
                    "imu_error_queue": self.imu_error_queue,
                    "display_timer": 0.1,

                }
            )
            self.imu_process.start()

    @Slot()
    def on_BLEConnectionButton_clicked(self):
        selected_device = self.ui.bleDevice.currentText()
        save = self.ui.saveButton_2.isChecked()

        if not selected_device:
            self.printer.print("Please select a Bluetooth device.", "red")
            return

        address = selected_device.split('-')[2].strip()
        print(address)
        self.bluetooth.connect(address)
        self.bluetooth.save = save
        self.ui.BLETerminationButton.setEnabled(True)
        self.ui.BLEConnectionButton.setEnabled(False)
        self.ui.serialConnectionButton.setEnabled(False)
        self.ui.serialTerminationButton.setEnabled(False)


    @Slot()
    def on_BLETerminationButton_clicked(self):
        if hasattr(self.bluetooth, "socket") and self.bluetooth.socket.isOpen():
            print('Disconnecting Bluetooth')
            self.bluetooth.disconnect()
            if hasattr(self, "imu_process") and self.imu_process.is_alive():
                self.printer.print(
                    "Stopping IMU process...", "blue")
                print("Stopping IMU process...")
                self.imu_process.terminate()
                self.imu_process.join()
                self.printer.print(
                    "IMU process stopped.", "green")

            if hasattr(self, "imu_queue"):
                self.imu_queue.close()
                self.imu_queue.join_thread()

            if hasattr(self, "imu_bridge"):
                self.imu_bridge.deleteLater()

            self.printer.print("Bluetooth connection closed.", "green")
        else:
            self.printer.print("No Bluetooth connection to close.", "red")

        self.ui.BLETerminationButton.setEnabled(False)
        self.ui.BLEConnectionButton.setEnabled(True)
        self.ui.serialConnectionButton.setEnabled(True)
        self.ui.serialTerminationButton.setEnabled(True)
    # @Slot(str)
    # def handle_received_data(self, data: str):
    #     # Push raw string to the queue
    #     if self.raw_queue:
    #         self.raw_queue.put(data)


