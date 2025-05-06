time_template = {
    "systemtime": None,
    "systemepoch": None,
}

gps_template = {
    "gpstime": None,
    "gpsepoch": None,
    "lat": None,
    "lon": None,
    "alt": None,
    "azimuth": None,
}

imu_template = {
    "roll": None,       # Angles (in radians)
    "pitch": None,
    "yaw": None,
    "accX": None,       # Acceleration without gravity (in m/s^2)
    "accY": None,
    "accZ": None,
    "gyroX": None,      # Angular velocity (in rad/s)
    "gyroY": None,
    "gyroZ": None,
    "qX": None,        # Quaternion
    "qY": None,
    "qZ": None,
    "qW": None,
}

status_template = {
    "fusionMode": 0,
    "imuStatus": 0,
    "gpsFix": 0,
    "nvSat": 0,
    "gpsAcc (H, V)": (0, 0),
    "rollAcc": 0,
    "pitchAcc": 0,
    "yawAcc": 0,
}

calib_status_template = {
    "gyroX": "Not Calibrated",
    "gyroY": "Not Calibrated",
    "gyroZ": "Not Calibrated",
    "accX": "Not Calibrated",
    "accY": "Not Calibrated",
    "accZ": "Not Calibrated",
}
