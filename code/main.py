import os
import time
import datetime
import argparse
from ublox import Ublox
from witmotion import WitMotion
from microstrain import Microstrain
from multiprocessing import Process, Queue

TIME = None

def set_time():
    print("Time set to")
    os.system('sudo date --set="%s"' % TIME)


def main(args):
    processes = []
    queues = []
    currentTime = datetime.datetime.now()
    currentTime = currentTime.strftime("%Y-%m-%d_%H-%M-%S")
    args.path = os.path.join(args.path, currentTime)

    if args.witmotion:
        witmotion_queue = Queue()
        witmotion = Process(
                    target=WitMotion,
                    kwargs={
                        "imu_port": args.witmotion[0],
                        "baud_rate": int(args.witmotion[1]),
                        "save_data": args.save,
                        "save_path":  args.path,
                        "imu_queue": witmotion_queue,
                        "display_timer": 0.1,
                    }
                )
        processes.append(witmotion)
        queues.append(witmotion_queue)
        witmotion.start()
        print(f"Witmotion on {args.witmotion[0]} at {args.witmotion[1]} baud")
    if args.ublox_pro:
        ublox_pro_queue = Queue()
        ublox_pro = Process(
                    target=Ublox,
                    kwargs={
                        "gps_port": args.ublox_pro[0],
                        "baud_rate": int(args.ublox_pro[1]),
                        "fusion": False,
                        "save_data": args.save,
                        "save_path": args.path,
                        # "ntrip_details": self.mainWindow.ntrip_details,
                        "gps_queue": ublox_pro_queue,
                        "display_timer": 0.1,
                    }
                )
        
        processes.append(ublox_pro)
        queues.append(ublox_pro_queue)
        ublox_pro.start()
        print(f"Ublox Pro on {args.ublox_pro[0]} at {args.ublox_pro[1]} baud")
    if args.ublox_fusion:
        ublox_fusion_queue = Queue()
        ublox_fusion = Process(
                    target=Ublox,
                    kwargs={
                        "gps_port": args.ublox_fusion[0],
                        "baud_rate": int(args.ublox_fusion[1]),
                        "fusion": True,
                        "save_data": args.save,
                        "save_path": args.path,
                         # "ntrip_details": self.mainWindow.ntrip_details,
                        "gps_queue": ublox_fusion_queue,
                        "display_timer": 0.1,
                    }
                )
        processes.append(ublox_fusion)
        queues.append(ublox_fusion_queue)
        ublox_fusion.start()
        print(
            f"Ublox Fusion on {args.ublox_fusion[0]} at {args.ublox_fusion[1]} baud")
    if args.microstrain:
        microstrain_queue = Queue()
        microstrain = Process(
                    target=Microstrain,
                    kwargs={
                        "imu_port": args.microstrain[0],
                        "baud_rate": int(args.microstrain[1]),
                        "save_data": args.save,
                        "save_path":  args.path,
                        "imu_queue": microstrain_queue,
                        "display_timer": 0.1,
                    }
                )
        processes.append(microstrain)
        queues.append(microstrain_queue)
        microstrain.start()
        print(
            f"Microstrain on {args.microstrain[0]} at {args.microstrain[1]} baud")
    print(f"Path: {args.path}")

    # Start the GPS and IMU
    global TIME
    TIME = datetime.datetime.now()
    set_time()    # Start the GPS and IMU
    count = 0

    try:
        while True:
            for queue in queues:
                if not queue.empty():
                    data = queue.get()
                    print("Data:", data)
            time.sleep(0.1)
    except KeyboardInterrupt:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()
            
        for queue in queues:
            queue.close()
            queue.join_thread()



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
