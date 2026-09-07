from __future__ import annotations

from typing import Any


PROTOCOL_VERSION = 2.0
BAUDRATE = 115_200
MOTOR_IDS = tuple(range(1, 8))

ADDR_RETURN_DELAY_TIME = 9
ADDR_OPERATING_MODE = 11
ADDR_CURRENT_LIMIT = 38
ADDR_TORQUE_ENABLE = 64
ADDR_GOAL_POSITION = 116
ADDR_PRESENT_POSITION = 132
LEN_PRESENT_POSITION = 4


class DynamixelBus:
    """Thin Protocol 2.0 wrapper for the seven-motor XL330 leader arm."""

    def __init__(self, port: str, *, sdk_module: Any | None = None):
        self.port = port
        self._sdk = sdk_module
        self.port_handler = None
        self.packet_handler = None
        self.sync_reader = None
        self._opened = False

    @property
    def is_open(self) -> bool:
        return self._opened

    def _load_sdk(self):
        if self._sdk is None:
            try:
                import dynamixel_sdk as sdk
            except ImportError as exc:
                raise RuntimeError(
                    "dynamixel-sdk is required for leader hardware access; install project dependencies first"
                ) from exc
            self._sdk = sdk
        return self._sdk

    def open(self) -> None:
        if self._opened:
            return
        sdk = self._load_sdk()
        self.port_handler = sdk.PortHandler(self.port)
        self.packet_handler = sdk.PacketHandler(PROTOCOL_VERSION)
        if not self.port_handler.openPort():
            raise ConnectionError(f"Failed to open Dynamixel port: {self.port}")
        if not self.port_handler.setBaudRate(BAUDRATE):
            self.port_handler.closePort()
            raise ConnectionError(f"Failed to set Dynamixel baudrate {BAUDRATE} on {self.port}")

        self.sync_reader = sdk.GroupSyncRead(
            self.port_handler,
            self.packet_handler,
            ADDR_PRESENT_POSITION,
            LEN_PRESENT_POSITION,
        )
        for motor_id in MOTOR_IDS:
            if not self.sync_reader.addParam(motor_id):
                self.port_handler.closePort()
                raise RuntimeError(f"Failed to add Dynamixel ID {motor_id} to sync read")
        self._opened = True

    def close(self) -> None:
        if self.port_handler is not None and self._opened:
            self.port_handler.closePort()
        self._opened = False

    def _check_result(self, comm_result: int, packet_error: int, *, context: str) -> None:
        sdk = self._load_sdk()
        if comm_result != sdk.COMM_SUCCESS:
            detail = self.packet_handler.getTxRxResult(comm_result)
            raise ConnectionError(f"{context}: {detail}")
        if packet_error != 0:
            detail = self.packet_handler.getRxPacketError(packet_error)
            raise RuntimeError(f"{context}: {detail}")

    def write_register(self, motor_id: int, address: int, length: int, value: int) -> None:
        if not self._opened or self.packet_handler is None or self.port_handler is None:
            raise RuntimeError("Dynamixel bus is not open")
        if length == 1:
            comm, err = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, address, int(value) & 0xFF
            )
        elif length == 2:
            comm, err = self.packet_handler.write2ByteTxRx(
                self.port_handler, motor_id, address, int(value) & 0xFFFF
            )
        elif length == 4:
            comm, err = self.packet_handler.write4ByteTxRx(
                self.port_handler, motor_id, address, int(value) & 0xFFFFFFFF
            )
        else:
            raise ValueError(f"Unsupported Dynamixel register width: {length}")
        self._check_result(comm, err, context=f"write id={motor_id} addr={address}")

    def read_positions(self) -> dict[int, int]:
        if not self._opened or self.sync_reader is None:
            raise RuntimeError("Dynamixel bus is not open")
        comm_result = self.sync_reader.txRxPacket()
        sdk = self._load_sdk()
        if comm_result != sdk.COMM_SUCCESS:
            detail = self.packet_handler.getTxRxResult(comm_result)
            raise ConnectionError(f"Dynamixel sync read failed: {detail}")

        values: dict[int, int] = {}
        for motor_id in MOTOR_IDS:
            if not self.sync_reader.isAvailable(
                motor_id, ADDR_PRESENT_POSITION, LEN_PRESENT_POSITION
            ):
                raise ConnectionError(f"No Present_Position available for Dynamixel ID {motor_id}")
            raw = int(
                self.sync_reader.getData(
                    motor_id, ADDR_PRESENT_POSITION, LEN_PRESENT_POSITION
                )
            )
            # LeRobot decodes Present_Position as signed two's complement.
            if raw >= 1 << 31:
                raw -= 1 << 32
            values[motor_id] = raw
        return values
