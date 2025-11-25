# 在ZCU104上手动读取SPD EEPROM数据

在ZCU104平台上，DDR4内存模块的SPD (Serial Presence Detect) EEPROM通过I2C总线访问。但是，由于ZCU104硬件设计的特殊性，需要先配置I2C开关才能访问SPD EEPROM。

## 手动读取SPD数据步骤

1. 启动BIOS控制台:
   ```bash
   cd rowhammer_tester/scripts
   python bios_console.py
   ```

2. 在BIOS控制台中执行以下命令:
   ```
   # 首先配置I2C开关选择DDR4 SPD EEPROM
   i2c_write 0x74 0x80 1
   
   # 然后读取SPD数据 (地址1是DDR4 SPD EEPROM的默认地址)
   sdram_spd 1
   ```

3. 从输出中复制内存转储数据并保存到文件中(spd_data.txt)。

## SPD数据格式说明

SPD数据是一个256或512字节的二进制数据块，包含内存模块的各种参数:
- 偏移量0-117: 基本信息 (模块类型、容量、速度等)
- 偏移量118-255: 扩展信息

## 使用SPD数据

读取SPD数据后，可以使用以下命令查看模块参数:
```bash
cd rowhammer_tester/scripts
python spd_eeprom.py show spd_data_file.bin 125e6
```
_SDRAMModule:
  clk_freq: 125000000.0
  rate: 1:4
  speedgrade: 3200
  geom_settings: <litedram.common.GeomSettings object at 0x77783cf20670>
  timing_settings: <litedram.common.TimingSettings object at 0x77783cf205b0>
  memtype: DDR4
  nbanks: 16
  nrows: 65536
  ncols: 1024
  technology_timings: <litedram.modules._TechnologyTimings object at 0x77783cf206d0>
  speedgrade_timings: {'3200': <litedram.modules._SpeedgradeTimings object at 0x77783cf20700>, 'default': <litedram.modules._SpeedgradeTimings object at 0x77783cf20700>}
_TechnologyTimings:
  tREFI: {'1x': 7812.5, '2x': 3906.25, '4x': 1953.125}
  tWTR: (4, 7.5)
  tCCD: (4, 5.0)
  tRRD: (4, 4.9)
  tZQCS: (128, 80)
_SpeedgradeTimings:
  tRP: 13.75
  tRCD: 13.75
  tWR: 15.0
  tRFC: {'1x': (None, 350.0), '2x': (None, 260.0), '4x': (None, 160.0)}
  tFAW: (20, 21.0)
  tRAS: 32.0
GeomSettings:
  bankbits: 4
  rowbits: 16
  colbits: 10
  addressbits: 16
TimingSettings:
  tRP: 3
  tRCD: 3
  tWR: 3
  tWTR: 2
  tREFI: 977
  tRFC: 45
  tFAW: 5
  tCCD: 2
  tRRD: 2
  tRC: 7
  tRAS: 5
  tZQCS: 32
  fine_refresh_mode: 1x
其中125e6是系统时钟频率。



