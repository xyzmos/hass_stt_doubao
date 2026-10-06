# 豆包语音识别 for Home Assistant

[![HACS 自定义仓库](https://img.shields.io/badge/HACS-自定义集成-orange.svg)](https://github.com/hacs/integration)
[![hacs 校验](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/validate.yml/badge.svg)](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/validate.yml)
[![release](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/release.yaml/badge.svg)](https://github.com/xyzmos/hass_stt_doubao/actions/workflows/release.yaml)

将 Home Assistant 的语音转文字（STT）替换为豆包输入法同款识别引擎，识别速度快、中文准确率高、自动加标点。基于 [doubaoime-asr](https://github.com/starccy/doubaoime-asr) 开发。

## 功能特性

- 🎙️ 中文语音识别（zh-CN），实时流式识别
- ⚡ UI 配置，即装即用，无需手动编辑配置文件
- 🔑 自动设备注册与凭据管理，开箱即用
- ✏️ 识别结果自动添加标点符号（可关闭）

## 系统要求

- Home Assistant **2024.11** 及以上
- 系统库 `libopus`（HAOS / 官方 Docker 镜像已内置，无需手动安装）

## 安装

### 方式一：HACS 安装（推荐）

[![通过 HACS 添加此仓库](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=xyzmos&repository=hass_stt_doubao&category=integration)

1. 点击上方按钮添加本仓库（或手动：**HACS → 右上角 ⋮ → 自定义仓库**，填入仓库地址，类别选 **集成**）
2. 在 HACS 中搜索 **豆包语音识别** → 下载
3. 重启 Home Assistant

### 方式二：手动安装

1. 将本仓库的 `custom_components/hass_stt_doubao` 目录复制到 HA 配置目录下的 `custom_components/` 中
2. 重启 Home Assistant

## 配置

1. **设置 → 设备与服务 → 添加集成**，搜索 **豆包语音识别**
2. 直接点 **提交** 即可（两个选项均可保持默认）：

   | 选项 | 默认值 | 说明 |
   |---|---|---|
   | 凭据文件路径 | `doubao_credentials.json` | 设备凭据缓存文件，首次使用时自动创建，相对路径基于 HA 配置目录 |
   | 启用标点符号 | 开启 | 识别结果自动添加标点 |

> 集成仅允许添加一个配置项；修改选项后自动重载生效，无需重启。

## 使用

1. 进入 **设置 → 语音助手（Assist）→ 管道**
2. 选择（或新建）一个管道，将「**语音转文字**」设为 **豆包语音识别**
3. 保存后即可通过语音唤醒/对话使用

> 💡 本集成仅提供 STT 能力，无实体服务，不需要也不支持在自动化中直接调用。

## 故障排除

| 现象 | 排查 |
|---|---|
| 集成无法加载 | 检查 HA 版本是否 ≥ 2024.11；确认 `libopus` 已安装（官方镜像内置） |
| 识别无结果 | 检查麦克风是否正常；查看 **设置 → 系统 → 日志** 中 `hass_stt_doubao` 相关日志 |
| 凭据失效 / 报错 | 删除 HA 配置目录下的 `doubao_credentials.json`，下次识别自动重新注册 |

## 免责声明

本项目基于 [doubaoime-asr](https://github.com/starccy/doubaoime-asr)，为**非官方 API**：

- 仅供学习和研究使用
- 不保证长期可用性和稳定性
- 服务端协议可能随时变更导致功能失效

## 问题反馈

[HomeAssistant 豆包输入法 STT 语音识别插件反馈](https://bbs.nextrt.com/d/3-homeassistant-dou-bao-shu-ru-fa-stt-yu-yin-shi-bie-cha-jian)

<details>
<summary><b>开发者信息</b>（点击展开）</summary>

### 技术架构

```
HA Audio Stream (PCM 16kHz Mono) → DoubaoSTTEntity → PCM→Opus → DoubaoASR WebSocket → 识别结果
```

### 目录结构

```
custom_components/hass_stt_doubao/
├── __init__.py              # 集成入口（entry.runtime_data）
├── manifest.json
├── const.py
├── config_flow.py           # Config/Options Flow
├── stt.py                   # STT 实体
├── strings.json / translations/
├── brand/icon.png
└── doubaoime_asr/           # 核心 ASR 库（vendor）
```

### 发布新版本

1. 更新 `manifest.json` 的 `version` 及更新日志
2. `git tag <version> && git push origin <version>`（兼容 `v*` 前缀）
3. CI 自动校验版本并创建 Release

</details>

## 许可证

MIT License

## 致谢

- [doubaoime-asr](https://github.com/starccy/doubaoime-asr)
- [Home Assistant](https://www.home-assistant.io/)

## 更新日志

### v1.2.1

- 集成名称改为「豆包语音识别」
- 新增 `suggested_object_id`，保证实体 ID 固定为 `stt.doubao_stt`

### v1.2.0

- 按 hassfest 规范重排 `manifest.json`，新增 `integration_type`、`single_config_entry`
- 集成数据改用 `entry.runtime_data`，选项修改后自动重载生效
- STT 实体接入设备注册表（`DeviceInfo` + `has_entity_name`）
- 凭据文件校验移入执行器，消除事件循环中的阻塞文件 I/O
- 翻译文件规范化，新增 `en.json` 及字段说明
- 修正 `hacs.json` 非法字段，声明最低 HA 版本 `2024.11.0`，新增品牌图标
- WebSocket 会话结束时正确取消收发任务，避免协程泄漏

### v1.0.0

- 初始版本：STT 组件实现、UI 配置、自动设备注册、中文语音识别
