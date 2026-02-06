# Doubao Speech-to-Text for Home Assistant

豆包语音识别 Home Assistant 集成插件，基于 [doubaoime-asr](https://github.com/starccy/doubaoime-asr) 开发。


## 功能特性

- ✅ 完全兼容 Home Assistant STT 组件规范
- ✅ UI 配置界面，无需手动编辑配置文件
- ✅ 自动设备注册和凭据管理
- ✅ 支持中文语音识别（zh-CN, zh）
- ✅ 实时流式识别
- ✅ 自动标点符号添加
- ✅ 保留原有设备伪装功能

## 系统要求

- Home Assistant 2024.1+
- Python 3.11+


## 安装方法

### 方法 1: 手动安装

1. 将整个 `custom_components/hass_stt_doubao` 目录复制到 Home Assistant 配置目录的 `custom_components` 文件夹下：

2. 重启 Home Assistant

### 方法 2: HACS 安装（推荐）

1. 确保你已经在 Home Assistant 中安装并配置了 HACS（Home Assistant Community Store）。
2. 点击 HACS 界面左上角的菜单，选择 自定义仓库（Custom repositories），在弹出的窗口中输入仓库地址 https://github.com/xyzmos/hass_stt_doubao，类别选择 集成，然后点击 添加。之后再搜索 "Doubao STT" 并安装。
3. 重启 Home Assistant

## 配置

### 通过 UI 配置（推荐）

1. 进入 Home Assistant 设置 → 设备与服务
2. 点击右下角 "添加集成"
3. 搜索 "Doubao Speech to Text"
4. 按照向导完成配置：
   - **凭据文件路径**：默认 `doubao_credentials.json`（相对于 HA 配置目录）
   - **启用标点符号**：默认启用

### 配置说明

- **凭据文件路径**：首次运行时会自动注册虚拟设备并保存凭据到此文件，避免重复注册
- **启用标点符号**：是否在识别结果中自动添加标点符号

## 使用示例

### 在 Assist 中使用

配置完成后，Doubao STT 会自动出现在 Assist 管道配置中：

1. 进入设置 → Assist → 管道
2. 选择或创建一个管道
3. 在 "语音转文字" 选项中选择 "Doubao STT"
4. 保存配置

### 在自动化中使用

```yaml
automation:
  - alias: "语音控制示例"
    trigger:
      - platform: event
        event_type: voice_command
    action:
      - service: stt.process
        data:
          entity_id: stt.doubao_stt
          language: zh-CN
```

## 技术架构

```
Home Assistant Audio Stream (PCM 16kHz Mono)
           ↓
    DoubaoSTTEntity
           ↓
    Audio Encoder (PCM → Opus)
           ↓
    DoubaoASR WebSocket Client
           ↓
    Doubao ASR Service
           ↓
    Recognition Result (Text)
```

## 目录结构

```
custom_components/hass_stt_doubao/
├── __init__.py              # 集成初始化
├── manifest.json            # 集成元数据
├── const.py                 # 常量定义
├── config_flow.py           # 配置流
├── stt.py                   # STT 实体实现
├── strings.json             # UI 字符串
├── translations/
│   └── zh.json             # 中文翻译
└── doubaoime_asr/          # doubaoime-asr 核心模块
    ├── __init__.py
    ├── asr.py
    ├── audio.py
    ├── config.py
    ├── constants.py
    ├── device.py
    └── asr_pb2.py
```

## 故障排除

### 无法连接到 Doubao 服务

1. 检查网络连接
2. 确认系统已安装 libopus0
3. 查看 Home Assistant 日志：`设置 → 系统 → 日志`

### 识别结果为空

1. 确保音频格式正确（PCM 16kHz Mono）
2. 检查麦克风是否正常工作
3. 尝试重新配置集成

### 凭据失效

1. 删除凭据文件（默认在配置目录下的 `doubao_credentials.json`）
2. 重新配置集成，会自动重新注册设备

## 免责声明

本项目基于 [doubaoime-asr](https://github.com/starccy/doubaoime-asr) - 核心 ASR 的实现，**非官方提供的 API**。

- 本项目仅供学习和研究目的
- 不保证未来的可用性和稳定性
- 服务端协议可能随时变更导致功能失效

## 许可证

MIT License

## 致谢

- [doubaoime-asr](https://github.com/starccy/doubaoime-asr) - 核心 ASR 实现
- [Home Assistant](https://www.home-assistant.io/) - 智能家居平台

## 更新日志

### v1.0.0 (2026-02-05)
- 初始版本
- 完整的 STT 组件实现
- UI 配置支持
- 自动设备注册
- 中文语音识别
