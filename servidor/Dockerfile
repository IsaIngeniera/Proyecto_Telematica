FROM debian:bookworm-slim

WORKDIR /app

# Instalar gcc y make en la misma imagen
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar el código fuente y encabezados
COPY Makefile protocolo.c protocolo.h nodos.c nodos.h server.c ./

# Compilar el binario
RUN make clean && make

# Exponer los puertos de telemetría (UDP) y operador (TCP)
EXPOSE 5000/udp
EXPOSE 6000/tcp

# Ejecutar el servidor
CMD ["./server", "5000", "6000"]