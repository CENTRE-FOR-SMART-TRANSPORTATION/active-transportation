import os
import time
import serial
import threading
import numpy as np
import src.serial.datatypes as dt

from pyubx2 import UBXReader
from queue import Queue, Empty
from pygnssutils import GNSSNTRIPClient
from PySide6.QtCore import QObject, QThread
from datetime import datetime, timezone, date
from scipy.spatial.transform import Rotation as R

GPS_EPOCH = datetime(1980, 1, 6)
GPS_UTC_OFFSET = 18
DEG_TO_RAD = np.pi / 180
FIX_FLAGS = {
    "0": "No Fix",
    "1": "2D/3D GNSS fix",
    "2": "Differential GNSS fix",
    "4": "RTK Fixed",
    "5": "RTK Float",
    "6": "GNSS Dead Reckoning",
}
GNSS_FIX_FLAGS = {
    0: "No Fix",
    1: "Dead Reckoning",
    2: "2D GNSS fix",
    3: "3D GNSS fix",
    4: "GNSS + Dead Reckoning",
    5: "Time only",
}


class Ublox(QObject):
    def __init__(self, **kwargs):
        super().__init__()

        self._serial = None
        self.running = False
        self.gps_port = kwargs.get("gps_port", "/dev/ttyACM0")
        self.baud_rate = kwargs.get("baud_rate", 9600)
        self.fusion = kwargs.get("fusion", False)
        self.save_data = kwargs.get("save_data", False)
        self.save_path = kwargs.get("save_path", None)
        self.ntrip_details = kwargs.get("ntrip_details", {"start": False})
        self.gps_queue = kwargs.get("gps_queue", None)
        self.gps_error_queue = kwargs.get("gps_error_queue", None)
        self.display_timer = kwargs.get("display_timer", 1)

        self.template = {**dt.time_template, **dt.gps_template}
        if self.fusion:
            self.template = {**self.template, **dt.imu_template}

        self._current_data = self.template.copy()
        self._last_data = self.template.copy()
        self._status = dt.status_template.copy()
        self._calib_status = dt.calib_status_template.copy()

        if self.save_data:
            base_dir = self.save_path or "."
            base_filename = f"ublox_data_fusion" if self.fusion else "ublox_data_pro"
            count = 1

            while True:
                filename = f"{base_filename}_{count}.csv"
                full_path = os.path.join(base_dir, filename)
                if not os.path.exists(full_path):
                    break
                count += 1

            self.save_path = full_path

        self._rawbuffer = Queue()
        self._filebuffer = Queue()  # Use a queue for thread-safe data transfer
        self._ntripbuffer = Queue()
        self._raw_data_thread = None
        self._parse_thread = None
        self._save_thread = None
        self._ntrip_thread = None
        self._ntrip_client = None

        if self.save_data and self.save_path:
            try:
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                with open(self.save_path, "w") as f:
                    f.write(",".join({**self._current_data, **self._status, **self._calib_status}.keys()) + "\n")
            except Exception as e:
                print(f"Error opening file for writing: {e}")
                self.save_data = False

        self.start()

    def start(self):
        try:
            self._serial = serial.Serial(
                self.gps_port, self.baud_rate, timeout=1)
            self._ubr = UBXReader(self._serial, protfilter=7)

            self.running = True

            self._raw_data_thread = threading.Thread(target=self._read_raw)
            self._raw_data_thread.start()

            self._parse_thread = threading.Thread(
                target=self._parse_sensor_data)
            self._parse_thread.start()

            if self.save_data:
                self._save_thread = threading.Thread(
                    target=self._save_data_thread)
                self._save_thread.start()

            if self.gps_queue is not None:
                while True:
                    temp = {**self._last_data, **
                            self._status, **self._calib_status}
                    temp = {k: str(v) if isinstance(
                        v, (int, float)) else v for k, v in temp.items()}
                    temp['fix'] = FIX_FLAGS.get(
                        temp['fix'], "Unknown")

                    self.gps_queue.put(temp)
                    time.sleep(self.display_timer)

        except Exception as e:
            print(f"UBlox port error: {e}")
            if self.gps_error_queue:
                self.gps_error_queue.put(f"Serial port error: {e}")

    def _start_ntrip_thread(self):
        self._ntrip_client = GNSSNTRIPClient(app=self)
        self._ntrip_client.run(
            server=self.ntrip_details.get('server'),
            port=self.ntrip_details.get('port'),
            mountpoint=self.ntrip_details.get('mountpoint'),
            datatype=self.ntrip_details.get('datatype'),
            ntripuser=self.ntrip_details.get('ntripuser'),
            ntrippassword=self.ntrip_details.get('ntrippassword'),
            version=self.ntrip_details.get('version'),
            ggainterval=self.ntrip_details.get('ggainterval'),
            ggamode=0,
            output=self._ntripbuffer,
        )

        self.ntrip_thread = threading.Thread(target=self._read_ntrip)
        self.ntrip_thread.start()

    def stop(self):  # Ensure any remaining data is saved
        self.running = False

        if self.ntrip_details['start']:
            self._stop_ntrip()

        if isinstance(self._raw_data_thread, threading.Thread) and self._raw_data_thread.is_alive():
            self._raw_data_thread.join()

        if isinstance(self._parse_thread, threading.Thread) and self._parse_thread.is_alive():
            self._parse_thread.join()

        if isinstance(self._save_thread, threading.Thread) and self._save_thread.is_alive():
            self._save_thread.join()

        if self._serial and self._serial.is_open:
            self._serial.close()

    def _stop_ntrip(self):
        self.ntrip_details['start'] = False

        if isinstance(self._ntrip_client, GNSSNTRIPClient) and self._ntrip_client._connected:
            self._ntrip_client.stop()
            self._ntrip_client = None

        if isinstance(self._ntrip_thread, threading.Thread) and self._ntrip_thread.is_alive():
            self._ntrip_thread.join()
            self._ntrip_thread = None

    def _read_raw(self):
        while self.running:
            try:
                if self._serial.in_waiting:
                    _, parsed_data = self._ubr.read()
                    self._rawbuffer.put(parsed_data)
            except Exception as e:
                print(f"GPS Read Error: {e}")
                if self.gps_error_queue:
                    self.gps_error_queue.put(f"GPS Read Error: {e}")

    def _read_ntrip(self):
        while self.running:
            try:
                # Block for a short time waiting for data (non-busy loop)
                raw_data = self._ntripbuffer.get(
                    timeout=1)  # Blocking read, 1s timeout
                self._serial.write(raw_data[0])
            except Empty:
                continue  # No data this second, just keep looping
            except Exception as e:
                print(f"NTRIP Read Error: {e}")
                if self.gps_error_queue:
                    self.gps_error_queue.put(f"NTRIP Read Error: {e}")

    def _parse_sensor_data(self):
        while self.running:
            try:
                parsed_data = self._rawbuffer.get(timeout=1)
                if hasattr(parsed_data, "identity"):
                    msg_type = parsed_data.identity

                    if msg_type == "NAV-PVT":
                        self._status.update({
                            "gpsFix": GNSS_FIX_FLAGS[parsed_data.fixType],
                            "HDOP": parsed_data.hAcc / 1000,    # m
                            "VDOP": parsed_data.vAcc / 1000,    # m
                            "PDOP": parsed_data.pDOP / 1000,    # no unit
                            "numSV": parsed_data.numSV,
                        })

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

                    elif msg_type in ["GNGGA", "GPGGA"]:
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
                            "sep": parsed_data.sep,
                            "fix": parsed_data.quality,
                            "sip": parsed_data.numSV,
                        })
                        
                        self._status.update({
                            "HDOP": parsed_data.HDOP,
                            "diffage": parsed_data.diffAge,
                            "diffstation": parsed_data.diffStation
                        })

                    elif msg_type == "GNVTG":
                        self._current_data["azimuth"] = parsed_data.cogt

                    elif msg_type == "RXM-RTCM":
                        self._status['rtcm_crc'] = parsed_data.crcFailed
                        self._status['rtcm_msg'] = parsed_data.msgUsed

                    elif msg_type in ["NAV-HPPOSECEF"]:
                        self._current_data.update({
                            "3D Acc": parsed_data.pAcc / 1000,  # m
                        })

                    elif msg_type in ["NAV-HPPOSLLH"]:
                        self._current_data.update({
                            "2D hAcc": parsed_data.hAcc / 1000,  # m
                            "2D vAcc": parsed_data.vAcc / 1000,  # m
                        })

                required_keys = ["systemtime", "gpstime", "lat", "lon", "alt", "fix"]
                if all(self._current_data.get(k) is not None for k in required_keys):
                    self._last_data = {**self._current_data.copy(), **self._status.copy(), **self._calib_status.copy()}
                    self._current_data = self.template.copy()
                    if (self._ntrip_client is None and
                            self.ntrip_details['start'] and
                            not self._last_data['lat'] == '' and
                            not self._last_data['lon'] == '' and
                            self._last_data['fix'] > 0
                        ):
                        print('STARTING NTRIP client')
                        self._start_ntrip_thread()

                    self._last_data = {k: str(v) if isinstance(
                        v, (int, float)) else v for k, v in self._last_data.items()}

                    if self.save_data:
                        self._filebuffer.put(self._last_data)

            except Exception as e:
                print(f"Parsing Error: {e}")
                if self.gps_error_queue:
                    self.gps_error_queue.put(f"Parsing Error: {e}")

    def _save_data_thread(self):
        with open(self.save_path, "a", buffering=1) as f:
            data_batch = []  # List to collect data packets
            while self.running:
                try:
                    data = self._filebuffer.get(timeout=1)
                    # Collect data in the batch
                    data_batch.append(",".join(data.values()))

                    # Check if we have collected 100 data packets
                    if len(data_batch) >= 5:
                        # Write the batch to the file
                        f.write("\n".join(data_batch) + "\n")
                        data_batch.clear()  # Clear the batch after writing
                except Empty:
                    continue
                except Exception as e:
                    print(f"Error writing to file: {e}")
                    if self.gps_error_queue:
                        self.gps_error_queue.put(f"Error writing to file: {e}")

            # Write any remaining data in the batch when the thread stops
            if data_batch:
                f.write("\n".join(data_batch) + "\n")

    def get_coordinates(self):
        return self._last_data

    def get_calib_status(self):
        return self._calib_status

    def get_status(self):
        return self._status

    def clear_status(self):
        self._status = dt.status_template.copy()
        self._calib_status = dt.calib_status_template.copy()

    def __del__(self):
        self.stop()


if __name__ == "__main__":
    gps_thread = QThread()
    gps = Ublox(gps_port="/dev/ttyACM1", fusion=False,
                save_data=True, save_path="test")
    gps.moveToThread(gps_thread)
    gps_thread.started.connect(gps.start)
    gps_thread.start()
    try:
        while True:
            print(gps.get_coordinates())
            time.sleep(1)
    except KeyboardInterrupt:
        gps.stop()
    except Exception as e:
        print(f"Unexpected error: {e}")
        gps.stop()
