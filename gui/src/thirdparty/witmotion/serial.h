#ifndef SERIAL_H
#define SERIAL_H

#ifdef __cplusplus
extern "C" {
#endif

#include <linux/types.h>
#include <stdio.h>
#include <time.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <string.h>
#include <linux/rtc.h>
#include <termios.h>


void serial_close(int fd);

int serial_open(const char* dev, unsigned int baud);

int serial_read_data(int fd, unsigned char *val, int len);

int serial_write_data(int fd, unsigned char *val, int len);


#endif
#ifdef __cplusplus
}
#endif
