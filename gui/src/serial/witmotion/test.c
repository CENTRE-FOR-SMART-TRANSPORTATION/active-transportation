#include "serial.h"
#include "wit_c_sdk.h"
#include "REG.h"
#include <stdint.h>

static void SensorDataUpdate(uint32_t uiReg, uint32_t uiRegNum)
{
    int i;
    for (i = 0; i < uiRegNum; i++)
    {
        switch (uiReg)
        {

        case MS:
        {
            int YY = sReg[YYMM] & 0xff;
            int Mo = (sReg[YYMM] & 0xff00) >> 8;
            int DD = sReg[DDHH] & 0xff;
            int HH = (sReg[DDHH] & 0xff00) >> 8;
            int Mi = sReg[MMSS] & 0xff;
            int SS = (sReg[MMSS] & 0xff00) >> 8;
            int Ms = sReg[MS];
            printf("Date: %02d/%02d/%02d, Time: %02d:%02d:%02d.%03d\n",
                   YY, Mo, DD, HH, Mi, SS, Ms);
        }
        break;

        case AZ:
        {
            float fAcc[3];
            int i;
            for (i = 0; i < 3; i++)
            {
                fAcc[i] = sReg[AX + i] / 32768.0f * 16.0f;
            }
            printf("acc:%.3f %.3f %.3f\n", fAcc[0], fAcc[1], fAcc[2]);
        }
        break;

        case GZ:
        {
            float fGyro[3];
            int i;
            for (i = 0; i < 3; i++)
            {
                fGyro[i] = sReg[GX + i] / 32768.0f * 2000.0f;
            }
            printf("gyro:%.3f %.3f %.3f\n", fGyro[0], fGyro[1], fGyro[2]);
        }
        break;

        case HZ:
        {
            // Scaling is to +/-4900 uTesla.
            printf("mag:%d %d %d\n", sReg[HX], sReg[HY], sReg[HZ]);
        }
        break;

        case Yaw:
        {
            float fAngle[3];
            int i;
            for (i = 0; i < 3; i++)
            {
                fAngle[i] = sReg[Roll + i] / 32768.0f * 180.0f;
            }
            printf("angle:%.3f %.3f %.3f\n", fAngle[0], fAngle[1], fAngle[2]);
        }
        break;

        case GPSHeight:
        {
            double longitude, latitude, height;
            {
                int32_t value = sReg[LonL] + (sReg[LonH] << 16);
                int degrees = value / 10000000;
                double minutes = (value % 10000000) / 100000.0;
                longitude = degrees + minutes / 60;
            }
            {
                int32_t value = sReg[LatL] + (sReg[LatH] << 16);
                int degrees = value / 10000000;
                double minutes = (value % 10000000) / 100000.0;
                latitude = degrees + minutes / 60;
            }
            {
                int32_t value = sReg[GPSHeight];
                height = value / 10.0;
            }
            printf("longitude:%11.6lf, latitude:%11.6lf, height: %6.2lf\n", longitude, latitude, height);
        }
        break;

        case HeightH:
        {
            int32_t value = sReg[HeightL] + (sReg[HeightH] << 16);
            double height = value * 100;
            printf("height:%.2lf\n", height);
        }
        break;

        default:
            break;
        }
        uiReg++;
    }
}

int main(int argc, char *argv[])
{
    if (argc != 3)
    {
        printf("Usage: %s DEVICE_NAME BAUD\n", argv[0]);
        printf("       DEVICE_NAME is the name of the serial device, like /dev/ttyUSB0\n");
        printf("       BAUD is the baud rate of the serial device, like 230400\n");
        return 1;
    }
    char *dev = argv[1];
    int baud = atoi(argv[2]);

    WitInit(WIT_PROTOCOL_NORMAL, 0x50);
    WitRegisterCallBack(SensorDataUpdate);

    int fd = -1;
    fd = serial_open(dev, baud);
    if (fd < 0)
    {
        printf("Could not open %s with baud %d\n", dev, baud);
        return 2;
    }

    printf("\n********************** Found device ************************\n");

    while (1)
    {
        char cBuff[1];
        while (serial_read_data(fd, cBuff, 1))
        {
            WitSerialDataIn(cBuff[0]);
        }
    }

    serial_close(fd);
    return 0;
}
