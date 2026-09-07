from types import SimpleNamespace

import pytest

from dm_arm_teleop.dynamixel_bus import DynamixelBus


class FakePortHandler:
    def __init__(self, port):
        self.port = port
        self.opened = False
        self.baudrate = None

    def openPort(self):
        self.opened = True
        return True

    def setBaudRate(self, baudrate):
        self.baudrate = baudrate
        return True

    def closePort(self):
        self.opened = False


class FakePacketHandler:
    def __init__(self, protocol):
        self.protocol = protocol
        self.writes = []

    def write1ByteTxRx(self, port, motor_id, address, value):
        self.writes.append((1, motor_id, address, value))
        return 0, 0

    def write2ByteTxRx(self, port, motor_id, address, value):
        self.writes.append((2, motor_id, address, value))
        return 0, 0

    def write4ByteTxRx(self, port, motor_id, address, value):
        self.writes.append((4, motor_id, address, value))
        return 0, 0

    def getTxRxResult(self, code):
        return f"comm={code}"

    def getRxPacketError(self, code):
        return f"packet={code}"


class FakeGroupSyncRead:
    values = {1: 2048, 2: 1024, 3: 2048, 4: 3072, 5: 2048, 6: 2048, 7: 2280}

    def __init__(self, port, packet, address, length):
        self.address = address
        self.length = length
        self.ids = []

    def addParam(self, motor_id):
        self.ids.append(motor_id)
        return True

    def txRxPacket(self):
        return 0

    def isAvailable(self, motor_id, address, length):
        return motor_id in self.values and address == self.address and length == self.length

    def getData(self, motor_id, address, length):
        return self.values[motor_id]


class FakeSDK:
    COMM_SUCCESS = 0
    PortHandler = FakePortHandler
    PacketHandler = FakePacketHandler
    GroupSyncRead = FakeGroupSyncRead


def test_bus_uses_protocol_2_and_115200_and_sync_reads_seven_ids():
    bus = DynamixelBus("/dev/fake", sdk_module=FakeSDK)
    bus.open()
    assert bus.packet_handler.protocol == 2.0
    assert bus.port_handler.baudrate == 115200
    assert bus.sync_reader.address == 132
    assert bus.sync_reader.length == 4
    assert bus.sync_reader.ids == [1, 2, 3, 4, 5, 6, 7]
    assert bus.read_positions()[7] == 2280


def test_register_write_uses_control_table_widths():
    bus = DynamixelBus("/dev/fake", sdk_module=FakeSDK)
    bus.open()
    bus.write_register(7, 11, 1, 5)
    bus.write_register(7, 38, 2, 100)
    bus.write_register(7, 116, 4, 2280)
    assert bus.packet_handler.writes == [
        (1, 7, 11, 5),
        (2, 7, 38, 100),
        (4, 7, 116, 2280),
    ]
