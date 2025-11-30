#!/usr/bin/env python3
# 这是一个使用硬件BIST（内建自测试）模块执行Rowhammer攻击的核心脚本。
# 它继承自通用的Rowhammer类，但实现了硬件加速的攻击和验证方法。

import time
from collections import defaultdict

from rowhammer_tester.scripts.rowhammer import RowHammer, main
from rowhammer_tester.scripts.utils import hw_memset, hw_memtest, memwrite, setup_inverters

################################################################################


class HwRowHammer(RowHammer):
    # HwRowHammer类，实现了基于硬件的Rowhammer攻击逻辑。

    def attack(self, row_tuple, read_count, progress_header=""):
        # 使用BIST读取器（Reader）模块执行实际的“锤击”操作。
        # row_tuple: 一个包含要攻击的行的元组。
        # read_count: 锤击次数（总读取操作数）。
        # progress_header: 显示在进度条前的文本。

        assert len(row_tuple) <= 32  # BIST模块支持的攻击行数量有限

        # 1. 将逻辑行号转换为BIST模块使用的DMA地址。
        addresses = [
            self.converter.encode_dma(bank=self.bank, col=self.column, row=r) for r in row_tuple
        ]
        # row_strw = len(str(2**self.settings.geom.rowbits - 1))

        # 2. 配置BIST读取器模块以进行锤击，而不是正常的内存测试。
        # FIXME: ------------------ move to utils ----------------------------
        # 清空并启用错误FIFO，准备捕获可能在攻击中发生的错误（虽然主要验证在攻击后进行）。
        self.wb.regs.reader_skip_fifo.write(1)
        time.sleep(0.1)
        # Enable error FIFO
        self.wb.regs.reader_skip_fifo.write(0)

        assert self.wb.regs.reader_ready.read() == 1  # 确保BIST模块已准备就绪

        # 再次跳过（清空）错误FIFO
        self.wb.regs.reader_skip_fifo.write(1)

        # 关键配置：内存地址掩码设为0，意味着BIST模块不会自动增加内存地址。
        # 它将只访问我们接下来提供给它的地址列表。
        self.wb.regs.reader_mem_mask.write(0x00000000)
        # 关键配置：设置模数，让BIST在提供的地址列表上循环。
        self.wb.regs.reader_modulo.write(1)
        self.wb.regs.reader_data_div.write(len(row_tuple) - 1)
        # self.wb.regs.reader_data_mask.write(len(row_tuple) - 1)

        # 将要攻击的行的DMA地址写入BIST的地址模式内存中。
        memwrite(self.wb, addresses, base=self.wb.mems.reader_pattern_addr.base)
        # （这行可能用于调试，设置一个数据模式，但在锤击中不重要）
        memwrite(self.wb, ([0xAAAAAAAA] * 16), base=self.wb.mems.reader_pattern_data.base)

        # 设置总锤击次数。
        print("read_count: " + str(int(read_count)))
        self.wb.regs.reader_count.write(int(read_count))

        # 启动BIST读取器模块开始锤击！
        self.wb.regs.reader_start.write(1)
        self.wb.regs.reader_start.write(0)

        # FIXME: --------------------------- move to utils ------------------

        # 3. 监控攻击进度直到完成。
        def progress(count):
            s = f"  {progress_header}{' ' if progress_header else ''}"
            s += f"Rows = {row_tuple}, Count = {count / 1e6:5.2f}M / {read_count / 1e6:5.2f}M"
            print(s, end="  \r")

        while True:
            r_count = self.wb.regs.reader_done.read()
            progress(r_count)
            if self.wb.regs.reader_ready.read():  # 当BIST模块再次变为ready状态时，表示攻击完成。
                break
            time.sleep(10 / 1e3)

        progress(self.wb.regs.reader_done.read())  # also clears the value
        print()
        self.wb.regs.reader_modulo.write(0)  # 攻击结束后重置模数

    def check_errors(self, row_pattern):
        # 攻击结束后，使用BIST模块的正常测试功能来验证整个内存，以查找比特翻转。
        # row_pattern: 写入内存的背景数据模式。
        dma_data_width = self.settings.phy.dfi_databits * self.settings.phy.nphases
        dma_data_bytes = dma_data_width // 8

        # 调用hw_memtest，它会配置BIST来扫描整个内存，将其内容与row_pattern比较。
        errors = hw_memtest(self.wb, 0x0, self.wb.mems.main_ram.size, [row_pattern])

        # 将BIST报告的错误（基于原始DMA偏移）转换回逻辑行号。
        row_errors = defaultdict(list)
        for e in errors:
            addr = self.wb.mems.main_ram.base + e.offset * dma_data_bytes
            bank, row, col = self.converter.decode_bus(addr)
            base_addr = min(self.addresses_per_row(row))
            # 将错误按行号分组。
            row_errors[row].append(((addr - base_addr) // 4, e.data, e.expected))

        return dict(row_errors)

    def run(self, row_pairs, pattern_generator, read_count, _row_progress=16, verify_initial=True):
        # 整个Rowhammer测试流程的编排函数。

        # （可选）设置数据反转模式，用于测试数据总线。
        divisor, mask = 0, 0
        if self.data_inversion:
            divisor, mask = self.data_inversion
            divisor = int(divisor, 0)
            mask = int(mask, 0)
        setup_inverters(self.wb, divisor, mask)

        assert len(row_pairs) > 0, "No pairs to hammer"
        print("\nPreparing ...")
        # 1. 准备背景数据：使用hw_memset高速填充整个DRAM。
        row_pattern = list(pattern_generator([row_pairs[0][0]]).values())[0]
        print(f"WARNING: only single word patterns supported, using: 0x{row_pattern:08x}")
        print("\nFilling memory with data ...")
        hw_memset(self.wb, 0x0, self.wb.mems.main_ram.size, [row_pattern])

        # 2. （可选）初始验证：在攻击前检查内存，确保没有预先存在的错误。
        if verify_initial:
            print("\nVerifying written memory ...")
            errors = self.check_errors(row_pattern)
            if self.errors_count(errors) == 0:
                print("OK")
            else:
                print()
                self.display_errors(errors, read_count)
                return

        # 3. （可选）关闭DRAM刷新，这会使Rowhammer攻击更容易成功。
        if self.no_refresh:
            print("\nDisabling refresh ...")
            self.wb.regs.controller_settings_refresh.write(0)

        # 4. 执行攻击。
        if self.no_attack_time is not None:
            self.no_attack_sleep()
        else:
            print("\nRunning Rowhammer attacks ...")
            # 遍历所有要攻击的行对（或行组）。
            for i, row_tuple in enumerate(row_pairs, start=1):
                n = len(str(len(row_pairs)))
                s = f"Iter {i:{n}} / {len(row_pairs):{n}}"
                # 根据配置选择攻击方式：
                if self.payload_executor:
                    # 使用更灵活的Payload Executor进行攻击（高级功能）。
                    # 1 read count maps to 1 ACT sent to all selected rows
                    # To keep read_count consistent with BIST behavior read_count
                    # must be divided by number of rows, and rounded up
                    self.payload_executor_attack(
                        read_count=(read_count + len(row_tuple) - 1) // len(row_tuple),
                        row_tuple=row_tuple,
                    )
                else:
                    # 使用我们上面定义的基于BIST的attack方法。
                    if len(row_tuple) & (len(row_tuple) - 1) != 0:
                        print("ERROR: BIST only supports power of 2 rows\n")
                        return

                    self.attack(row_tuple, read_count=read_count, progress_header=s)

        # 5. （可选）如果之前关闭了刷新，现在重新开启它。
        if self.no_refresh:
            print("\nReenabling refresh ...")
            self.wb.regs.controller_settings_refresh.write(1)

        # 6. 最终验证：攻击结束后，再次检查整个内存以发现比特翻转。
        print("\nVerifying attacked memory ...")
        errors = self.check_errors(row_pattern)
        if self.errors_count(errors) == 0:
            print("OK")
            self.bitflip_found = False
            return {}
        else:
            # 如果发现错误，显示它们。
            print()
            errors_in_rows = self.display_errors(errors, read_count, True)
            self.bitflip_found = True
            return errors_in_rows


################################################################################

if __name__ == "__main__":
    # 脚本的入口点。
    # 它调用通用的main函数（来自父类），但将特定的HwRowHammer类作为参数传入。
    # 这使得此脚本可以重用通用的命令行参数解析和流程设置，同时注入自己独特的、基于硬件的攻击实现。
    main(row_hammer_cls=HwRowHammer)
