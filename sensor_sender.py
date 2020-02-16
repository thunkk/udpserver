#!/usr/bin/env python3

import asyncio
import logging
import random
from enum import IntEnum
from ctypes import *


NR_SENSORS = 10


class ValueType(IntEnum):
    """
    Value data type identifier
    """
    NONE = 0x0000
    FIELD_INT8 = 0x0001
    FIELD_INT16 = 0x0002
    FIELD_INT32 = 0x0003
    FIELD_INT64 = 0x0004
    FIELD_UINT8 = 0x0005
    FIELD_UINT16 = 0x0006
    FIELD_UINT32 = 0x0007
    FIELD_UINT64 = 0x0008
    FIELD_FLOAT = 0x0009
    FIELD_DOUBLE = 0x000A
    FIELD_CHARARRAY = 0x000B
    FIELD_CHAR = 0x000C
    FIELD_BOOL = 0x000D
    FIELD_EMCY = 0x000E


ValueTypeToCtype = {
    ValueType.FIELD_BOOL: c_bool,
    ValueType.FIELD_INT8: c_int8,
    ValueType.FIELD_INT16: c_int16,
    ValueType.FIELD_INT32: c_int32,
    ValueType.FIELD_INT64: c_int64,
    ValueType.FIELD_UINT8: c_uint8,
    ValueType.FIELD_UINT16: c_uint16,
    ValueType.FIELD_UINT32: c_uint32,
    ValueType.FIELD_UINT64: c_uint64,
    ValueType.FIELD_FLOAT: c_float,
    ValueType.FIELD_DOUBLE: c_double,
    ValueType.FIELD_CHAR: c_char
}

# (value_type, max_value)
limited_selection_of_values_to_send = [
    (ValueType.FIELD_INT8, 2 ** 7  - 1),
    (ValueType.FIELD_INT32, 2 ** 31 - 1),
    (ValueType.FIELD_UINT64, 2 ** 64 - 1)
]


class Value(Union):
    _fields_ = [(value.name, ctype) for value, ctype in ValueTypeToCtype.items()]


class Packet(Structure):
    _pack_ = True
    _fields_ = [
        ('sensor_id', c_uint8),
        ('type', c_uint8),
        ('value', Value)
    ]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<Packet: sensor_id: {}, type: {}, value: {}".format(
            self.sensor_id,
            ValueType(self.type).name,
            self.value.__getattribute__(ValueType(self.type).name)
        )


class Server(asyncio.DatagramProtocol):

    def __init__(self, *, loop=None, logger=None):
        self.loop = loop
        self.logger = logger
        self.transport = None

        if not self.loop:
            self.loop = asyncio.get_event_loop()

        if not self.logger:
            self.logger = logging.getLogger(__name__)

    def connection_made(self, transport):
        """Called when UDP socket is up"""
        self.logger.info("UDP server is now up")
        self.transport = transport
        self.setup_sensor_sending()

    def setup_sensor_sending(self):
        self.logger.info("Starting sensors")
        for x in range(NR_SENSORS):
            interval = random.randint(0, 10)/10
            value_type, max_value = random.choice(limited_selection_of_values_to_send)
            self.loop.call_later(interval, self.send_packet, x, value_type, max_value, interval)

    def datagram_received(self, data, addr):
        self.logger.debug("Received %d bytes of data from %s, discarding", len(data), addr)

    def send_packet(self, sensor_id, value_type, max_value, interval=1):
        if not self.transport:
            self.logger.warning("UDP transport is not up yet, ignoring packet send")
            return

        value = random.randint(0, max_value)

        value_union = Value()
        value_union.__setattr__(value_type.name, value)
        packet = Packet(
            sensor_id=sensor_id,
            type=value_type,
            value=value_union
        )
        logger.debug("Sending packet len %s, data %s", sizeof(packet), packet)
        self.transport.sendto(bytes(packet), ('127.0.0.1', 12345))
        self.loop.call_later(interval, self.send_packet, sensor_id, value_type, max_value)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    loop = asyncio.get_event_loop()
    logger.info("Starting UDP server")
    # One protocol instance will be created to serve all client requests
    listen = loop.create_datagram_endpoint(
        Server, remote_addr=('127.0.0.1', 12345))
    transport, protocol = loop.run_until_complete(listen)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    transport.close()
    loop.close()
