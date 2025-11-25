# This file provides fast way for defininig new SDRAM modules.
# Modules defined in this files, after verifying that the settings are correct,
# should be later moved to LiteDRAM repository in a PR and removed from here.

from litedram.modules import _TechnologyTimings, _SpeedgradeTimings, DDR4Module

class MTA4ATF1G64HZ(DDR4Module):
    # geometry
    ngroupbanks = 4
    ngroups     = 2
    nbanks      = ngroups * ngroupbanks
    nrows       = 128*1024
    ncols       = 1024
    # timings
    trefi = {"1x": 64e6/8192,   "2x": (64e6/8192)/2, "4x": (64e6/8192)/4}
    trfc  = {"1x": (None, 350), "2x": (None, 260),   "4x": (None, 160)}
    technology_timings = _TechnologyTimings(tREFI=trefi, tWTR=(4, 7.5), tCCD=(4, 6.25), tRRD=(4, 7.5), tZQCS=(128, None))
    speedgrade_timings = {
        "2666": _SpeedgradeTimings(tRP=13.75, tRCD=13.75, tWR=15, tRFC=trfc, tFAW=(28, 30), tRAS=32),
    }
    speedgrade_timings["default"] = speedgrade_timings["2666"]

class M471A1K43EB1(DDR4Module):
    """Samsung M471A1K43EB1-CWE DDR4-3200 8GB SO-DIMM module"""
    # geometry (8GB, x8, single rank)
    ngroupbanks = 4
    ngroups     = 4  
    nbanks      = ngroups * ngroupbanks  # 16 banks total
    nrows       = 65536  # 64K rows
    ncols       = 1024   # 1K columns
    # timings
    trefi = {"1x": 64e6/8192, "2x": (64e6/8192)/2, "4x": (64e6/8192)/4}
    trfc  = {"1x": (None, 350), "2x": (None, 260), "4x": (None, 160)}
    technology_timings = _TechnologyTimings(tREFI=trefi, tWTR=(4, 7.5), tCCD=(4, 5.0), tRRD=(4, 4.9), tZQCS=(128, 80))
    speedgrade_timings = {
        # DDR4-1000: 计算基于以下原理：
        # - DDR4 JEDEC标准最小时序要求
        # - 125MHz系统时钟 (8ns周期)
        # - DDR时钟500MHz (2ns周期)
        # - 取max(时钟周期要求, 绝对时间要求)
        "1000": _SpeedgradeTimings(
            tRP=13.75,    # 行预充电时间: DDR4最小值13.75ns
            tRCD=13.75,   # RAS-CAS延迟: DDR4最小值13.75ns  
            tWR=15,       # 写恢复时间: DDR4标准15ns
            tRFC=trfc,    # 刷新时间: 取决于容量，不变
            tFAW=(None, 40),  # 四行激活窗口: DDR4典型值35-40ns
            tRAS=35       # 行激活时间: DDR4最小值35ns
        ),
        "2133": _SpeedgradeTimings(tRP=13.5, tRCD=13.5, tWR=15, tRFC=trfc, tFAW=(20, 25), tRAS=33),
        "2400": _SpeedgradeTimings(tRP=13.32, tRCD=13.32, tWR=15, tRFC=trfc, tFAW=(20, 25), tRAS=32),
        "2666": _SpeedgradeTimings(tRP=13.5, tRCD=13.5, tWR=15, tRFC=trfc, tFAW=(20, 25), tRAS=32),
        "3200": _SpeedgradeTimings(tRP=13.75, tRCD=13.75, tWR=15, tRFC=trfc, tFAW=(20, 21), tRAS=32),
    }
    speedgrade_timings["default"] = speedgrade_timings["1000"]  # 默认使用1000MHz以匹配125MHz系统时钟
