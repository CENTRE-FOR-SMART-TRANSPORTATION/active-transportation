import os
import time
import serial
import threading
import numpy as np
import datatypes as dt
from queue import Queue
from pyubx2 import UBXReader
from scipy.spatial.transform import Rotation as R
from datetime import datetime, timedelta, timezone, date
from PySide6.QtCore import QObject, Signal

GPS_EPOCH = datetime(1980, 1, 6)
GPS_UTC_OFFSET = 18
DEG_TO_RAD = np.pi / 180


class Ublox(QObject):
    lastData = Signal(dict)

    def __init__(self, gps_port="/dev/ttyACM0", baud_rate=115200, fusion=False, save_data=False, save_path=None):
        super().__init__()
        self._serial = None
        self.running = False
        self.gps_port = gps_port
        self.baud_rate = baud_rate
        self.template = {**dt.time_template, **dt.gps_template}

        if fusion:
            self.template = {**self.template, **dt.imu_template}

        self._current_data = self.template.copy()
        self._last_data = self.template.copy()
        self._status = dt.status_template.copy()
        self._calib_status = dt.calib_status_template.copy()
        self._save_data = save_data
        self._save_path = os.path.join(
            save_path, f"ublox_data_{gps_port[-1:]}.csv") if save_path else None
        self._rawbuffer = Queue()
        self._filebuffer = Queue()  # Use a queue for thread-safe data transfer
        self._save_thread = None

        if self._save_data and self._save_path:
            try:
                if not os.path.exists(save_path):
                    os.mkdir(save_path)
                with open(self._save_path, "w") as f:
                    f.write(",".join(self._current_data.keys()) + "\n")
            except Exception as e:
                print(f"Error opening file for writing: {e}")
                self._save_data = False

    def start(self):
        self._serial = serial.Serial(self.gps_port, self.baud_rate, timeout=1)
        self.ubr = UBXReader(self._serial, protfilter=7)
        self.running = True
        self.schedule_update()
        self.parse_thread()
        if self._save_data:
            self.start_saving_thread()

    def stop(self):  # Ensure any remaining data is saved
        self.running = False
        if self._update_thread:
            self._update_thread.join()
        if self._parse_thread:
            self._parse_thread.join()
        if self._serial and self._serial.is_open:
            self._serial.close()
        if self._save_thread:
            self._save_thread.join()  # Wait for the saving thread to finish

    def schedule_update(self):
        self._update_thread = threading.Thread(target=self.read_raw)
        self._update_thread.start()

    def parse_thread(self):
        self._parse_thread = threading.Thread(target=self.parse_sensor_data)
        self._parse_thread.start()

    def start_saving_thread(self):
        self._save_thread = threading.Thread(target=self.save_data_thread)
        self._save_thread.start()

    def read_raw(self):
        while self.running:
            try:
                if self._serial.in_waiting:
                    _, parsed_data = self.ubr.read()
                    self._rawbuffer.put(parsed_data)
            except Exception as e:
                print(f"GPS Read Error: {e}")

    def parse_sensor_data(self):
        while self.running:
            try:
                parsed_data = self._rawbuffer.get(timeout=1)
                if hasattr(parsed_data, "identity"):
                    msg_type = parsed_data.identity

                    # if msg_type == "NAV-PVT":
                    #     s = parsed_data.iTOW / 1000
                    #     time = GPS_EPOCH + timedelta(seconds=s - GPS_UTC_OFFSET)
                    #     iso_time = (
                    #         f"{parsed_data.year}-{parsed_data.month:02}-{parsed_data.day:02}T"
                    #         f"{time.strftime('%H:%M:%S.%f')}Z"
                    #     )
                    #     epoch_time = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                    #         tzinfo=timezone.utc
                    #     )
                    #     epoch_time = epoch_time.timestamp()

                    #     self._current_data.update({
                    #         "time": iso_time,
                    #         "epochtime": f"{epoch_time:.3f}",
                    #         "lat": parsed_data.lat,
                    #         "lon": parsed_data.lon,
                    #         "alt": parsed_data.hMSL / 1000,
                    #     })
                    #     self._status.update({
                    #         "gpsFix": parsed_data.fixType,
                    #         "gpsAcc (H, V)": (parsed_data.hAcc / 1000, parsed_data.vAcc / 1000),
                    #     })

                    if msg_type == "NAV-ATT":
                        roll = parsed_data.roll * DEG_TO_RAD
                        pitch = parsed_data.pitch * DEG_TO_RAD
                        yaw = parsed_data.heading * DEG_TO_RAD
                        quaternion = R.from_euler(
                            'xyz', [roll, pitch, yaw]).as_quat()

                        self._current_data.update({
                            "roll": roll,
                            "pitch": pitch,
                            "yaw": yaw,
                            "qX": quaternion[0],
                            "qY": quaternion[1],
                            "qZ": quaternion[2],
                            "qW": quaternion[3],
                            "azimuth": yaw,
                        })
                        self._status.update({
                            "rollAcc": parsed_data.accRoll,
                            "pitchAcc": parsed_data.accPitch,
                            "yawAcc": parsed_data.accHeading,
                        })

                    elif msg_type == "ESF-MEAS":
                        for i in range(1, parsed_data.numMeas + 1):
                            data_type = getattr(parsed_data, f"dataType_0{i}")
                            data_field = getattr(
                                parsed_data, f"dataField_0{i}")
                            if data_type == 16:
                                self._current_data["gyroX"] = data_field / \
                                    1000 * DEG_TO_RAD
                            elif data_type == 17:
                                self._current_data["gyroY"] = data_field / \
                                    1000 * DEG_TO_RAD
                            elif data_type == 18:
                                self._current_data["gyroZ"] = data_field / \
                                    1000 * DEG_TO_RAD

                    elif msg_type == "ESF-INS":
                        self._current_data.update({
                            "accX": parsed_data.xAccel,
                            "accY": parsed_data.yAccel,
                            "accZ": parsed_data.zAccel,
                        })

                    elif msg_type == "ESF-STATUS":
                        self._status.update({
                            "imuStatus": "Initialized" if parsed_data.imuInitStatus == 2 else ("Initializing" if parsed_data.imuInitStatus == 1 else "No"),
                            "fusionMode": parsed_data.fusionMode,
                        })
                        sensor_types = {5: "gyroX_calib", 13: "accX_calib",
                                        14: "accY_calib", 16: "accZ_calib", 17: "gyroY_calib", 18: "gyroZ_calib"}
                        for i in range(1, parsed_data.numSens + 1):
                            try:
                                sensor_type = getattr(
                                    parsed_data, f"type_{i:02d}")
                                calib_status_value = getattr(
                                    parsed_data, f"calibStatus_{i:02d}")
                                if sensor_type in sensor_types:
                                    sensor_name = sensor_types[sensor_type]
                                    self._calib_status[sensor_name] = "Calibrated" if calib_status_value in [
                                        2, 3] else ("Calibrating" if calib_status_value == 1 else "Not Calibrated")
                            except AttributeError:
                                print(
                                    f"Warning: Missing sensor data for index {i}")

                    elif msg_type in ["GNGGA", "GPGGA", "GNGNS", "GPGNS"]:
                        time_str = str(parsed_data.time)
                        if time_str.find(".") == -1:
                            time_str += ".000000"
                        date_str = date.today()
                        iso_time = f"{date_str}T{time_str}Z"
                        epoch_time = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                            tzinfo=timezone.utc
                        )
                        epoch_time = epoch_time.timestamp()

                        system_time = datetime.now()
                        system_time_str = system_time.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ")
                        system_epoch_time = datetime.strptime(system_time_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                            tzinfo=timezone.utc
                        )

                        self._current_data.update({
                            "systemtime": system_time_str,
                            "systemepoch": f"{system_epoch_time.timestamp():.3f}",
                            "gpstime": iso_time,
                            "gpsepoch": f"{epoch_time:.3f}",
                            "lat": parsed_data.lat,
                            "lon": parsed_data.lon,
                            "alt": parsed_data.alt,
                        })

                        self._status["nvSat"] = parsed_data.numSV

                    elif msg_type == "GNVTG":
                        self._current_data["azimuth"] = parsed_data.cogt

                if all(self._current_data.get(k) is not None for k in self._current_data.keys()):
                    self._last_data = self._current_data.copy()
                    self._current_data = self.template.copy()
                    self.temp = {**self._last_data, **
                                 self._status, **self._calib_status}

                    self.temp = {k: str(v) if isinstance(v, (int, float)) else v for k, v in self.temp.items()}
                    
                    self.lastData.emit(self.temp)

                    if self._save_data:
                        # Correct method for Queue
                        self._filebuffer.put(self._last_data)
            except Exception as e:
                print(f"Parsing Error: {e}")

    def save_data_thread(self):
        while self.running:
            try:
                # Wait for data to be available and get it
                data = self._filebuffer.get(timeout=1)
                with open(self._save_path, "a") as f:
                    f.write(",".join(map(str, data.values())) + "\n")
            except Exception as e:
                print(f"Error writing to file: {e}")
            except Queue.Empty:
                # No data available, continue waiting
                pass

    def get_last_data(self):
        return self._last_data

    def get_calib_status(self):
        return self._calib_status

    def get_status(self):
        return self._status

    def clear_status(self):
        self._status = dt.status_template.copy()
        self._calib_status = dt.calib_status_template.copy()

    # def save_data(self):
    #     try:
    #         # Make sure to save any remaining data from the buffer
    #         while not self._filebuffer.empty():
    #             data = self._filebuffer.get()
    #             with open(self._save_path, "a") as f:
    #                 f.write(",".join(map(str, data.values())) + "\n")
    #     except Exception as e:
    #         print(f"Error writing to file: {e}")

    def __del__(self):
        self.stop()


if __name__ == "__main__":
    gps = Ublox(gps_port="/dev/ttyACM0", fusion=False,
                save_data=True, save_path="test")
    gps.start()
    while True:
        try:
            print(gps.get_last_data())
        except KeyboardInterrupt:
            break

    # time.sleep(30)
    gps.stop()
