/*
 * nodos.c - Tabla de nodos, alertas y logica de negocio del servidor.
 */

#include "nodos.h"
#include "protocolo.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* ---------------------------------------------------------------- */
/* Estado del servidor                                                */
/* ---------------------------------------------------------------- */

typedef struct {
    char   id[16];
    int    used;          /* 1 si esta ranura tiene un nodo registrado */
    time_t last_seen;
    long   last_sequence;

    double temp;      int has_temp;
    double hum;       int has_hum;
    double energy;    int has_energy;
    double vibration; int has_vibration;
} Node;

typedef struct {
    char   node_id[16];
    char   alert_type[24];
    double value;
    time_t timestamp;
} Alert;

static Node nodes[MAX_NODES];
static int  node_count = 0;

static Alert alerts[MAX_ALERTS];
static int   alert_count = 0;      /* cuantas alertas validas hay (circular) */
static int   alert_next  = 0;      /* proxima posicion a escribir */

/* Contadores exigidos por el enunciado (S11) */
static unsigned long stat_udp_received = 0;   /* datagramas UDP validos (TELEMETRY aceptado) */
static unsigned long stat_udp_invalid  = 0;   /* datagramas UDP descartados por mal formados  */
static unsigned long stat_tcp_queries  = 0;   /* consultas TCP atendidas */

/* ---------------------------------------------------------------- */
/* Tabla de nodos                                                     */
/* ---------------------------------------------------------------- */

static Node *find_node(const char *id) {
    for (int i = 0; i < MAX_NODES; i++) {
        if (nodes[i].used && strcmp(nodes[i].id, id) == 0) return &nodes[i];
    }
    return NULL;
}

static Node *find_or_create_node(const char *id) {
    Node *n = find_node(id);
    if (n) return n;

    for (int i = 0; i < MAX_NODES; i++) {
        if (!nodes[i].used) {
            memset(&nodes[i], 0, sizeof(Node));
            strncpy(nodes[i].id, id, sizeof(nodes[i].id) - 1);
            nodes[i].used = 1;
            node_count++;
            log_line("Nuevo nodo registrado: %s", id);
            return &nodes[i];
        }
    }
    log_line("ADVERTENCIA: tabla de nodos llena (MAX_NODES=%d), se descarta %s",
              MAX_NODES, id);
    return NULL; /* servidor sigue vivo, simplemente no registra mas nodos */
}

static int node_is_active(const Node *n, time_t now) {
    return (now - n->last_seen) <= ACTIVE_TIMEOUT_SEC;
}

/* ---------------------------------------------------------------- */
/* Alertas                                                            */
/* ---------------------------------------------------------------- */

static void add_alert(const char *node_id, const char *alert_type, double value) {
    Alert *a = &alerts[alert_next];
    strncpy(a->node_id, node_id, sizeof(a->node_id) - 1);
    a->node_id[sizeof(a->node_id) - 1] = '\0';
    strncpy(a->alert_type, alert_type, sizeof(a->alert_type) - 1);
    a->alert_type[sizeof(a->alert_type) - 1] = '\0';
    a->value = value;
    a->timestamp = time(NULL);

    alert_next = (alert_next + 1) % MAX_ALERTS;
    if (alert_count < MAX_ALERTS) alert_count++;

    log_line("ALERTA generada: %s %s=%.2f", node_id, alert_type, value);
}

/* Revisa el valor recien recibido y genera alerta si supera el umbral */
static void check_anomaly(const char *node_id, const char *variable, double value) {
    if (strcmp(variable, VAR_TEMP) == 0 && value > TEMP_THRESHOLD) {
        add_alert(node_id, ALERT_TEMP_HIGH, value);
    } else if (strcmp(variable, VAR_HUM) == 0 && value > HUM_THRESHOLD) {
        add_alert(node_id, ALERT_HUM_HIGH, value);
    } else if (strcmp(variable, VAR_ENERGY) == 0 && value > ENERGY_THRESHOLD) {
        add_alert(node_id, ALERT_ENERGY_HIGH, value);
    } else if (strcmp(variable, VAR_VIBRATION) == 0 && value > VIBRATION_THRESHOLD) {
        add_alert(node_id, ALERT_VIBRATION_HIGH, value);
    }
}

/* ---------------------------------------------------------------- */
/* Construccion de mensajes de respuesta                              */
/* ---------------------------------------------------------------- */

static void build_status(char *out, size_t out_size) {
    time_t now = time(NULL);
    int active = 0;
    for (int i = 0; i < MAX_NODES; i++) {
        if (nodes[i].used && node_is_active(&nodes[i], now)) active++;
    }
    snprintf(out, out_size,
             "%s%sOK%sREGISTERED=%d%sACTIVE=%d%sALERTS=%d%sUDP_RECEIVED=%lu%sUDP_LOST=%lu\n",
             MSG_STATUS, FIELD_SEP, FIELD_SEP, node_count, FIELD_SEP, active,
             FIELD_SEP, alert_count, FIELD_SEP, stat_udp_received,
             FIELD_SEP, stat_udp_invalid);
}

