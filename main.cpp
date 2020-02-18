#include <stdio.h>
#include <stdlib.h>
#include <cstdint>

#include <time.h>
#include <string.h>

#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/select.h>

#include <list>
#include <chrono>

#pragma pack(push, 1)
typedef struct {
    int8_t sensor;
    int8_t type;
    union {
        uint64_t data;
        double double_data;
    };
} SensorPacket;

typedef struct {
    int8_t sensor;
    int8_t query;
} QueryPacket;
#pragma pack(pop)

typedef enum {
    NONE =              0x0000,
    FIELD_INT8 =        0x0001,
    FIELD_INT16 =       0x0002,
    FIELD_INT32 =       0x0003,
    FIELD_INT64 =       0x0004,
    FIELD_UINT8 =       0x0005,
    FIELD_UINT16 =      0x0006,
    FIELD_UINT32 =      0x0007,
    FIELD_UINT64 =      0x0008,
    FIELD_FLOAT =       0x0009,
    FIELD_DOUBLE =      0x000A,
    FIELD_CHARARRAY =   0x000B,
    FIELD_CHAR =        0x000C,
    FIELD_BOOL =        0x000D,
    FIELD_EMCY =        0x000E // error?
}  DataType;

typedef enum {
    LAST_VALUE   = 0,
    MEAN_LAST_10 = 1,
    MEAN_ALL     = 2,
    COUNT_QUERY_TYPES
}  QueryType;

int create_udp_socket(int16_t port) {
    int socket_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (socket_fd < 0) {
        fprintf(stderr, "Socket (port %hd) creation failed, error code: %d\n", port, socket_fd);
        exit(-1);
    }
    struct sockaddr_in server_address;
    server_address.sin_family = AF_INET;
    server_address.sin_addr.s_addr = INADDR_ANY;
    server_address.sin_port = htons(port);
    int bind_result = bind(socket_fd, (struct sockaddr *) &server_address, sizeof(server_address));
    if (bind_result < 0) {
        fprintf(stderr, "Port %hd binding failed, error code %d\n", port, bind_result);
        exit(-2);
    }
    return socket_fd;
}

int read_socket(int socket_fd, void* buffer, int buffer_length, struct sockaddr *client_addr, socklen_t *client_length) {
    return recvfrom(socket_fd, buffer, buffer_length, MSG_DONTWAIT, client_addr, client_length);
}

typedef struct {
    int8_t type;
    std::list<uint64_t> last_10; // TODO: honestly, this should just be a ring buffer
    int count;
    // NOTE: mean may not give the same value as mean_last_10() even if there have been less than 11 values due to rounding errors
    double mean;
} SensorData;

const int count_sensors = 10;
FILE *logfile;
SensorData sensor_data[count_sensors] = {0};

void log_sensor_packet(SensorPacket *packet) {
    // TODO: std::chrono::system_clock for more precision?
    fprintf(logfile, "%ld,%d,%llu\n", time(NULL), packet->sensor, (long long) packet->data);
    fflush(logfile);
}

void process_sensor(SensorPacket *packet) {
    SensorData *data = &sensor_data[packet->sensor];
    data->count += 1;
    data->last_10.push_back(packet->data);
    data->type = packet->type;

    if (data->last_10.size() > 10) {
        data->last_10.pop_front();
    }

    if (data->count == 1) { // on first reading
        data->mean = packet->data;
    } else {
        double diff = (double)packet->data - (double)data->mean;
        data->mean += diff / (double)data->count;
    }
}

double mean_last_10(SensorData *data) {
    double result = 0;
    if (data->last_10.empty()) {
        return 0;
    }
    for(uint64_t it: data->last_10) {
        result += it;
    }
    return result / data->last_10.size();
}

void build_response(QueryPacket *query, SensorPacket *response) {
    SensorData *data = &sensor_data[query->sensor];
    response->sensor = query->sensor;
    if (data->count < 1) {
        response->type = FIELD_EMCY;
        response->data = 0;
        return;
    }
    switch (query->query) {
        case LAST_VALUE: {
            response->type = data->type;
            response->data = data->last_10.back();
        } break;
        case MEAN_LAST_10: {
            response->type = FIELD_DOUBLE;
            response->double_data = mean_last_10(data);
        } break;
        case MEAN_ALL: {
            response->type = FIELD_DOUBLE;
            response->double_data = data->mean;
        } break;
    }
}

bool valid_packet(SensorPacket *packet, int length) {
    if (length != sizeof(SensorPacket)) return false;
    if (packet->sensor > count_sensors) return false;
    switch (packet->type) {
        case FIELD_INT8: {
            return packet->data <= 0x7F;
        } break;
        case FIELD_INT32: {
            return packet->data <= 0x7FFFFFFFFF;
        } break;
        case FIELD_UINT64: {
            return true;
        } break;
    }
    return false;
}

bool valid_packet(QueryPacket *packet, int length) {
    if (length != sizeof(QueryPacket)) return false;
    if (packet->sensor > count_sensors) return false;
    if (packet->query >= COUNT_QUERY_TYPES) return false;
    return true;
}

int main() {
    int sensors  = create_udp_socket(12345),
        requests = create_udp_socket(12346);

    fd_set ports;
    int highest = (sensors > requests) ? sensors : requests;
    highest += 1;
    timeval timeout = {0};

    int buffer_length = 100;
    uint8_t  buffer[buffer_length] = {};

    logfile = fopen("sensors.csv", "a");

    auto next_data_print_time = std::chrono::steady_clock::now();
    next_data_print_time += std::chrono::seconds(1);

    while (true) {
        FD_ZERO(&ports);
        FD_SET(sensors, &ports);
        FD_SET(requests, &ports);

        auto current_time = std::chrono::steady_clock::now();
        if (current_time > next_data_print_time) {
            next_data_print_time += std::chrono::seconds(1);
            for (int i = 0; i < count_sensors; i++) {
                printf("Sensor %d: %f\n", i, mean_last_10(&sensor_data[i]));
            }
        }
        auto diff = next_data_print_time - current_time;
        auto seconds = std::chrono::duration_cast<std::chrono::seconds>(diff);
        auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(diff) - seconds;

        timeout.tv_sec = seconds.count();
        timeout.tv_usec = microseconds.count();

        select(highest, &ports, NULL, NULL, &timeout);

        struct sockaddr_in client_addr = {0};
        socklen_t client_length = sizeof(client_addr);
        if (FD_ISSET(sensors, &ports)) {
            int length = read_socket(sensors, buffer, buffer_length, (struct sockaddr*) &client_addr, &client_length);
            SensorPacket *packet = (SensorPacket*) buffer;

            if (!valid_packet(packet, length)) {
                fprintf(stderr, "Malformed packet from sensors\n");
            } else {
                log_sensor_packet(packet);
                process_sensor(packet);
            }
        }
        if (FD_ISSET(requests, &ports)) {
            int length = read_socket(requests, buffer, buffer_length, (struct sockaddr*) &client_addr, &client_length);
            QueryPacket *packet = (QueryPacket*) buffer;

            if (!valid_packet(packet, length)) {
                fprintf(stderr, "Malformed data request\n");
            } else {
                printf("type %d\n", packet->query);
                SensorPacket response = {0};
                build_response(packet, &response);
                if (sendto(requests, &response, sizeof(SensorPacket), 0, (struct sockaddr*) &client_addr, client_length) < 0) {
                    fprintf(stderr, "Sending failed, errno: %d\n", errno);
                }
            }
        }
    }
    return 0;
}
