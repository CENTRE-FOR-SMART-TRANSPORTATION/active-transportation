"""
    Note: Modify sudo visudo to not ask for password
    sudo visudo
    youruser (name of the user) ALL=(ALL) NOPASSWD: /bin/date

    To sync with ntp server:
    sudo sntp -Ss -M 128 0.de.pool.ntp.org
"""

import os
import datetime
import platform
import threading
from ublox import Ublox
from witmotion import WitMotion

# Check if the system is Linux
if platform.system() == "Linux":
    device_path = (
        "/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00"
    )
    # device_path = "/dev/ttyACM0"get_last_data
elif platform.system() == "Windows":
    device_path = "COM10"

TIME = datetime.datetime.now()


def set_time(time):
    print("Time set to")
    os.system('sudo date --set="%s"' % time)
    threading.Timer(2, set_time).start()


def main():
    # Initialize the Ublox GPS
    gps = Ublox(gps_port="/dev/ttyACM0", baud_rate=115200,
                fusion=True, save_data=True)

    # Initialize the WitMotion IMU
    imu = WitMotion(port="/dev/ttyUSB0", baud_rate=115200)

    # Start the GPS and IMU
    gps.start()
    imu.start()
    set_time(TIME)

    try:
        while True:
            gps_data = gps.get_last_data()
            TIME = gps_data["time"]
            print("GPS Data:", gps_data)
            print("IMU Data:", imu.get_last_data())
    except KeyboardInterrupt:
        gps.stop()
        imu.stop()


if __name__ == "__main__":
    main()
