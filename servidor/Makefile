CC      = gcc
CFLAGS  = -Wall -Wextra -O2
TARGET  = server
SOURCES = protocolo.c nodos.c server.c
HEADERS = protocolo.h nodos.h

.PHONY: all clean run

all: $(TARGET)

$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCES)

# Uso: make run UDP=5000 TCP=6000
run: $(TARGET)
	./$(TARGET) $(or $(UDP),5000) $(or $(TCP),6000)

clean:
	rm -f $(TARGET)