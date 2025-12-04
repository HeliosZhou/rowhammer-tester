class RowMapping:
    subclasses = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        RowMapping.subclasses[cls.__name__] = cls()

    def get_by_name(name):
        return RowMapping.subclasses[name]

    def logical_to_physical(self, logical):
        raise NotImplementedError("Convert logical row number to physical row number")

    def physical_to_logical(self, physical):
        raise NotImplementedError("Convert physical row number to logical row number")


class TrivialRowMapping(RowMapping):

    def logical_to_physical(self, logical):
        return logical

    def physical_to_logical(self, physical):
        return physical


class TypeARowMapping(RowMapping):

    def logical_to_physical(self, logical):
        bit3 = (logical & 8) >> 3
        return logical ^ (bit3 << 1) ^ (bit3 << 2)

    def physical_to_logical(self, physical):
        bit3 = (physical & 8) >> 3
        return physical ^ (bit3 << 1) ^ (bit3 << 2)


class TypeBRowMapping(RowMapping):

    def logical_to_physical(self, logical):
        return logical * 2

    def physical_to_logical(self, physical):
        return physical // 2


class SamsungRowMapping(RowMapping):
    """Samsung芯片特定的行映射方案
    
    基于真实的Samsung DRAM芯片逻辑-物理行映射算法实现
    该映射方案通过位操作实现行地址的交错分布，减少相邻行的干扰
    
    算法原理:
    - 如果逻辑行号的第3位为1，则对位1和位2进行反转操作
    - 如果逻辑行号的第3位为0，则保持原地址不变
    
    这种映射确保连续的逻辑行被分散到不同的物理位置，
    从而优化DRAM的性能并减少行间串扰。
    """

    def logical_to_physical(self, logical):
        """Samsung逻辑到物理行号映射
        
        Args:
            logical: 逻辑行号
            
        Returns:
            physical: 物理行号
        """
        if logical & 0x8:  # 检查第3位(bit 3)是否为1
            # 保持除位1和位2外的所有位
            physical = logical & 0xFFFFFFF9  # 清除位1和位2 (保持位0和位3+)
            # 反转位1和位2并设置
            physical |= (~logical & 0x00000006)  # 反转并设置位1和位2
            return physical
        else:
            # 第3位为0时，直接返回逻辑地址
            return logical

    def physical_to_logical(self, physical):
        """Samsung物理到逻辑行号映射（反向映射）
        
        Args:
            physical: 物理行号
            
        Returns:
            logical: 逻辑行号
        """
        if physical & 0x8:  # 检查第3位(bit 3)是否为1
            # 保持除位1和位2外的所有位
            logical = physical & 0xFFFFFFF9  # 清除位1和位2
            # 反转位1和位2并设置（逆操作）
            logical |= (~physical & 0x00000006)  # 反转并设置位1和位2
            return logical
        else:
            # 第3位为0时，直接返回物理地址
            return physical
