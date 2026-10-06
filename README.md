# Doubao Speech-to-Text for Home Assistant

[![HACS 自定义仓库](https://img.shields.io/badge/HACS-自定义集成-orange.svg)](https://github.com/hacs/integration)
[![hacs 校验](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/validate.yml/badge.svg)](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/validate.yml)
[![release](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/release.yaml/badge.svg)](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/release.yaml)

豆包语音识别 Home Assistant 集成插件，基于 [doubaoime-asr](https://github.com/starccy/doubaoime-asr) 开发。

## 功能特性

- ✅ 完全兼容 Home Assistant STT 组件规范
- ✅ UI 配置界面（Config Flow），无需手动编辑配置文件
- ✅ 选项修改后自动重载生效（Options Flow）
- ✅ 自动设备注册和凭据管理
- ✅ 支持中文语音识别（zh-CN, zh）
- ✅ 实时流式识别
- ✅ 自动标点符号添加
- ✅ 保留原有设备伪装功能

## 系统要求

- Home Assistant 2024.11+
- Python 3.12+
- 系统库 `libopus`（HAOS / 官方容器镜像已内置；其他安装方式请自行安装 `libopus0` 或 `libopus`）

## 安装方法

### 方法 1: HACS 安装（推荐）

[![通过 HACS 添加此仓库](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=xyzmos&repository=hass_stt_doubao&category=integration)

1. 确保已在 Home Assistant 中安装 HACS
2. 点击上方按钮，或进入 HACS → 右上角菜单 → **自定义仓库**，添加 `https://github.com/xyzmos/hass_stt_doubao`，类别选择 **集成**
3. 搜索 "Doubao Speech to Text" 并下载
4. 重启 Home Assistant

### 方法 2: 手动安装

1. 将 `custom_components/hass_stt_doubao` 目录复制到 Home Assistant 配置目录的 `custom_components` 文件夹下
2. 重启 Home Assistant

## 配置

1. 进入 Home Assistant **设置 → 设备与服务**
2. 点击右下角 **添加集成**，搜索 "Doubao Speech to Text"
3. 按照向导完成配置：
   - **凭据文件路径**：默认 `doubao_credentials.json`（相对于 HA 配置目录，绝对路径亦可）
   - **启用标点符号**：默认启用

说明：

- 集成为单实例（`single_config_entry`），只能添加一个配置项
- 凭据文件在首次识别时自动创建，用于缓存设备注册信息，避免重复注册
- 修改选项后集成自动重载，无需手动重启

## 使用方法

配置完成后，在 **设置 → 语音助手（Assist）→ 管道** 中将「语音转文字」选择为 `stt.doubao_stt` 即可。

STT 实体供 Assist 语音管道调用，没有面向用户的服务动作，也不需要在自动化中直接调用。

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
├── __init__.py              # 集成初始化（entry.runtime_data）
├── manifest.json            # 集成元数据
├── const.py                 # 常量定义
├── config_flow.py           # 配置流 / 选项流
├── stt.py                   # STT 实体实现
├── strings.json             # UI 字符串（英文源）
├── translations/
│   ├── en.json              # 英文翻译
│   └── zh-Hans.json         # 简体中文翻译
├── brand/
│   └── icon.png             # 品牌图标（HACS 展示用）
├── requirements.txt         # 依赖清单（与 manifest 保持一致）
└── doubaoime_asr/           # doubaoime-asr 核心模块
    ├── __init__.py
    ├── asr.py
    ├── audio.py
    ├── client.py
    ├── config.py
    ├── constants.py
    ├── credential.py
    ├── device.py
    ├── models.py
    ├── ner.py
    ├── parser.py
    ├── protocol.py
    ├── sami.py
    ├── wave_client.py
    └── asr_pb2.py
```

## 故障排除

### 无法识别 / 连接失败

1. 检查网络连接
2. 确认系统已安装 `libopus`（官方镜像内置）
3. 查看 Home Assistant 日志：**设置 → 系统 → 日志**

### 识别结果为空

1. 确保音频格式正确（PCM 16kHz Mono）
2. 检查麦克风是否正常工作
3. 尝试重新配置集成

### 凭据失效

1. 删除凭据文件（默认在配置目录下的 `doubao_credentials.json`）
2. 下次识别时会自动重新注册设备

## 免责声明

本项目基于 [doubaoime-asr](https://github.com/starccy/doubaoime-asr) - 核心 ASR 的实现，**非官方提供的 API**。

- 本项目仅供学习和研究目的
- 不保证未来的可用性和稳定性
- 服务端协议可能随时变更导致功能失效

## 发布新版本

仓库配置了 tag 自动发布流程（`.github/workflows/release.yaml`）：

1. 更新 `manifest.json` 中的 `version` 字段及本文件的更新日志
2. 提交后打 tag 推送：`git tag v1.1.0 && git push origin v1.1.0`
3. CI 会自动校验 tag 与 manifest 版本一致并创建 GitHub Release，HACS 即以该版本向用户推送更新

## 问题反馈

[HomeAssistant 豆包输入法 STT 语音识别插件反馈](https://bbs.nextrt.com/d/3-homeassistant-dou-bao-shu-ru-fa-stt-yu-yin-shi-bie-cha-jian)

## 许可证

MIT License

## 致谢

- [doubaoime-asr](https://github.com/starccy/doubaoime-asr) - 核心 ASR 实现
- [Home Assistant](https://www.home-assistant.io/) - 智能家居平台

## 更新日志

### v1.2.0

- 按 hassfest 规范重排 `manifest.json`，新增 `integration_type`、`single_config_entry`
- 集成数据改用 `entry.runtime_data`，选项修改后自动重载生效
- STT 实体接入设备注册表（`DeviceInfo` + `has_entity_name`）
- 凭据文件校验移入执行器，消除事件循环中的阻塞文件 I/O
- 修正选项流：选项只写入 `entry.options`，不再冗余写入 `entry.data`
- 翻译文件规范化：`zh.json` → `zh-Hans.json`，新增 `en.json` 及字段说明
- 修正 `hacs.json` 非法字段，声明最低 HA 版本 `2024.11.0`，新增品牌图标
- WebSocket 会话结束时正确取消收发任务，避免协程泄漏

### v1.0.0

- 初始版本
- 完整的 STT 组件实现
- UI 配置支持
- 自动设备注册
- 中文语音识别
