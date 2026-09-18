/*
 * protocolo.h - Constantes y utilidades del protocolo de aplicacion
 * de la Plataforma Distribuida de Telemetria.
 *
 * Este archivo debe mantenerse alineado con protocolo.py (nodos/cliente
 * en Python). Aqui solo vive la CAPA DE PROTOCOLO: formato de mensajes,
 * separadores, codigos de error y parseo/validacion sintactica basica.
 * No conoce nada sobre nodos, alertas ni sockets: eso vive en nodos.h
 * y server.c respectivamente.
 *
 * Responsable: Isa O (rol "Servidor central (C)")
 */

#ifndef PROTOCOLO_H
#define PROTOCOLO_H

#include <stddef.h>

/* ---------------------------------------------------------------- */
/* Framing / limites del protocolo (alineado con protocolo.py)        */
/* ---------------------------------------------------------------- */

#define FIELD_SEP   "|"
#define LIST_SEP    ","
#define RECORD_SEP  ";"

#define RECV_BUF_SIZE      1024   /* MAX_MESSAGE_BYTES del protocolo */
#define CLIENT_BUF_SIZE    2048
#define MAX_FIELDS         8

/* ---------------------------------------------------------------- */
/* Tipos de mensaje (peticion)                                        */
/* ---------------------------------------------------------------- */

#define MSG_TELEMETRY   "TELEMETRY"
#define MSG_GET_STATUS  "GET_STATUS"
#define MSG_GET_NODES   "GET_NODES"
#define MSG_GET_NODE    "GET_NODE"
#define MSG_GET_ALERTS  "GET_ALERTS"

/* ---------------------------------------------------------------- */
/* Tipos de mensaje (respuesta)                                       */
/* ---------------------------------------------------------------- */

#define MSG_STATUS      "STATUS"
#define MSG_NODES       "NODES"
#define MSG_NODE_DATA   "NODE_DATA"
#define MSG_ALERTS      "ALERTS"
#define MSG_ERROR       "ERROR"

#define VAL_OK          "OK"
#define VAL_NO_DATA     "NO_DATA"

/* ---------------------------------------------------------------- */
/* Variables validas                                                  */
/* ---------------------------------------------------------------- */

#define VAR_TEMP        "TEMP"
#define VAR_HUM         "HUM"
#define VAR_ENERGY      "ENERGY"
#define VAR_VIBRATION   "VIBRATION"

/* ---------------------------------------------------------------- */
/* Tipos de alerta                                                    */
/* ---------------------------------------------------------------- */

#define ALERT_TEMP_HIGH       "TEMP_HIGH"
#define ALERT_HUM_HIGH        "HUM_HIGH"
#define ALERT_ENERGY_HIGH     "ENERGY_HIGH"
#define ALERT_VIBRATION_HIGH  "VIBRATION_HIGH"

/* ---------------------------------------------------------------- */
/* Codigos / descripciones de error                                   */
/* ---------------------------------------------------------------- */

#define ERR_BAD_REQUEST  "400"
#define ERR_NOT_FOUND    "404"
#define ERR_SERVER       "500"

#define ERR_INVALID_MESSAGE        "INVALID_MESSAGE"
#define ERR_INVALID_NODE_ID        "INVALID_NODE_ID"
#define ERR_INVALID_SEQUENCE       "INVALID_SEQUENCE"
#define ERR_INVALID_VARIABLE       "INVALID_VARIABLE"
#define ERR_INVALID_VALUE          "INVALID_VALUE"
#define ERR_MESSAGE_TOO_LONG       "MESSAGE_TOO_LONG"
#define ERR_NODE_NOT_FOUND         "NODE_NOT_FOUND"
#define ERR_INTERNAL_SERVER_ERROR  "INTERNAL_SERVER_ERROR"

/* ---------------------------------------------------------------- */
/* Utilidad de logging con timestamp, usada por todo el servidor      */
/* ---------------------------------------------------------------- */

void log_line(const char *fmt, ...);

/* ---------------------------------------------------------------- */
/* Parseo y validacion sintactica de bajo nivel                       */
/* ---------------------------------------------------------------- */

/* Separa 'line' en campos por '|' (modifica 'line' in-place). */
int split_fields(char *line, char *fields[], int max_fields);

/* Valida formato NODE## (2 digitos), igual que NODE_ID_PATTERN en protocolo.py */
int is_valid_node_id(const char *id);

int is_valid_variable(const char *v);

int parse_double(const char *s, double *out);
int parse_long(const char *s, long *out);

/* ---------------------------------------------------------------- */
/* Construccion de mensajes de error (no depende del estado del servidor) */
/* ---------------------------------------------------------------- */

void build_error(char *out, size_t out_size, const char *code, const char *desc);

#endif /* PROTOCOLO_H */