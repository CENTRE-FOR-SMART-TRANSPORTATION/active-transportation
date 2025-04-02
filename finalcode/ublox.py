import os
import serial
import threading
import datetime
import numpy as np
import datatypes as dt
from pyubx2 import UBXReader
from scipy.spatial.transform import Rotation as R
from datetime import datetime, timedelta, timezone

GPS_EPOCH = datetime(1980, 1, 6)
GPS_UTC_OFFSET = 18
DEG_TO_RAD = np.pi / 180


class Ublox:
    def __init__(self, gps_port="/dev/ttyACM0", baud_rate=115200, fusion=False, save_data=False, save_path=None):
        self.serial = None
        self.running = False
        self.timer = None
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
            save_path, "ublox_data.csv") if save_path else None
        self._filebuffer = []

        if self._save_data and self._save_path:
            try:
                with open(self._save_path, "w") as f:
                    f.write(",".join(self._current_data.keys()) + "\n")
            except Exception as e:
                print(f"Error opening file for writing: {e}")
                self._save_data = False

    def start(self):
        self.serial = serial.Serial(self.gps_port, self.baud_rate, timeout=1)
        self.ubr = UBXReader(self.serial, protfilter=7)
        self.running = True
        self.schedule_update()

    def stop(self):
        if self._save_data:
            self.save_data()
        self.running = False
        if self.timer:
            self.timer.cancel()
        if self.serial and self.serial.is_open:
            self.serial.close()

    def schedule_update(self):
        if self.running:
            self.timer = threading.Timer(-1, self.update)
            self.timer.start()

    def parse_sensor_data(self, parsed_data):
        if hasattr(parsed_data, "identity"):
            msg_type = parsed_data.identity

            if msg_type == "NAV-PVT":
                s = parsed_data.iTOW / 1000
                time = GPS_EPOCH + timedelta(seconds=s - GPS_UTC_OFFSET)
                iso_time = (
                    f"{parsed_data.year}-{parsed_data.month:02}-{parsed_data.day:02}T"
                    f"{time.strftime('%H:%M:%S.%f')}Z"
                )
                epoch_time = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                    tzinfo=timezone.utc
                )
                epoch_time = epoch_time.timestamp()

                self._current_data.update({
                    "time": iso_time,
                    "epochtime": f"{epoch_time:.3f}",
                    "lat": parsed_data.lat,
                    "lon": parsed_data.lon,
                    "alt": parsed_data.hMSL / 1000,
                })
                self._status.update({
                    "gpsFix": parsed_data.fixType,
                    "gpsAcc (H, V)": (parsed_data.hAcc / 1000, parsed_data.vAcc / 1000),
                })

            elif msg_type == "NAV-ATT":
                roll = parsed_data.roll * DEG_TO_RAD
                pitch = parsed_data.pitch * DEG_TO_RAD
                yaw = parsed_data.heading * DEG_TO_RAD
                quaternion = R.from_euler('xyz', [roll, pitch, yaw]).as_quat()

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
                    data_field = getattr(parsed_data, f"dataField_0{i}")
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
                sensor_types = {5: "gyroX", 13: "accX",
                                14: "accY", 16: "accZ", 17: "gyroY", 18: "gyroZ"}
                for i in range(1, parsed_data.numSens + 1):
                    try:
                        sensor_type = getattr(parsed_data, f"type_{i:02d}")
                        calib_status_value = getattr(
                            parsed_data, f"calibStatus_{i:02d}")
                        if sensor_type in sensor_types:
                            sensor_name = sensor_types[sensor_type]
                            self._calib_status[sensor_name] = "Calibrated" if calib_status_value in [
                                2, 3] else ("Calibrating" if calib_status_value == 1 else "Not Calibrated")
                    except AttributeError:
                        print(f"Warning: Missing sensor data for index {i}")

            elif msg_type in ["GNGGA", "GPGGA", "GNGNS", "GPGNS"]:
                self._current_data.update({
                    "lat": parsed_data.lat,
                    "lon": parsed_data.lon,
                    "alt": parsed_data.alt,
                })
                self._status["nvSat"] = parsed_data.numSV

            elif msg_type == "GNVTG":
                self._current_data["azimuth"] = parsed_data.cogt

    def update(self):
        try:
            if self.serial.in_waiting:
                _, parsed_data = self.ubr.read()
                self.parse_sensor_data(parsed_data)
                if all(self._current_data.get(k) is not None for k in self._current_data.keys()):
                    self._last_data = self._current_data.copy()
                    self._current_data = self.template.copy()
                    if self._save_data:
                        self._filebuffer.append(self._last_data)
                        if len(self._filebuffer) > 100:
                            self.save_data()
        except Exception as e:
            print(f"GPS Read Error: {e}")
        finally:
            self.schedule_update()

    def backup_data(self):
        backup_msg = b"\xb5\x62\x09\x14\x04\x00\x00\x00\x00\x00"
        clear_msg = b"\xb5\x62\x09\x14\x04\x00\x01\x00\x00\x00"

        if (
            self._status["gpsFix"] > 2
            and self._status["fusionMode"] == 1
            and "Not Calibrated" not in self._calib_status.values()
        ):
            # Send backup signal
            self.serial.write(clear_msg)
            for raw_data, parsed_data in self.ubr:
                if parsed_data.identity == "UPD-ACK-ACK":
                    print("Clear success!")
                    check = 1
                elif parsed_data.identity == "UBX-ACK-NAK":
                    print("Clear failed!")
                    check = 0
                    break
            if check:
                self.ubr.write(backup_msg)
                for raw_data, parsed_data in self.ubr:
                    if parsed_data.identity == "UPD-SOS-ACK":
                        if parsed_data.response == 1:
                            print("Backup success!")
                        else:
                            print("Backup failed!")

    def get_last_data(self):
        return self._last_data

    def get_calib_status(self):
        return self._calib_status

    def get_status(self):
        return self._status

    def clear_status(self):
        self._status = dt.status_template.copy()
        self._calib_status = dt.calib_status_template.copy()

    def save_data(self):
        try:
            with open(self._save_path, "a") as f:
                for data in self._filebuffer:
                    f.write(",".join(map(str, data.values())) + "\n")
            self._filebuffer.clear()
        except Exception as e:
            print(f"Error writing to file: {e}")

    def __del__(self):
        if self.serial and self.serial.is_open:
            self.serial.close()


if __name__ == "__main__":
    gps = Ublox(fusion=True, save_data=True, save_path="test")
    # gps = Ublox(fusion=True)
    gps.start()
    try:
        while True:
            print(gps.get_status())
    except KeyboardInterrupt:
        gps.stop()
        print("GPS stopped.")
