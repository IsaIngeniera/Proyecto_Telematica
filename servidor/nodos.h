/*
 * nodos.h - Estado del servidor: tabla de nodos, alertas y deteccion
 * de anomalias.
 *
 * Esta capa conoce el protocolo (usa protocolo.h para parsear/validar
 * y construir respuestas) pero no conoce sockets: no hace recv/send,
 * eso vive en server.c.
 *
 * Responsable: Isa O (rol "Servidor central (C)")
 */

#ifndef NODOS_H
#define NODOS_H

#include <stddef.h>

#define MAX_NODES          64
#define MAX_ALERTS         200
#define ACTIVE_TIMEOUT_SEC 20        /* sin telemetria en este tiempo -> INACTIVE */

/* Umbrales de anomalia. Deben quedar por DEBAJO de los valores que
 * nodo.py fuerza cuando simula una anomalia (TEMP=45, HUM=90,
 * ENERGY=60, VIBRATION=12), para que el servidor SI las detecte. */
#define TEMP_THRESHOLD       40.0
#define HUM_THRESHOLD        85.0
#define ENERGY_THRESHOLD     50.0
#define VIBRATION_THRESHOLD  10.0

/* Procesa una linea TELEMETRY recibida por UDP: valida el mensaje,
 * registra/actualiza el nodo en la tabla y dispara una alerta si el
 * valor supera el umbral. No devuelve nada (UDP no responde). */
void process_telemetry_line(char *line, const char *from_addr);

/* Procesa una linea de consulta de un operador (llega por TCP) y
 * escribe la respuesta correspondiente en 'response'. */
void process_operator_line(char *line, char *response, size_t response_size);

/* Contadores y estado que main() reporta al apagar el servidor. */
void nodos_get_stats(int *node_count_out, int *alert_count_out,
                      unsigned long *udp_received_out,
                      unsigned long *udp_invalid_out,
                      unsigned long *tcp_queries_out);

#endif /* NODOS_H */