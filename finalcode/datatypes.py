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
    "diffStation": None
}

imu_template = {
    "imutime": None,
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
    "rtcm_msg": 0,
    "rtcm_crc": 0,
}

calib_status_template = {
    "gyroX_calib": "Not Calibrated",
    "gyroY_calib": "Not Calibrated",
    "gyroZ_calib": "Not Calibrated",
    "accX_calib": "Not Calibrated",
    "accY_calib": "Not Calibrated",
    "accZ_calib": "Not Calibrated",
}
