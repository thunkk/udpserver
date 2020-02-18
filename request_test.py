#!/usr/bin/env python3

import asyncio
import logging
import random
from enum import IntEnum
from ctypes import *
import struct

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


class SensorPacket(Structure):
    _pack_ = True
    _fields_ = [
        ('sensor_id', c_uint8),
        ('type', c_uint8),
        ('value', Value)
    ]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<SensorPacket: sensor_id: {}, type: {}, value: {}".format(
            self.sensor_id,
            ValueType(self.type).name,
            self.value.__getattribute__(ValueType(self.type).name)
        )

    def receiveSome(self, bytes):
        fit = min(len(bytes), sizeof(self))
        memmove(addressof(self), bytes, fit)


class RequestPacket(Structure):
    _pack_ = True
    _fields_ = [
        ('sensor_id', c_uint8),
        ('type', c_uint8),
    ]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<SensorPacket: sensor_id: {}, type: {}".format(
            self.sensor_id,
            self.type
        )


class SensorServer(asyncio.DatagramProtocol):

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
        self.send_sensor_data()

    def send_sensor_data(self):
        for value in range(10):
            value_union = Value()
            value_union.__setattr__(ValueType.FIELD_INT32.name, value)
            packet = SensorPacket(
                sensor_id=1,
                type=ValueType.FIELD_INT32,
                value=value_union
            )
            logger.debug("Sending SensorPacket len %s, data %s", sizeof(packet), packet)
            self.transport.sendto(bytes(packet), ('127.0.0.1', 12345))

    def datagram_received(self, data, addr):
        self.logger.debug("Received %d bytes of data from %s, discarding", len(data), addr)

def types():
    for value in range(3):
        yield value

class RequestServer(asyncio.DatagramProtocol):

    def __init__(self, *, loop=None, logger=None):
        self.loop = loop
        self.logger = logger
        self.transport = None
        self.generator = types()

        if not self.loop:
            self.loop = asyncio.get_event_loop()

        if not self.logger:
            self.logger = logging.getLogger(__name__)

    def connection_made(self, transport):
        """Called when UDP socket is up"""
        self.logger.info("UDP server is now up")
        self.transport = transport
        self.loop.call_later(1, self.send_request)

    def send_request(self):
        try:
            packet = RequestPacket(
                sensor_id=1,
                type=next(self.generator),
            )
            logger.debug("Sending RequestPacket len %s, data %s", sizeof(packet), packet)
            self.transport.sendto(bytes(packet), ('127.0.0.1', 12346))
            self.loop.call_later(1, self.send_request)
        except:
            pass

    def datagram_received(self, data, addr):
        self.logger.debug("Received %d bytes of data from %s, data:", len(data), addr)
        packet = SensorPacket()
        packet.receiveSome(data)
        if packet.type != 10:
            self.logger.debug("Sensor %d, type %d, data %f", packet.sensor_id, packet.type, packet.value.FIELD_UINT64)
        else:
            self.logger.debug("Sensor %d, type %d, data %f", packet.sensor_id, packet.type, packet.value.FIELD_DOUBLE)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    loop = asyncio.get_event_loop()
    logger.info("Starting UDP server")
    listen = loop.create_datagram_endpoint(
        SensorServer, remote_addr=('127.0.0.1', 12345))
    transport, protocol = loop.run_until_complete(listen)

    listen = loop.create_datagram_endpoint(
        RequestServer,
        local_addr=('127.0.0.1', 32453),
        remote_addr=('127.0.0.1', 12346))
    transport, protocol = loop.run_until_complete(listen)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    transport.close()
    loop.close()
