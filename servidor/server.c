/*
 * server.c - Servidor central de la Plataforma Distribuida de Telemetria
 *
 * Responsable: Isa O (rol "Servidor central (C)")
 *
 * Este archivo SOLO se encarga de sockets y del bucle principal:
 *   - Escucha UDP en TELEMETRY_PORT: recibe mediciones de los nodos
 *     y delega el procesamiento a process_telemetry_line() (nodos.c).
 *   - Escucha TCP en OPERATOR_PORT: atiende consultas de operadores
 *     y delega el procesamiento a process_operator_line() (nodos.c).
 *   - Nunca se cae: errores de parseo, clientes que se desconectan
 *     abruptamente o mensajes invalidos solo generan un log/ERROR,
 *     jamas exit()/abort() (salvo al fallar la creacion de los
 *     sockets de escucha al iniciar, que es un error fatal de arranque).
 *
 * La logica de negocio (tabla de nodos, alertas, formato de las
 * respuestas) vive en nodos.c. El parseo/validacion del protocolo de
 * texto vive en protocolo.c. Ver esos archivos para esa parte.
 *
 * Concurrencia: un solo hilo con select() multiplexando:
 *     socket UDP + socket TCP de escucha + N sockets TCP de clientes.
 * Esto evita problemas de sincronizacion sobre la tabla de nodos
 * (no hay dos hilos tocandola al mismo tiempo) y es standard en C
 * para este tipo de servidores.
 *
 * Compilar:  make            (ver Makefile: compila protocolo.c, nodos.c
 *                              y server.c juntos)
 *            o manualmente:
 *            gcc -Wall -Wextra -O2 -o server protocolo.c nodos.c server.c
 * Ejecutar:  ./server [puerto_udp] [puerto_tcp]
 *            (por defecto 5000 UDP, 6000 TCP)
 */

#include "protocolo.h"
#include "nodos.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define DEFAULT_UDP_PORT   5000
#define DEFAULT_TCP_PORT   6000

#define MAX_CLIENTS        32

typedef struct {
    int  fd;
    int  in_use;
    char buf[CLIENT_BUF_SIZE];
    size_t buf_len;
} Client;

static Client clients[MAX_CLIENTS];

static volatile sig_atomic_t keep_running = 1;

static void handle_signal(int sig) {
    (void)sig;
    keep_running = 0;
}

/* ---------------------------------------------------------------- */
/* Sockets                                                            */
/* ---------------------------------------------------------------- */

static int create_udp_socket(int port) {
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) { perror("socket UDP"); exit(1); }

    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons((uint16_t)port);

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind UDP");
        exit(1);
    }
    return fd;
}

static int create_tcp_listen_socket(int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket TCP"); exit(1); }

    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons((uint16_t)port);

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind TCP");
        exit(1);
    }
    if (listen(fd, MAX_CLIENTS) < 0) {
        perror("listen TCP");
        exit(1);
    }
    return fd;
}

static Client *find_free_client_slot(void) {
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (!clients[i].in_use) return &clients[i];
    }
    return NULL;
}

static void close_client(Client *c) {
    if (c->fd >= 0) close(c->fd);
    c->fd = -1;
    c->in_use = 0;
    c->buf_len = 0;
}

/* Procesa todo el buffer de un cliente: puede traer 0, 1 o varias
 * lineas completas (terminadas en '\n'); las procesa todas (delegando
 * en process_operator_line, de nodos.c) y deja en el buffer el resto
 * incompleto para la proxima lectura. */
static int handle_client_data(Client *c) {
    char *start = c->buf;
    char *newline;

    while ((newline = memchr(start, '\n', c->buf_len - (start - c->buf))) != NULL) {
        *newline = '\0';

        /* Quitar '\r' final si viene de un cliente que usa CRLF */
        size_t len = strlen(start);
        if (len > 0 && start[len - 1] == '\r') start[len - 1] = '\0';

        if (strlen(start) == 0) {
            start = newline + 1;
            continue;
        }

        if (strlen(start) > RECV_BUF_SIZE) {
            char response[256];
            build_error(response, sizeof(response), ERR_BAD_REQUEST, ERR_MESSAGE_TOO_LONG);
            if (write(c->fd, response, strlen(response)) < 0) {
                return -1; /* el llamador cierra el socket */
            }
        } else {
            char response[1200];
            process_operator_line(start, response, sizeof(response));
            if (write(c->fd, response, strlen(response)) < 0) {
                return -1;
            }
        }

        start = newline + 1;
    }

    /* Mover lo que sobro (mensaje incompleto) al inicio del buffer */
    size_t remaining = c->buf_len - (start - c->buf);
    memmove(c->buf, start, remaining);
    c->buf_len = remaining;

    if (c->buf_len >= CLIENT_BUF_SIZE - 1) {
        /* Cliente mandando basura sin '\n': cortamos por seguridad */
        char response[256];
        build_error(response, sizeof(response), ERR_BAD_REQUEST, ERR_MESSAGE_TOO_LONG);
        if (write(c->fd, response, strlen(response)) < 0) { /* ignorado a proposito */ }
        c->buf_len = 0;
    }

    return 0;
}

/* ---------------------------------------------------------------- */
/* Main loop                                                          */
/* ---------------------------------------------------------------- */

