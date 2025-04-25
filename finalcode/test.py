import os
import datetime
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
    gps_port1 = '/dev/ttyACM0'      # Fusion
    gps_port2 = '/dev/ttyACM1'      # Pro
    imu_port1 = '/dev/ttyUSB0'      
    imu_port2 = '/dev/ttyUSB1'   

    currentTime = datetime.datetime.now()
    currentTime = currentTime.strftime("%Y-%m-%d_%H-%M-%S")
    
    if not os.path.exists(currentTime):
        os.mkdir(currentTime)

    if gps_port1:
        gps_1 = Ublox(gps_port=gps_port1, baud_rate=115200,
                    fusion=True, save_data=True, save_path=currentTime)
        gps_1.start()
    
    if gps_port2:
        gps_2 = Ublox(gps_port=gps_port2, baud_rate=115200,
                    fusion=False, save_data=True, save_path=currentTime)
        gps_2.start()

    if imu_port2:
        imu_2 = WitMotion(imu_port=imu_port2, baud_rate=115200, save_data=True, save_path=currentTime)
        imu_2.start()
    
    if imu_port1:
        imu_1 = WitMotion(imu_port=imu_port1, baud_rate=115200, save_data=True, save_path=currentTime)
        imu_1.start()


    # Start the GPS and IMU
    global TIME
    TIME = datetime.datetime.now()
    set_time(TIME)    # Start the GPS and IMU

    try:
        while True:
            if gps_port1:
                gps_1_data = gps_1.get_last_data()
                TIME = gps_1_data["time"]
                print("GPS Data:", gps_1_data)
                calib_status = gps_1.get_calib_status()
                status = gps_1.get_status()
                # print({**calib_status, **status})
            
            if gps_port2:
                gps_2_data = gps_2.get_last_data()
                print("GPS Data:", gps_2_data)
                # calib_status = gps_2.get_calib_status()
                # status = gps_2.get_status()
                # print({**calib_status, **status})
            
            if imu_port1:
                print("IMU Data:", imu_1.get_last_data())
                pass
            
            if imu_port2:
                print("IMU Data:", imu_2.get_last_data())
                pass

    except KeyboardInterrupt:
        if gps_port1:
            gps_1.stop()
        if gps_port2:
            gps_2.stop()
        if imu_port1:
            imu_1.stop()
        if imu_port2:
            imu_2.stop()

if __name__ == "__main__":
    main()
