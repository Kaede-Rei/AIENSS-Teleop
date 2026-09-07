import math

import pytest

from dm_arm_teleop.mapping import leader_ticks_to_action, normalize_gripper


def test_joint_ticks_match_original_lerobot_formula_and_offset():
    raw = {
        "joint_1": 2048,
        "joint_2": 1024,
        "joint_3": 2048,
        "joint_4": 3072,
        "joint_5": 2048,
        "joint_6": 2048,
        "gripper": 2280,
    }
    action = leader_ticks_to_action(
        raw,
        direction=(1, 1, 1, 1, 1, 1),
        offset=(0.0, 0.0, 1.64, 0.0, 0.0, 0.0),
        gripper_open_pos=2280,
        gripper_closed_pos=1670,
    )
    assert action["joint_1.pos"] == pytest.approx(0.0)
    assert action["joint_2.pos"] == pytest.approx(-math.pi / 2)
    assert action["joint_3.pos"] == pytest.approx(1.64)
    assert action["joint_4.pos"] == pytest.approx(math.pi / 2)
    assert action["gripper.pos"] == pytest.approx(0.0)


def test_gripper_normalization_matches_original_direction():
    assert normalize_gripper(2280, 2280, 1670) == pytest.approx(0.0)
    assert normalize_gripper(1670, 2280, 1670) == pytest.approx(1.0)
    assert normalize_gripper((2280 + 1670) / 2, 2280, 1670) == pytest.approx(0.5)