int main(int argc, char *argv[]) {
    int udp_port = DEFAULT_UDP_PORT;
    int tcp_port = DEFAULT_TCP_PORT;

    if (argc >= 2) udp_port = atoi(argv[1]);
    if (argc >= 3) tcp_port = atoi(argv[2]);

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    signal(SIGPIPE, SIG_IGN); /* si un cliente cierra abrupto, no matar el proceso */

    for (int i = 0; i < MAX_CLIENTS; i++) { clients[i].fd = -1; clients[i].in_use = 0; }

    int udp_fd = create_udp_socket(udp_port);
    int tcp_listen_fd = create_tcp_listen_socket(tcp_port);

    log_line("Servidor iniciado. UDP=%d (telemetria) TCP=%d (operadores)",
             udp_port, tcp_port);

    while (keep_running) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(udp_fd, &read_fds);
        FD_SET(tcp_listen_fd, &read_fds);
        int max_fd = (udp_fd > tcp_listen_fd) ? udp_fd : tcp_listen_fd;

        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (clients[i].in_use) {
                FD_SET(clients[i].fd, &read_fds);
                if (clients[i].fd > max_fd) max_fd = clients[i].fd;
            }
        }

        struct timeval tv = { .tv_sec = 1, .tv_usec = 0 }; /* timeout para poder chequear keep_running */
        int ready = select(max_fd + 1, &read_fds, NULL, NULL, &tv);

        if (ready < 0) {
            if (errno == EINTR) continue; /* senal recibida, seguimos vivos */
            log_line("select() fallo: %s (el servidor continua)", strerror(errno));
            continue;
        }
        if (ready == 0) continue; /* timeout, solo para revisar keep_running */

        /* --- Datos UDP (telemetria) --- */
        if (FD_ISSET(udp_fd, &read_fds)) {
            char buf[RECV_BUF_SIZE + 1];
            struct sockaddr_in from;
            socklen_t from_len = sizeof(from);

            ssize_t r = recvfrom(udp_fd, buf, RECV_BUF_SIZE, 0,
                                  (struct sockaddr *)&from, &from_len);
            if (r > 0) {
                buf[r] = '\0';
                char addr_str[64];
                snprintf(addr_str, sizeof(addr_str), "%s:%d",
                         inet_ntoa(from.sin_addr), ntohs(from.sin_port));

                /* quitar salto de linea final si viene */
                while (r > 0 && (buf[r - 1] == '\n' || buf[r - 1] == '\r')) { buf[--r] = '\0'; }

                process_telemetry_line(buf, addr_str);
            } else if (r < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                log_line("recvfrom UDP fallo: %s (continua)", strerror(errno));
            }
        }

        /* --- Nueva conexion TCP --- */
        if (FD_ISSET(tcp_listen_fd, &read_fds)) {
            struct sockaddr_in client_addr;
            socklen_t client_len = sizeof(client_addr);
            int new_fd = accept(tcp_listen_fd, (struct sockaddr *)&client_addr, &client_len);

            if (new_fd >= 0) {
                Client *slot = find_free_client_slot();
                if (!slot) {
                    log_line("Limite de clientes TCP alcanzado (%d), rechazando conexion",
                              MAX_CLIENTS);
                    close(new_fd);
                } else {
                    slot->fd = new_fd;
                    slot->in_use = 1;
                    slot->buf_len = 0;
                    log_line("Operador conectado desde %s:%d",
                              inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));
                }
            } else if (errno != EAGAIN && errno != EWOULDBLOCK) {
                log_line("accept() fallo: %s (continua)", strerror(errno));
            }
        }

        /* --- Datos de clientes TCP existentes --- */
        for (int i = 0; i < MAX_CLIENTS; i++) {
            Client *c = &clients[i];
            if (!c->in_use || !FD_ISSET(c->fd, &read_fds)) continue;

            ssize_t r = read(c->fd, c->buf + c->buf_len, CLIENT_BUF_SIZE - c->buf_len - 1);

            if (r > 0) {
                c->buf_len += (size_t)r;
                c->buf[c->buf_len] = '\0';
                if (handle_client_data(c) < 0) {
                    log_line("Escritura fallida a operador (fd=%d), cerrando conexion", c->fd);
                    close_client(c);
                }
            } else if (r == 0) {
                log_line("Operador desconectado (fd=%d)", c->fd);
                close_client(c);
            } else {
                if (errno != EAGAIN && errno != EWOULDBLOCK) {
                    log_line("Error leyendo de operador (fd=%d): %s. Cerrando esa conexion.",
                              c->fd, strerror(errno));
                    close_client(c);
                }
            }
        }
    }

    int node_count, alert_count;
    unsigned long udp_received, udp_invalid, tcp_queries;
    nodos_get_stats(&node_count, &alert_count, &udp_received, &udp_invalid, &tcp_queries);

    log_line("Apagando servidor. Nodos=%d Alertas=%d UDP_recibidos=%lu "
              "UDP_invalidos=%lu Consultas_TCP=%lu",
              node_count, alert_count, udp_received, udp_invalid, tcp_queries);

    close(udp_fd);
    close(tcp_listen_fd);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].in_use) close(clients[i].fd);
    }

    return 0;
}