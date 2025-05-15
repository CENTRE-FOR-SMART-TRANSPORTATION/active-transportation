import os
import time
import serial
import threading
import numpy as np
from pyubx2 import UBXReader
from queue import Queue, Empty
import datatypes as dt
from pygnssutils import GNSSNTRIPClient
from datetime import datetime, timezone, date
from scipy.spatial.transform import Rotation as R

GPS_EPOCH = datetime(1980, 1, 6)
GPS_UTC_OFFSET = 18
DEG_TO_RAD = np.pi / 180
FIX_FLAGS = {
    0: "No Fix",
    1: "2D/3D GNSS fix",
    2: "Differential GNSS fix",
    4: "RTK Fixed",
    5: "RTK Float",
    6: "GNSS Dead Reckoning",
}
GNSS_FIX_FLAGS = {
    0: "No Fix",
    1: "Dead Reckoning",
    2: "2D GNSS fix",
    3: "3D GNSS fix",
    4: "GNSS + Dead Reckoning",
    5: "Time only",
}


class Ublox():

    def __init__(self, gps_port="/dev/ttyACM0", baud_rate=115200, fusion=False, save_data=False, save_path=None):
        super().__init__()
        self._serial = None
        self.running = False
        self.gps_port = gps_port
        self.ntrip_run = False
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
        self._ntrip_data = Queue()
        self._raw_data_thread = None
        self._parse_thread = None
        self._save_thread = None
        self._ntrip_client = None
        self._ntrip_settings = {"start": False}

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
        self._ubr = UBXReader(self._serial, protfilter=7)

        self.running = True

        self._raw_data_thread = threading.Thread(target=self.read_raw)
        self._raw_data_thread.start()

        self._parse_thread = threading.Thread(target=self.parse_sensor_data)
        self._parse_thread.start()

        if self._save_data:
            self._save_thread = threading.Thread(target=self.save_data_thread)
            self._save_thread.start()

    def stop(self):  # Ensure any remaining data is saved
        self.running = False

        if self._ntrip_client:
            self._ntrip_client.stop()

        if isinstance(self._raw_data_thread, threading.Thread) and self._raw_data_thread.is_alive():
            self._raw_data_thread.join()

        if isinstance(self._parse_thread, threading.Thread) and self._parse_thread.is_alive():
            self._parse_thread.join()

        if isinstance(self.ntrip_thread, threading.Thread) and self.ntrip_thread.is_alive():
            self.ntrip_thread.join()

        if isinstance(self._save_thread, threading.Thread) and self._save_thread.is_alive():
            self._save_thread.join()

        if self._serial and self._serial.is_open:
            self._serial.close()

        if self._save_data:
            self.save_data()

    def ntrip_connect(self):
        if self._ntrip_client is None:
            self._ntrip_settings['start'] = True
            self._start_ntrip_thread()
        else:
            self._stop_ntrip()

    def set_ntrip_settings(self, settings):
        self._ntrip_settings = settings

    def _start_ntrip_thread(self):
        self._ntrip_client = GNSSNTRIPClient(app=self)
        self._ntrip_client.run(
            server=self._ntrip_settings.server,
            port=self._ntrip_settings.port,
            mountpoint=self._ntrip_settings.mountpoint,
            datatype='RTCM',
            ntripuser=self._ntrip_settings.user,
            ntrippassword=self._ntrip_settings.password,
            ggainterval=1,
            ggamode=0,
            # Possible problem with this. (Also fix in NTRIP Parsing)
            output=self._ntrip_data,
        )

        self.ntrip_thread = threading.Thread(target=self.read_ntrip)
        self.ntrip_thread.start()

    def _stop_ntrip(self):
        self._ntrip['start'] = False

        if isinstance(self.ntrip_thread, GNSSNTRIPClient) and self._ntrip_client._connected:
            self._ntrip_client.stop()
            self._ntrip_client = None

        if isinstance(self.ntrip_thread, threading.Thread) and self.ntrip_thread.is_alive():
            self.ntrip_thread.join()
            self.ntrip_thread = None

    def get_coordinates(self):
        return self._last_data

    def read_raw(self):
        while self.running:
            try:
                if self._serial.in_waiting:
                    _, parsed_data = self._ubr.read()
                    self._rawbuffer.put(parsed_data)
            except Exception as e:
                print(f"GPS Read Error: {e}")

    def parse_sensor_data(self):
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
                            "hdop": parsed_data.HDOP,
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

                if all(self._current_data.get(k) is not None for k in self._current_data.keys()):
                    self._last_data = self._current_data.copy()
                    self._current_data = self.template.copy()
                    if (self._ntrip_client is None and
                                self._ntrip['start'] and
                                not self._last_data['lat'] == '' and
                                not self._last_data['lon'] == '' and
                                self._last_data['fix'] > 0
                            ):
                        print('STARTING NTRIP client')
                        self._start_ntrip_thread()

                    self._last_data = {k: str(v) if isinstance(
                        v, (int, float)) else v for k, v in self._last_data.items()}
                    temp = {**self._last_data, **
                            self._status, **self._calib_status}
                    temp['fix'] = FIX_FLAGS.get(
                        temp['fix'], "Unknown")

                    if self._save_data:
                        self._filebuffer.put(self._last_data)

            except Exception as e:
                print(f"Parsing Error: {e}")

    def save_data_thread(self):
        while self.running:
            try:
                # Wait for data to be available and get it
                data = self._filebuffer.get(timeout=1)
                with open(self._save_path, "a") as f:
                    f.write(",".join(data.values()) + "\n")
            except Exception as e:
                print(f"Error writing to file: {e}")
            except Empty:
                continue

    def read_ntrip(self):
        while self.running:
            try:
                if not self._ntrip_data.empty():
                    raw_data = self._ntrip_data.get()
                    self._serial.write(raw_data[0])
            except Exception as e:
                print(f"NTRIP Read Error: {e}")

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
            # Make sure to save any remaining data from the buffer
            while not self._filebuffer.empty():
                data = self._filebuffer.get()
                with open(self._save_path, "a") as f:
                    f.write(",".join(map(str, data.values())) + "\n")
        except Exception as e:
            print(f"Error writing to file: {e}")

    def __del__(self):
        self.stop()


if __name__ == "__main__":
    gps = Ublox(gps_port="COM4", fusion=False,
                save_data=True, save_path="test")
    gps.start()
    while True:
        try:
            print(gps.get_last_data())
            time.sleep(1)
            # pass
        except KeyboardInterrupt:
            break

    # time.sleep(30)
    gps.stop()
