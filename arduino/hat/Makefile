# set the board to uno because nano has incorrect fuses for new bootloader
ARDUINO_DIR = /home/stelian/Arduino/arduino-1.8.16/
BOARD_TAG = uno
BOARD_SUB   = atmega328p

CPPFLAGS = -I.
ARDUINO_LIBS = IRLib2 IRLibProtocols IRLibRecvPCI
USER_LIB_PATH = $(realpath IRLib2)

ISP_PROG = avrispmkii

ARDMK_DIR = /home/stelian/Arduino/arduino-1.8.16/
include Arduino-noserial.mk
