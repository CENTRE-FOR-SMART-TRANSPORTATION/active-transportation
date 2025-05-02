TEMPLATE = app
QT       += core gui
QT       += serialport
QT       += qml quick
QT       += quickwidgets
QT       += location positioning
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets printsupport

CONFIG += c++17

# You can make your code fail to compile if it uses deprecated APIs.
# In order to do so, uncomment the following line.
#DEFINES += QT_DISABLE_DEPRECATED_BEFORE=0x060000    # disables all the APIs deprecated before Qt 6.0.0

SOURCES += \
    main.cpp \
    src/mainwindow.cpp \
    src/sensor.cpp \
    # src/serial/serialthread.cpp \
    src/serial/witmotion/witmotion.cpp \
    src/thirdparty/witmotion/serial.c \
    src/thirdparty/witmotion/wit_c_sdk.c \
    ui/qledlabel.cpp

HEADERS += \
    src/mainwindow.h \
    src/sensor.h \
    # src/serial/serialthread.h \
    src/serial/datatypes.h \
    src/serial/witmotion/witmotion.h \
    src/thirdparty/witmotion/serial.h \
    src/thirdparty/witmotion/wit_c_sdk.h \
    src/thirdparty/witmotion/REG.h \
    ui/qledlabel.h

FORMS += \
    ui/sensor.ui \
    ui/mainwindow.ui

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target
