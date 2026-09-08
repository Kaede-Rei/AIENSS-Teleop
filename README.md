# AIENSS-Teleop

**AIENSS-Teleop** 是一个不依赖 LeRobot、ROS、相机或 GUI 的单臂主从遥操作仓库：

```text
Dynamixel XL330 Leader  →  Python standalone teleop  →  DaMiao DM Follower
```

目标不是重新设计控制逻辑，而是把原 `Dual-DM-Arm-LeRobot` 中已经验证过的单臂遥操作路径完整抽离出来，保留原有电机配置、关节映射、夹爪逻辑和限位行为，同时把部署压缩到一个普通 Python 环境中

## 1. 硬件与平台

### 1.1 硬件组成

#### Leader：Dynamixel 示教臂

| 关节 | 电机 | ID |
|---|---|---:|
| J1 | XL330-M288 | 1 |
| J2 | XL330-M288 | 2 |
| J3 | XL330-M288 | 3 |
| J4 | XL330-M288 | 4 |
| J5 | XL330-M077 | 5 |
| J6 | XL330-M077 | 6 |
| Gripper | XL330-M077 | 7 |

Leader 通信参数：

- DYNAMIXEL Protocol 2.0
- 115200 baud
- 读取 `Present_Position`
- 7 个电机同步读取

#### Follower：达妙 DM 六轴臂 + 夹爪

| 关节 | 电机 | Slave ID | Master ID |
|---|---|---:|---:|
| J1 | DM4340 | `0x01` | `0x11` |
| J2 | DM4340 | `0x02` | `0x12` |
| J3 | DM4340 | `0x03` | `0x13` |
| J4 | DM4310 | `0x04` | `0x14` |
| J5 | DM4310 | `0x05` | `0x15` |
| J6 | DM4310 | `0x06` | `0x16` |
| Gripper | DM4310 | `0x07` | `0x17` |

Follower 通过串口连接达妙 USB-CAN/串口控制器，当前代码固定使用 `115200` baud

### 1.2 操作系统支持

| 平台 | 状态 | 说明 |
|---|---|---|
| **Linux / Ubuntu** | **推荐、正式支持** | 当前默认 `/dev/...` 设备路径、`install.sh`、`launch.sh` 和本仓库现有实机使用方式均按 Linux 设计 |
| **Windows Native** | **提供一键安装/启动，尚未完成本仓库实机验收** | 提供 `install.bat` / `launch.bat`；Leader 使用官方 DYNAMIXEL SDK，Follower 使用 `pyserial`，串口配置改为 `COMx` |
| WSL | 不推荐用于当前实机遥操作 | USB/串口透传、权限和设备重连会额外增加排障成本 |
| macOS | 底层 SDK 支持，但本仓库未验收 | 不作为当前部署目标 |

ROBOTIS 官方 DYNAMIXEL SDK 本身支持 Windows、Linux 和 macOS，因此 Python Leader 代码不是 Linux 专属；仓库现在同时提供 Linux Bash 和 Windows Batch 入口；平台差异主要集中在串口设备名、USB 驱动和虚拟环境路径

