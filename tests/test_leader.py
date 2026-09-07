import pytest

from dm_arm_teleop.config import LeaderConfig
from dm_arm_teleop.leader import DMLeader


class FakeBus:
    def __init__(self):
        self.opened = False
        self.closed = False
        self.writes = []
        self.positions = {
            1: 2048,
            2: 1024,
            3: 2048,
            4: 3072,
            5: 2048,
            6: 2048,
            7: 2280,
        }

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def write_register(self, motor_id, address, length, value):
        self.writes.append((motor_id, address, length, value))

    def read_positions(self):
        return dict(self.positions)


def make_config():
    return LeaderConfig(
        port="/dev/fake",
        gripper_open_pos=2280,
        gripper_closed_pos=1670,
        direction=(1, 1, 1, 1, 1, 1),
        offset=(0.0, 0.0, 1.64, 0.0, 0.0, 0.0),
    )


def test_leader_configuration_matches_original_lerobot_sequence_values():
    bus = FakeBus()
    leader = DMLeader(make_config(), bus=bus)
    leader.connect()

    torque_disable = (64, 1, 0)
    assert bus.writes[:7] == [(motor_id, *torque_disable) for motor_id in range(1, 8)]
    assert bus.writes[7:14] == [(motor_id, 9, 1, 0) for motor_id in range(1, 8)]
    assert bus.writes[14:] == [
        (7, 64, 1, 0),
        (7, 11, 1, 5),
        (7, 38, 2, 100),
        (7, 64, 1, 1),
        (7, 116, 4, 2280),
    ]


def test_leader_read_action_matches_original_mapping():
    bus = FakeBus()
    leader = DMLeader(make_config(), bus=bus)
    leader.connect()
    action = leader.read_action()
    assert action["joint_1.pos"] == pytest.approx(0.0)
    assert action["joint_2.pos"] == pytest.approx(-pytest.approx(0).expected if False else -1.5707963267948966)
    assert action["joint_3.pos"] == pytest.approx(1.64)
    assert action["gripper.pos"] == pytest.approx(0.0)
