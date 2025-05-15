from microstrain import Microstrain
from witmotion import WitMotion
from datetime import datetime
from ublox import Ubox
import argparse
import time
import os
import sys

if sys.platform.startswith("linux"):
    LINUX = True
else:
    LINUX = False

TIME = None


def set_time():
    print("Time set to")
    os.system('sudo date --set="%s"' % TIME)


def main(args):
    if args.witmotion:
        witmotion = WitMotion(imu_port=args.witmotion[0], baud_rate=int(
            args.witmotion[1]), save_data=args.save, save_path=args.path)
        witmotion.start()
        print(f"Witmotion on {args.witmotion[0]} at {args.witmotion[1]} baud")
    if args.ublox_pro:
        ublox_pro = Ubox(gps_port=args.ublox_pro[0], baud_rate=int(
            args.ublox_pro[1]), fusion=False, save_data=args.save, save_path=args.path)
        ublox_pro.start()
        print(f"Ublox Pro on {args.ublox_pro[0]} at {args.ublox_pro[1]} baud")
    if args.ublox_fusion:
        ublox_fusion = Ubox(gps_port=args.ublox_fusion[0], baud_rate=int(
            args.ublox_fusion[1]), fusion=True, save_data=args.save, save_path=args.path)
        ublox_fusion.start()
        print(
            f"Ublox Fusion on {args.ublox_fusion[0]} at {args.ublox_fusion[1]} baud")
    if args.microstrain:
        microstrain = Microstrain(imu_port=args.microstrain[0], baud_rate=int(
            args.microstrain[1]), save_data=args.save, save_path=args.path)
        microstrain.start()
        print(
            f"Microstrain on {args.microstrain[0]} at {args.microstrain[1]} baud")
    print(f"Path: {args.path}")

    if LINUX:
        global TIME
        TIME = datetime.datetime.now()
        set_time()    # Start the GPS and IMU
        count = 0

    try:
        while True:
            if args.ublox_pro:
                ublox_data = ublox_pro.get_last_data()
                if ublox_data:
                    print("Ublox Pro Data:", ublox_data)
                    if count < 2 and LINUX:
                        TIME = ublox_data["gpstime"]
                        set_time()
                        count += 1

            if args.ublox_fusion:
                ublox_fusion_data = ublox_fusion.get_last_data()
                if ublox_fusion_data:
                    print("Ublox Fusion Data:", ublox_fusion_data)
                    if count < 2 and not args.ublox_pro and LINUX:
                        TIME = ublox_fusion_data["gpstime"]
                        set_time()
                        count += 1

            if args.witmotion:
                witmotion_data = witmotion.get_last_data()
                if witmotion_data:
                    print("Witmotion Data:", witmotion_data)

            if args.microstrain:
                microstrain_data = microstrain.get_last_data()
                if microstrain_data:
                    print("Microstrain Data:", microstrain_data)

            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        if args.witmotion:
            witmotion.stop()
        if args.ublox_pro:
            ublox_pro.stop()
        if args.ublox_fusion:
            ublox_fusion.stop()
        if args.microstrain:
            microstrain.stop()
        print("Stopped all threads.")
    except Exception as e:
        print(f"An error occurred: {e}")
        if args.witmotion:
            witmotion.stop()
        if args.ublox_pro:
            ublox_pro.stop()
        if args.ublox_fusion:
            ublox_fusion.stop()
        if args.microstrain:
            microstrain.stop()
        print("Stopped all threads.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPS and IMU Data Logger")

    parser.add_argument("--witmotion", nargs=2, metavar=("PORT", "BAUDRATE"),
                        help="Witmotion: <port> <baudrate> (default baudrate: 115200)")
    parser.add_argument("--ublox-pro", nargs=2, metavar=("PORT", "BAUDRATE"),
                        help="Ublox Simple RTK2B/3B Pro: <port> <baudrate> (default baudrate: 115200)")
    parser.add_argument("--ublox-fusion", nargs=2, metavar=("PORT", "BAUDRATE"),
                        help="Ublox Simple RTK2B/3B Fusion: <port> <baudrate> (default baudrate: 115200)")
    parser.add_argument("--microstrain", nargs=2, metavar=("PORT", "BAUDRATE"),
                        help="Microstrain 3DM-CV7-AHRS: <port> <baudrate> (default baudrate: 115200)")

    parser.add_argument("--save", default=False,
                        action="store_true", help="Enable saving of data")
    parser.add_argument("--path", type=str, default="test",
                        help="Output path (default: test)")

    args = parser.parse_args()

    # Set default baudrates if not provided
    default_baud = "115200"
    if args.witmotion and len(args.witmotion) == 1:
        args.witmotion.append(default_baud)
    if args.ublox_pro and len(args.ublox_pro) == 1:
        args.ublox_pro.append(default_baud)
    if args.ublox_fusion and len(args.ublox_fusion) == 1:
        args.ublox_fusion.append(default_baud)
    if args.microstrain and len(args.microstrain) == 1:
        args.microstrain.append(default_baud)

    main(args)