static void build_nodes_list(char *out, size_t out_size) {
    time_t now = time(NULL);
    char records[900] = {0};
    int first = 1;
    int count = 0;

    for (int i = 0; i < MAX_NODES; i++) {
        if (!nodes[i].used) continue;
        count++;
        const char *state = node_is_active(&nodes[i], now) ? "ACTIVE" : "INACTIVE";
        char entry[128];

        /* nodes[i].id nunca supera 6 caracteres (formato NODE##, validado por
         * is_valid_node_id antes de registrarse), asi que este snprintf jamas
         * trunca datos reales. GCC no logra probarlo en esta cadena de
         * snprintf anidados/inlineados y emite un falso positivo conocido de
         * -Wformat-truncation; se silencia solo aqui, no para todo el archivo. */
        #pragma GCC diagnostic push
        #pragma GCC diagnostic ignored "-Wformat-truncation"
        snprintf(entry, sizeof(entry), "%s%s%s%s%s", first ? "" : RECORD_SEP,
                 nodes[i].id, LIST_SEP, state, "");
        #pragma GCC diagnostic pop
        strncat(records, entry, sizeof(records) - strlen(records) - 1);
        first = 0;
    }

    if (count == 0) {
        snprintf(out, out_size, "%s%sOK%s0%s%s\n", MSG_NODES, FIELD_SEP, FIELD_SEP,
                 FIELD_SEP, VAL_NO_DATA);
    } else {
        snprintf(out, out_size, "%s%sOK%s%d%s%s\n", MSG_NODES, FIELD_SEP, FIELD_SEP,
                 count, FIELD_SEP, records);
    }
}

static void format_value_or_no_data(char *buf, size_t buf_size, const char *name,
                                     int has_value, double value) {
    if (has_value) {
        snprintf(buf, buf_size, "%s=%.2f", name, value);
    } else {
        snprintf(buf, buf_size, "%s=%s", name, VAL_NO_DATA);
    }
}

static void build_node_data(char *out, size_t out_size, const Node *n) {
    time_t now = time(NULL);
    const char *state = node_is_active(n, now) ? "ACTIVE" : "INACTIVE";

    char temp_s[32], hum_s[32], energy_s[32], vib_s[32], time_s[32];
    format_value_or_no_data(temp_s, sizeof(temp_s), "TEMP", n->has_temp, n->temp);
    format_value_or_no_data(hum_s, sizeof(hum_s), "HUM", n->has_hum, n->hum);
    format_value_or_no_data(energy_s, sizeof(energy_s), "ENERGY", n->has_energy, n->energy);
    format_value_or_no_data(vib_s, sizeof(vib_s), "VIBRATION", n->has_vibration, n->vibration);

    struct tm tm_seen;
    localtime_r(&n->last_seen, &tm_seen);
    strftime(time_s, sizeof(time_s), "%Y-%m-%dT%H:%M:%S", &tm_seen);

    snprintf(out, out_size, "%s%sOK%s%s%s%s%s%s%s%s%s%s%s%s%s%sLAST_SEEN=%s\n",
             MSG_NODE_DATA, FIELD_SEP, FIELD_SEP, n->id, FIELD_SEP, state,
             FIELD_SEP, temp_s, FIELD_SEP, hum_s, FIELD_SEP, energy_s,
             FIELD_SEP, vib_s, FIELD_SEP, "", time_s);
}

static void build_alerts_list(char *out, size_t out_size) {
    char records[900] = {0};
    int first = 1;
    int total = alert_count;

    /* Recorremos desde la mas antigua a la mas reciente dentro del buffer circular */
    int start = (alert_count < MAX_ALERTS) ? 0 : alert_next;
    for (int i = 0; i < total; i++) {
        int idx = (start + i) % MAX_ALERTS;
        Alert *a = &alerts[idx];

        struct tm tm_a;
        localtime_r(&a->timestamp, &tm_a);
        char time_s[32];
        strftime(time_s, sizeof(time_s), "%Y-%m-%dT%H:%M:%S", &tm_a);

        char entry[96];
        snprintf(entry, sizeof(entry), "%s%s%s%s%s%s%.2f%s%s", first ? "" : RECORD_SEP,
                 a->node_id, LIST_SEP, a->alert_type, LIST_SEP, "", a->value, LIST_SEP, time_s);
        strncat(records, entry, sizeof(records) - strlen(records) - 1);
        first = 0;
    }

    if (total == 0) {
        snprintf(out, out_size, "%s%sOK%s0%s%s\n", MSG_ALERTS, FIELD_SEP, FIELD_SEP,
                 FIELD_SEP, VAL_NO_DATA);
    } else {
        snprintf(out, out_size, "%s%sOK%s%d%s%s\n", MSG_ALERTS, FIELD_SEP, FIELD_SEP,
                 total, FIELD_SEP, records);
    }
}

/* ---------------------------------------------------------------- */
/* Procesamiento de TELEMETRY (llega por UDP)                         */
/* ---------------------------------------------------------------- */

