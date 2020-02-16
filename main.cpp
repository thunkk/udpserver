#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <cstdint>

#pragma pack(push, 1)
typedef struct {
    int8_t sensor;
    int8_t type;
    uint64_t data;
} SensorPacket;
#pragma pack(pop)

int create_udp_socket(int16_t port) {
    int socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (socket < 0) {
        fprintf(stderr, "Socket (port %hd) creation failed, error code: %d/d", socket, socket);
        exit(-1);
    }
    struct sockaddr_in server_address;
    server_address.sin_family = AF_INET;
    server_address.sin_addr.s_addr = INADDR_ANY;
    server_address.sin_port = htons(port);
    int bind_result = bind(sockfd, (struct sockaddr *) &server_address, sizeof(server_address));
    if (bind_result < 0) {
        printf("Port %hd binding failed, error code %d\n", socket, bind_result);
        exit(-2);
    }
    return socket;
}

int main(int argc, const char* argv[]) {
    printf("ready\n");
    while (true) {
        struct sockaddr cli_addr;
        socklen_t clilen = 0;
        uint8_t  buffer[100];
        recvfrom(sockfd, &buffer, 100, MSG_WAITALL, &cli_addr, &clilen);
        printf("len: %d\n", clilen);
        SensorPacket *raw = (SensorPacket*) buffer;
        switch (raw->type) {
            case 1: {
                printf("Sensor %d, type %d, data %d\n", raw->sensor, raw->type, (int8_t) raw->data);
            } break;
            case 3: {
                printf("Sensor %d, type %d, data %d\n", raw->sensor, raw->type, (int32_t) raw->data);
            } break;
            case 8: {
                printf("Sensor %d, type %d, data %lu\n", raw->sensor, raw->type, raw->data);
            } break;
            default: {
                printf("Sensor %d, type %d, ERROR\n", raw->sensor, raw->type);
            } break;
        }

        //break;
    }
}
