ARDUINO_DIR = /home/stelian/Arduino/arduino-1.8.18/
BOARD_TAG = uno
#BOARD_TAG = mega32-16
MCU = atmega32

ISP_PROG = avrispmkii

CPPFLAGS += -I. -I$(OBJDIR)

all: $(OBJDIR)/charset.h $(TARGET_EEP) $(TARGET_HEX)

$(OBJDIR)/charset.h: make_charset.py font.ttf
	@$(MKDIR) $(OBJDIR)
	python3 make_charset.py > $(OBJDIR)/charset.h

include $(ARDUINO_DIR)/Arduino.mk
