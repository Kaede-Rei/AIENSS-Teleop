from pathlib import Path

import pytest

from dm_arm_teleop.config import load_arm_config


ROOT = Path(__file__).resolve().parents[1]


def test_source_config_values_are_preserved():
    cfg = load_arm_config(ROOT / "config" / "arm.yaml")
    assert cfg.robot.port == "/dev/com-1.3-tty"
    assert cfg.robot.disable_torque_on_disconnect is True
    assert cfg.robot.joint_velocity_scaling == 1.0
    assert cfg.robot.max_gripper_torque == 1.0
    assert cfg.teleop.port == "/dev/com-1.4-tty"
    assert cfg.teleop.gripper_open_pos == 2280
    assert cfg.teleop.gripper_closed_pos == 1670
    assert cfg.teleop.direction == (1, 1, 1, 1, 1, 1)
    assert cfg.teleop.offset == (0.0, 0.0, 1.64, 0.0, 0.0, 0.0)


def test_invalid_direction_rejected(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(
        "robot:\n  port: /dev/follower\nteleop:\n  port: /dev/leader\n  direction: [1, 1, 0, 1, 1, 1]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="direction"):
        load_arm_config(p)