官方参考：[ROBOTIS DYNAMIXEL SDK Overview](https://emanual.robotis.com/docs/en/software/dynamixel/dynamixel_sdk/overview/)

> 当前建议：实际机械臂部署优先使用原生 Linux；Windows 如需使用，先完成只读连接测试，再做低速遥操作，不要直接把“SDK 支持 Windows”理解为“本仓库已经完成 Windows 实机验证”

### 1.3 软件要求

- Python `>= 3.10`
- `numpy`
- `pyserial`
- `PyYAML`
- `dynamixel-sdk`

不需要：

- LeRobot
- PyTorch
- Hugging Face
- ROS / ROS 2
- OpenCV
- Rerun
- 相机驱动

---

## 2. Quick Start

### 2.1 Linux

#### 安装

在仓库根目录：

```bash
./install.sh
```

脚本会：

1. 检查 Python `>=3.10`
2. 创建 `.venv`
3. 更新 `pip / setuptools / wheel`
4. 安装本项目和全部运行时依赖

如果脚本没有执行权限：

```bash
chmod +x install.sh launch.sh
./install.sh
```

如果系统存在多个 Python，可以显式指定：

```bash
PYTHON_BIN=python3.11 ./install.sh
```

#### 配置串口

安装完成后先修改：

```text
config/arm.yaml
```

最重要的是确认：

```yaml
robot:
  port: /dev/com-1.3-tty

teleop:
  port: /dev/com-1.4-tty
```

这两个 `/dev/com-*` 是当前机器使用的稳定设备名，**不是 Linux 通用固定名称**；换机器后可能是：

```text
/dev/ttyUSB0
/dev/ttyUSB1
/dev/ttyACM0
```

请以实际设备为准

#### 首次建议：先做只读检查

Leader：

```bash
./.venv/bin/python scripts/leader_test.py
```

Follower：

```bash
./.venv/bin/python scripts/follower_test.py
```

两者都正常后再开始遥操作

#### 启动遥操作

```bash
./launch.sh
```

停止：

```text
Ctrl-C
```

`launch.sh` 会固定使用仓库自己的 `.venv`，因此不需要手动执行 `source .venv/bin/activate`


### 2.2 Windows Native

在仓库根目录双击，或在 CMD / PowerShell 中运行：

```bat
install.bat
```

脚本会自动：

1. 优先使用 Windows Python Launcher `py -3`，否则尝试 `python`
2. 检查 Python `>= 3.10`
3. 创建 `.venv`
4. 更新 `pip / setuptools / wheel`
5. 执行 `pip install -e .`

然后修改 `config/arm.yaml` 中的两个串口，例如：

```yaml
robot:
  port: COM3

teleop:
  port: COM4
```

建议首次先做只读检查：

```bat
.venv\Scripts\python.exe scripts\leader_test.py
.venv\Scripts\python.exe scripts\follower_test.py
```

确认两侧硬件读取正常后启动遥操作：

```bat
launch.bat
```

Windows 启动脚本同样会把额外参数全部透传给 `scripts\teleop.py`，例如：

```bat
launch.bat --freq 100 --joint_velocity_scaling 0.3
```

或者临时覆盖端口：

```bat
launch.bat --leader_port COM4 --follower_port COM3
```

停止使用 `Ctrl-C`

> Windows 仍需要先安装 Leader USB 转接器和 Follower DM USB-CAN/串口设备对应的 Windows 驱动；本仓库已提供 Windows 软件入口，但真实机械臂 Windows 端仍建议先只读测试、再低速遥操作

---

## 3. 配置 `config/arm.yaml`

默认配置：

```yaml
robot:
  port: /dev/com-1.3-tty
  disable_torque_on_disconnect: true
  joint_velocity_scaling: 1.0
  max_gripper_torque: 1.0

  cameras:
    end:
      type: opencv
      index_or_path: /dev/com-1.2-video
      width: 640
      height: 480
      fps: 30
    eye:
      type: opencv
      index_or_path: 4
      width: 1280
      height: 720
      fps: 30

teleop:
  port: /dev/com-1.4-tty
  gripper_open_pos: 2280
  gripper_closed_pos: 1670
  direction: [1, 1, 1, 1, 1, 1]
  offset: [0.0, 0.0, 1.64, 0.0, 0.0, 0.0]
```

### 3.1 `robot`：DM Follower

#### `robot.port`

Follower 的串口设备

Linux 示例：

```yaml
port: /dev/ttyUSB0
```

Windows 原生示例：

```yaml
port: COM3
```

#### `disable_torque_on_disconnect`

```yaml
disable_torque_on_disconnect: true
```

为 `true` 时，正常退出遥操作后会尝试失能全部 DM 电机

建议保持：

```yaml
true
```

#### `joint_velocity_scaling`

```yaml
joint_velocity_scaling: 1.0
```

允许范围：

```text
0 < scaling <= 1.0
```

首次调试如果希望降低跟随速度，可以先设置：

```yaml
joint_velocity_scaling: 0.3
```

当前版本为保持原仓库行为，J1~J6 都使用：

```text
joint_velocity_scaling × DM4340_SPEED
```

即使 J4~J6 实际使用 DM4310，也暂时不按型号拆分速度上限

#### `max_gripper_torque`

```yaml
max_gripper_torque: 1.0
```

用于计算 Follower 夹爪 `Torque_Pos` 模式下的目标电流

#### `cameras`

该字段仅为了兼容原 `Dual-DM-Arm-LeRobot` 配置保留

**本仓库不会读取、初始化或显示任何相机**

因此可以保留，也可以从 YAML 中删除整个 `cameras:` 块

### 3.2 `teleop`：Dynamixel Leader

#### `teleop.port`

Leader 的 DYNAMIXEL 串口设备

Linux：

```yaml
port: /dev/ttyUSB1
```

Windows Native：

```yaml
port: COM4
```

#### `gripper_open_pos / gripper_closed_pos`

```yaml
gripper_open_pos: 2280
gripper_closed_pos: 1670
```

这两个值是 Leader 夹爪的 DYNAMIXEL encoder tick

当前映射：

```text
2280 → 0.0 → Follower open
1670 → 1.0 → Follower closed
```

如果更换 Leader 夹爪结构或零点，需要重新测这两个值

#### `direction`

```yaml
direction: [1, 1, 1, 1, 1, 1]
```

对应 J1~J6 的关节方向

允许值只有：

```text
1
-1
```

某个关节方向相反时，例如反转 J2：

```yaml
direction: [1, -1, 1, 1, 1, 1]
```

#### `offset`

```yaml
offset: [0.0, 0.0, 1.64, 0.0, 0.0, 0.0]
```

对应 J1~J6 的弧度偏置

当前原始配置中：

```text
J3 offset = +1.64 rad
```

这是现有 Leader/Follower 对齐的一部分，不建议在没有重新标定的情况下修改

---

## 4. `launch.sh` 与运行参数

最简单：

```bash
./launch.sh
```

`launch.sh` 会把后面的参数全部透传给 `scripts/teleop.py`

### 临时覆盖串口

```bash
./launch.sh \
  --leader_port /dev/ttyUSB1 \
  --follower_port /dev/ttyUSB0
```

这不会修改 `config/arm.yaml`

### 临时降低速度

```bash
./launch.sh --joint_velocity_scaling 0.3
```

### 修改目标循环频率

默认：

```text
200 Hz
```

例如：

```bash
./launch.sh --freq 100
```

完整参数：

```bash
./launch.sh --help
```

---

## 5. 首次硬件检查与安全

### 5.1 Leader 只读检查

```bash
./.venv/bin/python scripts/leader_test.py
```

或者覆盖端口：

```bash
./.venv/bin/python scripts/leader_test.py \
  --leader_port /dev/ttyUSB1
```

该脚本：

- 读取 7 个 Dynamixel 的 `Present_Position`
- 不使能主臂关节扭矩
- 不发送目标位置

### 5.2 Follower 只读检查

```bash
./.venv/bin/python scripts/follower_test.py
```

或者：

```bash
./.venv/bin/python scripts/follower_test.py \
  --follower_port /dev/ttyUSB0
```

该脚本：

- 探测 7 个 DM 电机
- 读取控制模式和状态
- 不 enable 电机
- 不执行夹爪 homing

### 5.3 正式 `teleop.py` 会做什么

运行：

```bash
./launch.sh
```

后，Follower 会按照原仓库行为：

1. 检查 J1~J6 + Gripper
2. 切换到对应控制模式
3. enable DM 电机
4. 写入原控制参数
5. 执行夹爪自动找零
6. 进入 Leader → Follower 实时映射循环

夹爪自动找零逻辑会主动运动夹爪，直到检测到：

```text
torque > 1.2
```

然后停止、失能、设置零位、重新使能并进入 `Torque_Pos`

因此首次启动前必须保证夹爪运动方向没有手指、线缆、工具或硬物阻挡

---

## 6. 控制行为与数据流

```text
XL330 Leader
ID 1..7 / 115200 / Protocol 2.0
        ↓
Present_Position
        ↓
raw tick → rad
        ↓
direction + offset
        ↓
gripper normalize 0..1
        ↓
DM Follower
J1..J6: POS_VEL
Gripper: Torque_Pos
```

### Leader 映射

J1~J6：

```text
rad = raw / 4096 × 2π - π
rad = rad × direction[i] + offset[i]
```

默认：

```text
J3 += 1.64 rad
```

Gripper：

```text
open tick   = 2280 → 0.0
closed tick = 1670 → 1.0
```

### Follower 限位

当前保留原实现：

```text
J4: -100° ~ +100°
J5:  -90° ~  +90°
```

夹爪：

```text
Leader 0..1
     ↓
Follower 0 .. -5.23 rad
```

### Follower 原始控制参数

J1~J3：

```text
ACC    = 10
DEC    = -10
KP_APR = 200
KI_APR = 10
```

Gripper：

```text
KP_APR = 100
```

---

## 7. 开发与测试

安装开发依赖：

```bash
./.venv/bin/python -m pip install -e '.[dev]'
```

运行测试：

```bash
./.venv/bin/python -m pytest -q
```

语法检查：

```bash
./.venv/bin/python -m compileall -q dm_arm_teleop scripts
bash -n install.sh
bash -n launch.sh
```

软件测试覆盖：

- 配置加载与覆盖
- Leader tick → rad
- direction / offset
- J3 `+1.64 rad`
- Gripper 归一化
- J4/J5 限位
- 统一 DM4340 速度缩放兼容行为
- Gripper 位置和电流换算
- DYNAMIXEL Protocol 2.0 寄存器访问
- Leader 配置顺序
- 仓库无 LeRobot runtime import/dependency
- Bash 启动入口存在且语法正确

---

## 8. 仓库结构

```text
AIENSS-Teleop/
├── install.sh
├── launch.sh
├── config/
│   └── arm.yaml
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

---

## 9. 仓库历史

本仓库的单臂遥操作逻辑最初来自：

```text
Kaede-Rei/Dual-DM-Arm-LeRobot
```

原实现面向 LeRobot 集成，将：

- DM Follower
- Dynamixel Leader
- LeRobot `Robot`
- LeRobot `Teleoperator`
- Camera config
- `lerobot-teleoperate`
- Rerun GUI

放在同一个框架中

对于单纯的机械臂主从遥操作，这会引入大量与实际运动控制无关的依赖

因此 AIENSS-Teleop 将其中已经使用过的单臂链路独立出来：

```text
原来：
Leader → LeRobot Teleoperator → LeRobot teleop runtime → Robot → DM

现在：
Leader → standalone Python → DM
```

独立过程中刻意保持以下行为不变：

- Leader 7 个 XL330 ID 与型号
- Protocol 2.0 / 115200
- J3 `+1.64 rad`
- `direction / offset`
- Gripper 2280 / 1670
- DM 电机 ID 与类型
- J4/J5 限位
- Gripper 自动找零
- Gripper Torque-Position
- J1~J6 共用原 `DM4340_SPEED` 的兼容行为

也就是说，该仓库的目标是**去框架依赖，而不是借机改变机械臂控制表现**

后续如果需要连接 LeRobot、Isaac Sim、ROS 2 或 SerialArm-Core，建议把本仓库继续视为最低层的硬件遥操作 baseline，而不是再次把底层通信绑定回某个上层框架

---

## 10. Windows Native 补充说明

Windows 已提供：

```text
install.bat
launch.bat
```

常规使用直接参考前面的 **2.2 Windows Native**；如果需要绕过批处理脚本，也可以直接使用：

```bat
.venv\Scripts\python.exe scripts\teleop.py
```

需要额外确认：

- Leader USB 转接器的 Windows 驱动
- Follower DM USB-CAN/串口设备的 Windows 驱动
- `COM3` / `COM4` 等端口是否与实际设备对应
- 目标 Windows 机器上 200 Hz 遥操作循环的实际稳定性


## 11. 来源与许可证

DM 底层协议实现来源和许可证见：

```text
NOTICE.md
dm_arm_teleop/dm_control/LICENSE
```

本仓库其余新增代码使用根目录 `MIT License`
