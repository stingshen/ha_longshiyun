# Longshi Cloud for Home Assistant

通过 Home Assistant 读取和控制龙势云中的录音设备。本项目根据龙势云客户端的
通信协议实现，不是龙势云官方集成。

## 功能

集成会自动发现账号中的设备，并为每台设备创建以下实体：

| 实体 | 类型 | 功能 |
| --- | --- | --- |
| Connectivity | 二进制传感器 | 显示设备在线或离线 |
| Status | 传感器 | 显示在线状态，并通过属性提供设备模型、状态和配置 |
| Recording schedule | 传感器 | 显示录音计划条目数量，完整计划保存在属性中 |
| Recording mode | 下拉框 | 设置全天、事件、计划或关闭录音模式 |
| Recording mode setting state | 传感器 | 显示模式设置进度、目标模式和错误；新选择会取消旧设置任务 |
| Recording sensitivity | 数值 | 设置录音灵敏度，范围 `0-100` |
| Recording volume | 数值 | 设置录音音量，范围 `0-100` |

集成每 60 秒刷新一次。Connectivity 和 Status 使用龙势云设备网关报告的在线状态。
设备在线但暂时没有响应控制会话时，设备仍显示在线，但控制实体会标记为不可用。
录音模式、灵敏度和音量使用设备独立查询接口返回的实时值，不使用云端缓存值。
录音模式设置状态为 `idle`、`setting`、`succeeded` 或 `failed`。如果设备仍在处理
旧模式时选择了新模式，集成会取消旧设置任务并只继续处理最新选择。
设备确认新模式后，HA 会立即更新模式和设置状态；其他设备信息继续按正常轮询周期刷新。

## 要求

- Home Assistant 2024.6 或更高版本
- Home Assistant 主机可以连接龙势云服务器和设备网关
- 有效的龙势云账号和密码

## 使用 HACS 安装

1. 打开 HACS，进入 **Integrations**。
2. 打开右上角菜单，选择 **Custom repositories**。
3. 输入 `https://github.com/stingshen/ha_longshiyun`，类别选择 **Integration**。
4. 安装 **Longshi Cloud** 并重启 Home Assistant。
5. 打开 **设置 > 设备与服务 > 添加集成**。
6. 搜索 **Longshi Cloud**，输入龙势云账号、密码和区域。

## 手动安装

1. 下载此仓库源码。

2. 将仓库中的 `custom_components/longshi_cloud` 复制到 Home Assistant 配置目录：

   ```text
   /config/custom_components/longshi_cloud
   ```

   最终应存在：

   ```text
   /config/custom_components/longshi_cloud/manifest.json
   ```

3. 重启 Home Assistant。

4. 打开 **设置 > 设备与服务 > 添加集成**。

5. 搜索并选择 **Longshi Cloud**。

6. 输入龙势云用户名和密码。区域一般选择 `auto`；中国账号也可选择 `cn`。

7. 提交后，Home Assistant 会自动发现账号中的所有设备。

## 控制录音设备

在设备页面直接操作 Recording mode、Recording sensitivity 和 Recording volume
实体。也可以在自动化中调用 Home Assistant 标准实体服务。

设置 `double` 设备为计划录音模式的自动化示例：

```yaml
action:
  - service: select.select_option
    target:
      entity_id: select.double_recording_mode
    data:
      option: Schedule
```

设置录音音量：

```yaml
action:
  - service: number.set_value
    target:
      entity_id: number.double_recording_volume
    data:
      value: 50
```

实际实体 ID 由 Home Assistant 根据设备名称生成，请在设备页面确认。

每天早晨 07:00 关闭录音的自动化示例：

```yaml
alias: 每天早晨关闭录音
triggers:
  - trigger: time
    at: "07:00:00"
actions:
  - action: select.select_option
    target:
      entity_id: select.double_recording_mode
    data:
      option: Off
mode: single
```

自动化时间使用 Home Assistant 配置的时区。

## 为设备创建独立侧边栏

