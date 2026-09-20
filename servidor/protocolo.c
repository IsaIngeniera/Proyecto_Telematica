/*
 * protocolo.c - Implementacion de la capa de protocolo.
 *
 * Solo conoce texto: como separar campos, validar su sintaxis y
 * construir mensajes de error. No sabe nada de nodos, alertas ni
 * sockets.
 */

#include "protocolo.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <time.h>
#include <stdarg.h>

void log_line(const char *fmt, ...) {
    char timebuf[32];
    time_t now = time(NULL);
    struct tm tm_now;
    localtime_r(&now, &tm_now);
    strftime(timebuf, sizeof(timebuf), "%Y-%m-%d %H:%M:%S", &tm_now);

    va_list args;
    va_start(args, fmt);
    printf("[%s] ", timebuf);
    vprintf(fmt, args);
    printf("\n");
    fflush(stdout);
    va_end(args);
}

int is_valid_node_id(const char *id) {
    if (strlen(id) != 6) return 0;
    if (strncmp(id, "NODE", 4) != 0) return 0;
    return isdigit((unsigned char)id[4]) && isdigit((unsigned char)id[5]);
}

int is_valid_variable(const char *v) {
    return strcmp(v, VAR_TEMP) == 0 || strcmp(v, VAR_HUM) == 0 ||
           strcmp(v, VAR_ENERGY) == 0 || strcmp(v, VAR_VIBRATION) == 0;
}

int parse_double(const char *s, double *out) {
    if (!s || !*s) return 0;
    char *end = NULL;
    errno = 0;
    double val = strtod(s, &end);
    if (errno != 0 || end == s || *end != '\0') return 0;
    *out = val;
    return 1;
}

int parse_long(const char *s, long *out) {
    if (!s || !*s) return 0;
    char *end = NULL;
    errno = 0;
    long val = strtol(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0') return 0;
    *out = val;
    return 1;
}

int split_fields(char *line, char *fields[], int max_fields) {
    int n = 0;
    char *tok = strtok(line, FIELD_SEP);
    while (tok != NULL && n < max_fields) {
        fields[n++] = tok;
        tok = strtok(NULL, FIELD_SEP);
    }
    return n;
}

void build_error(char *out, size_t out_size, const char *code, const char *desc) {
    snprintf(out, out_size, "%s%s%s%s%s\n", MSG_ERROR, FIELD_SEP, code, FIELD_SEP, desc);
}