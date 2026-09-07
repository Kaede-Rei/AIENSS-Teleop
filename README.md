# DM-Arm-Standalone-Teleop

独立的单臂主从遥操作仓库：**Dynamixel XL330 主臂 → 达妙 DM 从臂**

本仓库从 `Kaede-Rei/Dual-DM-Arm-LeRobot` 的单臂遥操作路径中抽离，目标是保持原有硬件参数和映射行为，同时彻底移除 LeRobot、ROS、相机、数据集和 GUI 依赖

## 1. 数据流

```text
XL330 Leader (ID 1..7, 115200, Protocol 2.0)
        ↓ Present_Position
raw tick → rad → direction/offset → gripper normalize
        ↓
DM Follower
J1..J6: POS_VEL
Gripper: Torque_Pos
```

运行时依赖只有：

- `numpy`
- `pyserial`
- `PyYAML`
- `dynamixel-sdk`

## 2. 与原仓库保持一致的配置

默认 `config/arm.yaml` 直接保留原 IL-RL 配置：

```yaml
robot:
  port: /dev/com-1.3-tty
  disable_torque_on_disconnect: true
  joint_velocity_scaling: 1.0
  max_gripper_torque: 1.0

teleop:
  port: /dev/com-1.4-tty
  gripper_open_pos: 2280
  gripper_closed_pos: 1670
  direction: [1, 1, 1, 1, 1, 1]
  offset: [0.0, 0.0, 1.64, 0.0, 0.0, 0.0]
```

`cameras` 字段仍可留在 YAML 中用于兼容旧配置，但本仓库完全忽略它

### Leader

- ID 1~4：XL330-M288
- ID 5~7：XL330-M077
- 波特率：115200
- Protocol：2.0
- J1~J6 映射：`raw / 4096 * 2π - π`，再乘 `direction`、加 `offset`
- 默认 J3 偏置：`+1.64 rad`
- 夹爪：2280 → 0.0（开），1670 → 1.0（闭）

主臂正常遥操作初始化仍按原逻辑：全关节失能、Return Delay=0，然后仅夹爪设置 Current-Position Mode、Current Limit=100、使能并回到 `gripper_open_pos`

### Follower

| 关节 | 型号 | Slave ID | Master ID |
|---|---|---:|---:|
| J1 | DM4340 | 0x01 | 0x11 |
| J2 | DM4340 | 0x02 | 0x12 |
| J3 | DM4340 | 0x03 | 0x13 |
| J4 | DM4310 | 0x04 | 0x14 |
| J5 | DM4310 | 0x05 | 0x15 |
| J6 | DM4310 | 0x06 | 0x16 |
| Gripper | DM4310 | 0x07 | 0x17 |

保留的行为：

- J1~J3：`ACC=10`, `DEC=-10`, `KP_APR=200`, `KI_APR=10`
- Gripper：`KP_APR=100`
- J4 限位：±100°
- J5 限位：±90°
- 夹爪归一化 0~1 映射到 `0~-5.23 rad`
- 启动时夹爪按原代码执行力矩阈值 `>1.2` 的自动找零
- 为保持兼容，J1~J6 目前都继续使用原代码的 `joint_velocity_scaling * DM4340_SPEED`

最后一点是原实现的既有行为，即使 J4~J6 实际是 DM4310，本版本也**不擅自修改**；以后若要按电机型号分速度，应作为单独版本变更

## 3. 安装

推荐 Python 3.10~3.12；项目声明 `>=3.10`

```bash
git clone <your-new-repository-url>
cd DM-Arm-Standalone-Teleop

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

也可以：

```bash
pip install -r requirements.txt
pip install -e . --no-deps
```

## 4. 先做只读硬件检查

### 主臂

```bash
python scripts/leader_test.py
```

或：

```bash
python scripts/leader_test.py --leader_port /dev/ttyUSB0
```

这个脚本**只读取** 7 个 Dynamixel 的 `Present_Position`，不会使能扭矩，不会发送目标位置

### 从臂

```bash
python scripts/follower_test.py
```

或：

```bash
python scripts/follower_test.py --follower_port /dev/ttyACM0
```

这个脚本只探测 7 个 DM 电机、读取控制模式和状态，**不会 enable 电机，也不会执行夹爪 homing**

## 5. 单臂遥操作

清空机械臂工作空间后运行：

```bash
python scripts/teleop.py
```

覆盖设备端口：

```bash
python scripts/teleop.py \
  --leader_port /dev/ttyUSB0 \
  --follower_port /dev/ttyACM0
```

覆盖控制频率和从臂速度缩放：

```bash
python scripts/teleop.py \
  --freq 200 \
  --joint_velocity_scaling 0.5
```

> **注意：** 正常 `teleop.py` 会按照原仓库行为初始化 DM 从臂，并执行夹爪自动找零；运行前确保夹爪运动方向无人员、线缆和硬物阻挡

按 `Ctrl-C` 停止；若 `disable_torque_on_disconnect: true`，退出时会尝试失能全部 DM 电机并关闭串口

## 6. 测试

```bash
pip install -e '.[dev]'
pytest -q
python -m compileall -q dm_arm_teleop scripts
```

这些测试不连接真实硬件，验证的是：

- 配置兼容性
- Leader tick→rad、direction、offset
- J3 `+1.64 rad`
- 夹爪归一化
- J4/J5 限位
- 原有统一 DM4340 速度缩放行为
- 夹爪位置/电流换算
- Dynamixel Protocol 2.0 寄存器访问
- 仓库无 LeRobot runtime import/dependency

真实机械臂仍需按“只读检查 → 低速遥操作 → 200 Hz”顺序现场验收

## 7. 仓库结构

```text
DM-Arm-Standalone-Teleop/
├── config/arm.yaml
├── dm_arm_teleop/
│   ├── config.py
│   ├── mapping.py
│   ├── dynamixel_bus.py
│   ├── leader.py
│   ├── follower.py
│   └── dm_control/
│       ├── DM_CAN.py
│       └── LICENSE
├── scripts/
│   ├── teleop.py
│   ├── leader_test.py
│   └── follower_test.py
├── tests/
├── pyproject.toml
├── requirements.txt
├── NOTICE.md
└── LICENSE
```

## 8. 来源与许可证

DM 底层协议实现来源和许可证见 `NOTICE.md` 与 `dm_arm_teleop/dm_control/LICENSE`；本仓库其余新增代码使用根目录 MIT License