可以为每台龙势云设备创建一个单独的 Home Assistant 仪表盘，并将它固定在侧边栏。
以下示例为 `double` 设备创建侧边栏页面。

### 使用 Home Assistant 界面创建

1. 打开 **设置 > 仪表盘**。
2. 点击右下角 **添加仪表盘**。
3. 名称填写 `Double 录音设备`，图标填写 `mdi:record-rec`。
4. 确保启用 **在侧边栏中显示**，然后创建仪表盘。
5. 打开新仪表盘，点击右上角菜单并选择 **编辑仪表盘**。
6. 添加一个 **实体** 卡片，并加入该设备的以下实体：

   - `binary_sensor.double_connectivity`
   - `sensor.double_status`
   - `select.double_recording_mode`
   - `sensor.double_recording_mode_setting_state`
   - `number.double_recording_sensitivity`
   - `number.double_recording_volume`
   - `sensor.double_recording_schedule`

实际实体 ID 由设备名称生成。请先在 **设置 > 设备与服务 > 实体** 中搜索设备名称并
确认实体 ID。

### 使用 YAML 创建

在 `/config/configuration.yaml` 中加入：

```yaml
lovelace:
  mode: storage
  dashboards:
    lovelace-double:
      mode: yaml
      title: Double 录音设备
      icon: mdi:record-rec
      show_in_sidebar: true
      filename: double-dashboard.yaml
```

然后创建 `/config/double-dashboard.yaml`：

```yaml
title: Double 录音设备
views:
  - title: 录音控制
    path: recording
    icon: mdi:record-rec
    cards:
      - type: entities
        title: Double
        show_header_toggle: false
        entities:
          - entity: binary_sensor.double_connectivity
            name: 连接状态
          - entity: sensor.double_status
            name: 设备状态
          - entity: select.double_recording_mode
            name: 录音模式
          - entity: sensor.double_recording_mode_setting_state
            name: 模式设置状态
          - entity: number.double_recording_sensitivity
            name: 录音灵敏度
          - entity: number.double_recording_volume
            name: 录音音量
          - entity: sensor.double_recording_schedule
            name: 录音计划
```

保存文件后重启 Home Assistant。侧边栏中会出现 **Double 录音设备**。为其他设备
创建侧边栏时，复制此配置并替换仪表盘 ID、文件名和实体 ID。

## 区域设置

| 区域值 | 账号服务器 | 默认国家区号 |
| --- | --- | --- |
| `auto` | 自动尝试以下区域 | 自动推断 |
| `cn` | `rsroot.rongsee.net` | `86` |
| `asia` | `rsroot-xjp.audiocam.net` | `65` |
| `us` | `rsroot-us.audiocam.net` | `1` |

如果设备网关认证失败，可以删除并重新添加集成，在配置时填写正确的国家区号。

## 故障排查

### 集成无法登录

- 确认使用完整账号，例如邮箱账号不能省略域名。
- 区域选择 `auto`。
- 检查 Home Assistant 日志中的 `longshi_cloud` 错误。

### 设备显示离线

设备可能处于休眠或没有网络。集成会向设备发送唤醒命令，但设备仍可能无法及时
响应。等待设备上线后，使用 Home Assistant 实体页面的刷新功能或等待下一次轮询。

### 开启调试日志

在 `configuration.yaml` 中添加：

```yaml
logger:
  logs:
    custom_components.longshi_cloud: debug
```

重启 Home Assistant 后查看日志。日志不会主动输出账号密码或设备通信密码。

## 安全说明

- 龙势云协议使用未加密的 WebSocket 连接，但消息载荷使用厂商协议加密。
- Home Assistant 会把账号密码保存在配置条目中。请保护好 Home Assistant 配置目录。
- 集成不会在实体属性或正常日志中暴露账号密码及设备通信密码。

## 开发验证

运行静态语法检查：

```bash
python3 -m compileall custom_components/longshi_cloud
```

## 隐私与安全

提交 Issue 时请勿附带龙势云密码、Home Assistant 长期访问令牌、设备通信密码或完整日志。

## 许可证

本项目使用 MIT License。
