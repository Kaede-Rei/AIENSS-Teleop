# Standalone DM Arm Teleoperation Design

## Goal

Extract the single-arm leader/follower teleoperation path from `Kaede-Rei/Dual-DM-Arm-LeRobot` into a standalone Python repository with no runtime dependency on LeRobot, ROS, cameras, datasets, or GUI tooling.

## Compatibility baseline

The standalone implementation must preserve the behavior of the IL-RL branch reviewed on 2026-09-07:

- Leader: 7 ROBOTIS XL330 motors at IDs 1..7, Protocol 2.0, 115200 baud.
- Leader joint models: IDs 1..4 use XL330-M288; IDs 5..7 use XL330-M077.
- Leader mapping: raw joint tick `v` -> `v / 4096 * 2*pi - pi`, then `direction[i]` and `offset[i]`.
- Default leader direction: `[1, 1, 1, 1, 1, 1]`.
- Default leader offset: `[0, 0, 1.64, 0, 0, 0]` radians.
- Leader gripper normalization: configured open/closed raw ticks map to 0.0/1.0 respectively.
- Leader configuration writes Return Delay Time = 0 for all motors; all torques are disabled, then gripper is configured in current-position mode, Current Limit = 100, torque enabled, and commanded to `gripper_open_pos`.
- Follower: DM4340 on J1..J3, DM4310 on J4..J6 + gripper with the original CAN/master IDs.
- Follower joint control mode: POS_VEL.
- J1..J3 parameters: ACC=10, DEC=-10, KP_APR=200, KI_APR=10.
- Gripper KP_APR=100.
- Follower gripper homing: VEL mode, velocity 10, stop when measured torque > 1.2, disable, zero, re-enable, then Torque_Pos mode.
- Follower gripper physical mapping: 0.0(open normalized) -> 0.0 rad; 1.0(closed normalized) -> -5.23 rad.
- Follower limits: J4 ±100 degrees; J5 ±90 degrees.
- Preserve current velocity behavior: every non-gripper joint uses `joint_velocity_scaling * DM4340_SPEED`, including J4..J6.
- Follower gripper force command uses the original DM4310 constants and current conversion.
- Default teleop loop target remains 200 Hz and keeps the simple `read -> send -> sleep(period)` flow.

## Architecture

The repository has four small runtime units:

1. `config.py`: standalone YAML loading and validated dataclasses.
2. `mapping.py`: pure leader/gripper mapping functions for deterministic tests.
3. `dynamixel_bus.py` + `leader.py`: direct `dynamixel-sdk` Protocol 2.0 communication for the leader.
4. `follower.py` + vendored `dm_control/DM_CAN.py`: original DM protocol implementation and follower behavior.

`scripts/teleop.py` is the only live control loop. `leader_test.py` and `follower_test.py` are read-only diagnostics and intentionally avoid the normal actuator configuration/homing path.

## Dependencies

Runtime dependencies are limited to:

- numpy >= 2.0.1
- pyserial >= 3.5
- PyYAML >= 6.0
- dynamixel-sdk >= 3.7.31

No `lerobot` import is allowed anywhere in runtime or scripts.

## Safety and error handling

- Leader read-only diagnostic does not enable torque or command positions.
- Follower read-only diagnostic does not enable motors and does not home the gripper.
- The normal teleop command preserves the original follower homing behavior, so users must clear the workspace before running it.
- Connection and packet errors raise exceptions with motor/register context.
- Ctrl-C always attempts to disconnect both devices; follower torque is disabled on disconnect when configured.

## Verification

Software verification must cover:

- YAML defaults/overrides and validation.
- Joint raw-tick mapping, including J3 +1.64 rad.
- Gripper normalization.
- J4/J5 clipping and preserved all-joint DM4340 velocity scaling.
- Gripper force mapping/current conversion.
- No `lerobot` import in the repository.
- Python syntax/import checks using installed test dependencies or test-time fakes for unavailable hardware SDKs.

Real hardware communication cannot be certified in the sandbox and must be validated on the target machine using the provided diagnostics before running teleoperation.
