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
from ublox_thread import Ublox
from witmotion import WitMotion
import argparse

TIME = None


def set_time(time):
    print("Time set to")
    os.system('sudo date --set="%s"' % time)
    threading.Timer(2, set_time).start()


def main():
     # Create the parser
    parser = argparse.ArgumentParser(description="Process GPS and Witmotion ports.")

    # Add optional arguments for GPS port and Witmotion port
    parser.add_argument('--gps-port', type=str, help='Specify the GPS port (e.g., /dev/ttyUSB0)')
    parser.add_argument('--witmotion-port', type=str, help='Specify the Witmotion port (e.g., /dev/ttyUSB1)')

    # Parse the arguments
    args = parser.parse_args()

    # Access the arguments
    gps_port = args.gps_port
    witmotion_port = args.witmotion_port

    currentTime = datetime.datetime.now()
    currentTime = currentTime.strftime("%Y-%m-%d_%H-%M-%S")
    
    if not os.path.exists(currentTime):
        os.mkdir(currentTime)

    # Initialize the Ublox GPS
    if gps_port:
        gps = Ublox(gps_port=gps_port, baud_rate=115200,
                    fusion=True, save_data=True, save_path=currentTime)
        gps.start()


    # Initialize the WitMotion IMU
    if witmotion_port:
        imu = WitMotion(imu_port=witmotion_port, baud_rate=115200, save_data=True, save_path=currentTime)
        imu.start()

    # Start the GPS and IMU
    global TIME
    TIME = datetime.datetime.now()
    set_time(TIME)    # Start the GPS and IMU

    try:
        while True:
            if gps_port:
                gps_data = gps.get_last_data()
                TIME = gps_data["time"]
                # print("GPS Data:", gps_data)
                calib_status = gps.get_calib_status()
                status = gps.get_status()
                print({**calib_status, **status})
            # if witmotion_port:
                # print("IMU Data:", imu.get_last_data())
    except KeyboardInterrupt:
        if gps_port:
            gps.stop()
        if witmotion_port:
            imu.stop()


if __name__ == "__main__":
    main()