void process_telemetry_line(char *line, const char *from_addr) {
    char *fields[MAX_FIELDS];
    char line_copy[RECV_BUF_SIZE];
    strncpy(line_copy, line, sizeof(line_copy) - 1);
    line_copy[sizeof(line_copy) - 1] = '\0';

    int n = split_fields(line_copy, fields, MAX_FIELDS);

    if (n != 5 || strcmp(fields[0], MSG_TELEMETRY) != 0) {
        stat_udp_invalid++;
        log_line("UDP invalido desde %s: '%s' (%s)", from_addr, line, ERR_INVALID_MESSAGE);
        return;
    }

    const char *node_id = fields[1];
    const char *seq_s   = fields[2];
    const char *variable = fields[3];
    const char *value_s  = fields[4];

    if (!is_valid_node_id(node_id)) {
        stat_udp_invalid++;
        log_line("UDP invalido desde %s: id de nodo invalido '%s'", from_addr, node_id);
        return;
    }

    long sequence;
    if (!parse_long(seq_s, &sequence) || sequence <= 0) {
        stat_udp_invalid++;
        log_line("UDP invalido desde %s: secuencia invalida '%s'", from_addr, seq_s);
        return;
    }

    if (!is_valid_variable(variable)) {
        stat_udp_invalid++;
        log_line("UDP invalido desde %s: variable invalida '%s'", from_addr, variable);
        return;
    }

    double value;
    if (!parse_double(value_s, &value)) {
        stat_udp_invalid++;
        log_line("UDP invalido desde %s: valor invalido '%s'", from_addr, value_s);
        return;
    }

    /* Mensaje valido: registrar/actualizar nodo */
    Node *node = find_or_create_node(node_id);
    if (!node) {
        stat_udp_invalid++; /* no cabe en la tabla, se descarta con seguridad */
        return;
    }

    node->last_seen = time(NULL);
    node->last_sequence = sequence;

    if (strcmp(variable, VAR_TEMP) == 0) { node->temp = value; node->has_temp = 1; }
    else if (strcmp(variable, VAR_HUM) == 0) { node->hum = value; node->has_hum = 1; }
    else if (strcmp(variable, VAR_ENERGY) == 0) { node->energy = value; node->has_energy = 1; }
    else if (strcmp(variable, VAR_VIBRATION) == 0) { node->vibration = value; node->has_vibration = 1; }

    stat_udp_received++;
    log_line("TELEMETRY %s seq=%ld %s=%.2f", node_id, sequence, variable, value);

    check_anomaly(node_id, variable, value);
}

/* ---------------------------------------------------------------- */
/* Procesamiento de consultas TCP de operadores                       */
/* ---------------------------------------------------------------- */

/* Procesa una linea completa recibida de un cliente TCP y escribe la
 * respuesta en 'response'. Nunca cierra el socket desde aqui: eso lo
 * decide el loop principal en server.c segun el resultado de write/recv. */
void process_operator_line(char *line, char *response, size_t response_size) {
    char *fields[MAX_FIELDS];
    char line_copy[CLIENT_BUF_SIZE];
    strncpy(line_copy, line, sizeof(line_copy) - 1);
    line_copy[sizeof(line_copy) - 1] = '\0';

    int n = split_fields(line_copy, fields, MAX_FIELDS);

    if (n == 0) {
        build_error(response, response_size, ERR_BAD_REQUEST, ERR_INVALID_MESSAGE);
        return;
    }

    stat_tcp_queries++;

    if (strcmp(fields[0], MSG_GET_STATUS) == 0 && n == 1) {
        build_status(response, response_size);

    } else if (strcmp(fields[0], MSG_GET_NODES) == 0 && n == 1) {
        build_nodes_list(response, response_size);

    } else if (strcmp(fields[0], MSG_GET_NODE) == 0 && n == 2) {
        const char *node_id = fields[1];
        if (!is_valid_node_id(node_id)) {
            build_error(response, response_size, ERR_BAD_REQUEST, ERR_INVALID_NODE_ID);
            return;
        }
        Node *found = find_node(node_id);
        if (!found) {
            build_error(response, response_size, ERR_NOT_FOUND, ERR_NODE_NOT_FOUND);
            return;
        }
        build_node_data(response, response_size, found);

    } else if (strcmp(fields[0], MSG_GET_ALERTS) == 0 && n == 1) {
        build_alerts_list(response, response_size);

    } else {
        build_error(response, response_size, ERR_BAD_REQUEST, ERR_INVALID_MESSAGE);
    }
}

/* ---------------------------------------------------------------- */
/* Estadisticas para el log de apagado (main en server.c)             */
/* ---------------------------------------------------------------- */

void nodos_get_stats(int *node_count_out, int *alert_count_out,
                      unsigned long *udp_received_out,
                      unsigned long *udp_invalid_out,
                      unsigned long *tcp_queries_out) {
    *node_count_out    = node_count;
    *alert_count_out   = alert_count;
    *udp_received_out  = stat_udp_received;
    *udp_invalid_out   = stat_udp_invalid;
    *tcp_queries_out   = stat_tcp_queries;
}