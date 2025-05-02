#ifndef DATATYPES_H
#define DATATYPES_H

#include <QObject>
#include <QMap>
#include <QDebug>
#include <QSet>
#include <QStringList>

struct IMUData {
    QString system_time;
    QString timestamp;

    float accX = 0, accY = 0, accZ = 0;
    float gyroX = 0, gyroY = 0, gyroZ = 0;
    float roll = 0, pitch = 0, yaw = 0;
    float qX = 0, qY = 0, qZ = 0, qW = 0;

    QSet<QString> validFields;

    static QStringList fieldOrder() {
        return {"system_time", "timestamp",
                "accX", "accY", "accZ",
                "gyroX", "gyroY", "gyroZ",
                "roll", "pitch", "yaw",
                "qX", "qY", "qZ", "qW"};
    }

    void set(const QString& key, const QString& value) {
        bool ok = false;
        float f = value.toFloat(&ok);

        if (key == "system_time") system_time = value;
        else if (key == "timestamp") timestamp = value;
        else if (ok) {
            if (key == "accX") accX = f;
            else if (key == "accY") accY = f;
            else if (key == "accZ") accZ = f;
            else if (key == "gyroX") gyroX = f;
            else if (key == "gyroY") gyroY = f;
            else if (key == "gyroZ") gyroZ = f;
            else if (key == "roll") roll = f;
            else if (key == "pitch") pitch = f;
            else if (key == "yaw") yaw = f;
            else if (key == "qX") qX = f;
            else if (key == "qY") qY = f;
            else if (key == "qZ") qZ = f;
            else if (key == "qW") qW = f;
        }

        validFields.insert(key);
    }

    QString getAsString(const QString& key) const {
        if (key == "system_time") return system_time;
        if (key == "timestamp") return timestamp;
        if (key == "accX") return QString::number(accX, 'f', 4);
        if (key == "accY") return QString::number(accY, 'f', 4);
        if (key == "accZ") return QString::number(accZ, 'f', 4);
        if (key == "gyroX") return QString::number(gyroX, 'f', 4);
        if (key == "gyroY") return QString::number(gyroY, 'f', 4);
        if (key == "gyroZ") return QString::number(gyroZ, 'f', 4);
        if (key == "roll") return QString::number(roll, 'f', 4);
        if (key == "pitch") return QString::number(pitch, 'f', 4);
        if (key == "yaw") return QString::number(yaw, 'f', 4);
        if (key == "qX") return QString::number(qX, 'f', 4);
        if (key == "qY") return QString::number(qY, 'f', 4);
        if (key == "qZ") return QString::number(qZ, 'f', 4);
        if (key == "qW") return QString::number(qW, 'f', 4);
        return {};
    }

    QString toCSVRow() const {
        QStringList values;
        for (const QString &key : fieldOrder()) {
            values << getAsString(key);
        }
        return values.join(",");
    }

    bool full() const {
        for (const QString& key : fieldOrder()) {
            if (!validFields.contains(key)) {
                return false;
            }
        }
        return true;
    }

    void add(const IMUData &other) {
        for (const QString& key : fieldOrder()) {
            if (other.validFields.contains(key)) {
                set(key, other.getAsString(key));
            }
        }
    }

    void printData() const {
        qDebug() << toCSVRow();
    }

    void clear() {
        system_time.clear();
        timestamp.clear();

        accX = accY = accZ = 0.0f;
        gyroX = gyroY = gyroZ = 0.0f;
        roll = pitch = yaw = 0.0f;
        qX = qY = qZ = qW = 0.0f;

        validFields.clear();
    }

};

/// ─────────────────────────────────────────────
///                MACROS
/// ─────────────────────────────────────────────

// Assign float directly with formatted string conversion
#define IMU_SET_FLOAT(data, key, value) \
data.set(key, QString::number(value, 'f', 4))

// Assign string directly
#define IMU_SET_STR(data, key, value) \
    data.set(key, value)

#endif // DATATYPES_H
