import math

import pytest

from dm_arm_teleop.config import FollowerConfig
from dm_arm_teleop.follower import DMFollower


class FakeControl:
    def __init__(self):
        self.pos_vel = []
        self.pos_force = []
        self.refreshed = []

    def refresh_motor_status(self, motor):
        self.refreshed.append(motor.SlaveID)

    def control_Pos_Vel(self, motor, position, velocity):
        self.pos_vel.append((motor.SlaveID, position, velocity))

    def control_pos_force(self, motor, position, velocity, i_des):
        self.pos_force.append((motor.SlaveID, position, velocity, i_des))


def make_follower():
    follower = DMFollower(
        FollowerConfig(
            port="/dev/fake",
            disable_torque_on_disconnect=True,
            joint_velocity_scaling=0.5,
            max_gripper_torque=1.0,
        )
    )
    follower.control = FakeControl()
    follower.bus_connected = True
    return follower


def test_send_action_preserves_joint_limits_and_original_shared_velocity_scale():
    follower = make_follower()
    action = {f"joint_{i}.pos": 0.1 * i for i in range(1, 7)}
    action["joint_4.pos"] = 99.0
    action["joint_5.pos"] = -99.0
    action["gripper.pos"] = 0.5

    sent = follower.send_action(action)

    calls = {slave_id: (pos, vel) for slave_id, pos, vel in follower.control.pos_vel}
    assert calls[0x04][0] == pytest.approx(math.radians(100))
    assert calls[0x05][0] == pytest.approx(math.radians(-90))
    expected_velocity = 0.5 * follower.DM4340_SPEED
    assert len(calls) == 6
    assert all(vel == pytest.approx(expected_velocity) for _, vel in calls.values())
    assert sent["joint_4.pos"] == pytest.approx(math.radians(100))
    assert sent["joint_5.pos"] == pytest.approx(math.radians(-90))


def test_gripper_mapping_and_force_command_match_original():
    follower = make_follower()
    action = {f"joint_{i}.pos": 0.0 for i in range(1, 7)}
    action["gripper.pos"] = 0.5

    follower.send_action(action)

    slave_id, pos, vel, current = follower.control.pos_force[0]
    assert slave_id == 0x07
    assert pos == pytest.approx(-5.23 / 2)
    assert vel == pytest.approx(follower.DM4310_SPEED * follower.EMIT_VELOCITY_SCALE)
    assert current == pytest.approx(1.0 / follower.DM4310_TORQUE_CONSTANT * follower.EMIT_CURRENT_SCALE)
