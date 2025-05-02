"""
This script reads GPS and IMU data and writes it to a file.
The GPS data is read from the gpsd daemon, and the IMU data is read from a WitMotion IMU.
"""

import os
import gpsd
import time
import argparse
import datetime
from IMU import IMUData

def main(args):
    # Configure the serial connection
    imu_port = args.imu_port
    baud_rate = args.baud_rate

    # Connect to the gpsd daemon
    gpsd.connect()
    print("Connected to gpsd")

    # GPS data template
    gps_info = {
        "time": None,
        "system_time": datetime.datetime.now().isoformat(),
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "azimuth": None,
        "mode": None,
        "satellites": None,
    }

    imu = IMUData(imu_port, baud_rate)
    imu.start()
    print(f"Connected to IMU on {imu_port}")

    # Create a file name based on current date and time
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"{timestamp}.txt"

    # Open the file for writing
    with open(filename, "w") as file:
        print(f"Writing GPS and IMU data to file: {filename}")

        # Write headers
        header = ", ".join(gps_info.keys()) + ", " + ", ".join(imu.last_data.keys())
        file.write(header + "\n")

        try:
            while True:
                # Fetch current GPS data
                try:
                    gps_data = gpsd.get_current()
                    gps_info = {
                        "time": gps_data.get_time().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "system_time": datetime.datetime.now().isoformat(),
                        "latitude": gps_data.lat,
                        "longitude": gps_data.lon,
                        "altitude": gps_data.alt,
                        "azimuth": gps_data.track,
                        "mode": gps_data.mode,
                        "satellites": gps_data.sats,
                    }
                except Exception as e:
                    gps_info = {"error": str(e)}

                # Get latest IMU data
                imu_data = ", ".join(str(value) for value in imu.last_data.values())

                # Write the combined data to the file
                file_data = (
                    ", ".join(str(value) for value in gps_info.values())
                    + ", "
                    + imu_data
                )
                file.write(file_data + "\n")
                file.flush()

                # Print to console for real-time feedback
                file_data_list = file_data.split(", ")
                formatted_last_9 = [
                    f"{float(value):.3f}" if value != "None" else value
                    for value in file_data_list[-9:]
                ]
                output_data = file_data_list[:-9] + formatted_last_9

                # Print the formatted data
                os.system("clear")  # For Linux/Mac, use 'cls' for Windows
                print(f"{header}")
                print(f"{' | '.join(map(str, output_data))} ")
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nExiting GPS and IMU reader.")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            imu.stop()
            print("Exited")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read GPS and IMU data.")
    parser.add_argument(
        "--imu_port",
        type=str,
        default="/dev/ttyUSB0",
        help="The serial port for the IMU (default: /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--baud_rate",
        type=int,
        default=115200,
        help="The baud rate for the IMU (default: 115200)",
    )

    args = parser.parse_args()
    main(args)
