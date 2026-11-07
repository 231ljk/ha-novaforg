# NovaForge for Home Assistant

[NovaForge Studio](https://github.com/231ljk) 的官方 Home Assistant 社区集成。
用 NovaForge 编译并烧录的 ESP32 固件内置局域网 HTTP API 与 mDNS 广播，
安装本集成后，Home Assistant 会**自动发现设备**并创建开关 / 传感器实体——
不需要 MQTT Broker，也不需要刷 ESPHome、Tasmota 等任何第三方固件。

## 工作原理

- 固件开机后通过 mDNS 广播 `_novaforge._tcp` 服务（TXT 携带硬件 ID、设备名、固件版本）
- 集成通过 zeroconf 自动发现设备，点击确认即完成接入（也可手动输入 IP）
- 状态同步走局域网 HTTP 轮询（`GET /api/state`，10 秒一次），开关控制走 `GET /api/set`
- **设备以芯片 MAC 派生的硬件 ID（形如 `nf-a4cf12ff7e2a`）作为唯一标识**：
  多台同名设备同时接入、或之后随意修改设备名称，都不会串号、掉线或重复注册；
  设备更换 IP 时会自动更新已配置条目的地址

## 安装

### 方式一：HACS 自定义仓库（推荐）

1. 打开 HACS → 右上角菜单 → **Custom repositories**
2. 仓库地址填 `https://github.com/231ljk/ha-novaforg`，类别选 **Integration**
3. 在 HACS 中安装 **NovaForge**，然后重启 Home Assistant

### 方式二：手动安装

1. 将 `custom_components/novaforge` 整个目录复制到 HA 配置目录下的 `custom_components/`
2. 重启 Home Assistant

## 使用

1. 在 NovaForge Studio 中配置引脚，编译并烧录官方固件到 ESP32
2. 设备联网后，打开 HA「设置 → 设备与服务」，会出现发现的 NovaForge 设备
3. 点击确认即可；输出引脚自动生成**开关**，输入引脚自动生成**二元传感器**

也可以「添加集成 → NovaForge」手动输入设备 IP。

## 实体映射

| 固件引脚 | HA 实体 | 说明 |
| --- | --- | --- |
| `mode: "out"` | `switch` | 开/关写入 `value=1/0` |
| `mode: "in"` | `binary_sensor` | 只读，10 秒轮询刷新 |
