OBJS = udpserver/udpserver.cpp
OBJ_NAME = x64/udpserver

MKDIR_P := mkdir -p
OUT_DIR := x64

.PHONY: directories all clean

all: $(OUT_DIR)/program

directories: $(OUT_DIR)

$(OUT_DIR):
	${MKDIR_P} $(OUT_DIR)

$(OUT_DIR)/program: | directories
	g++ $(OBJS) -o $(OBJ_NAME)

clean: rm -rf $(OUT_DIR)
