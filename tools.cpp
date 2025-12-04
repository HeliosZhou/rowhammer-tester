#include "tools.h"

// 逻辑物理地址转换方案，定义在cpp里
LogPhysRowIDScheme logical_physical_conversion_scheme = LogPhysRowIDScheme::SAMSUNG;

Inst all_nops()
{
  return  __pack_mininsts(SMC_NOP(), SMC_NOP(), SMC_NOP(), SMC_NOP());
}

void sleep_delay (Program& program, uint64_t sleep_time) {
  while(sleep_time > UINT32_MAX){
    program.add_inst(SMC_SLEEP(UINT32_MAX));
    sleep_time -= UINT32_MAX;
  }
  switch(sleep_time){
    case 0: 
      break;
    case 1:
      program.add_inst(all_nops());
      break;
    case 2:
      program.add_inst(all_nops());
      program.add_inst(all_nops());
      break;
    default:
      program.add_inst(SMC_SLEEP(sleep_time));
      break;
  }
}

int add_op_with_delay (Program& prog, Mininst ins, int before_cycles, int after_cycles) {
    
    int remaining = before_cycles < 0 ? 0 : before_cycles;

    while(remaining >= 4) {
        prog.add_inst(all_nops());
        remaining -= 4;
    }

    switch(remaining) {
        case 0:
            prog.add_inst(__pack_mininsts(ins, SMC_NOP(), SMC_NOP(), SMC_NOP()));
            remaining = after_cycles - 3;
            break;
        case 1:
            prog.add_inst(__pack_mininsts(SMC_NOP(), ins, SMC_NOP(), SMC_NOP()));
            remaining = after_cycles - 2;
            break;
        case 2:
            prog.add_inst(__pack_mininsts(SMC_NOP(), SMC_NOP(), ins, SMC_NOP()));
            remaining = after_cycles - 1;
            break;
        case 3:
            prog.add_inst(__pack_mininsts(SMC_NOP(), SMC_NOP(), SMC_NOP(), ins));
            remaining = after_cycles;
            break;

        default:
            assert(false && "This line should not be reached. Possible bug in the program.");
    }

    while (remaining >= 4) {
        prog.add_inst(all_nops());
        remaining -= 4;
    }

    return remaining;
}

int add_op_with_delay (Program& prog, Inst ins, int before_cycles, int after_cycles) {
    
    int remaining = before_cycles;

    while(remaining > 0) {
        prog.add_inst(all_nops());
        remaining -= 4;
    }

    prog.add_inst(ins);
    remaining = after_cycles;

    while (remaining >= 4) {
        prog.add_inst(all_nops());
        remaining -= 4;
    }

    return remaining;
}

std::string createSMCLabel(const std::string& name) {
    static uint32_t label_counter = 0;
    return name + std::to_string(label_counter++);
}

SoftMCRegAllocator::SoftMCRegAllocator(uint32_t num_regs, const std::vector<uint32_t>& reserved_regs) {
    free_regs.reserve(num_regs);

    for(uint32_t i = 0; i < num_regs; i++) {
        if(std::find(reserved_regs.begin(), reserved_regs.end(), i) == reserved_regs.end())
            free_regs.emplace_back(i);
    }
}

SMC_REG SoftMCRegAllocator::allocate_SMC_REG() {
    if(free_regs.size() == 0)
        throw OutOfSoftMCRegsException();

    SMC_REG ret_reg = *(free_regs.begin());
    free_regs.erase(free_regs.begin());
    return ret_reg;
}

void SoftMCRegAllocator::free_SMC_REG(const SMC_REG r) {
    auto it = std::find(free_regs.begin(), free_regs.end(), r);
    assert(it == free_regs.end());

    free_regs.push_back(r);
}

uint SoftMCRegAllocator::num_free_regs() const {
    return free_regs.size();
}

const char* OutOfSoftMCRegsException::what() const throw () {
    return "No more SoftMC registers to allocate.";
}

//输入逻辑地址，输出物理地址
PhysicalRowID to_physical_row_id(uint logical_row_id) {
    
    switch(logical_physical_conversion_scheme) {
        case LogPhysRowIDScheme::SEQUENTIAL: {
            return logical_row_id;
        }
        case LogPhysRowIDScheme::SAMSUNG: {
            if(logical_row_id & 0x8) {
                PhysicalRowID phys_row_id = logical_row_id & 0xFFFFFFF9;
                phys_row_id |= (~logical_row_id & 0x00000006); // 设置位3和位2
                return phys_row_id;
            } else {
                return logical_row_id;
            }
        }
        default: {
            std::cout << "ERROR: unimplemented logical to physical row id conversion scheme!" << std::endl;
            exit(1);
        }
    }
}

LogicalRowID to_logical_row_id(uint physical_row_id) {
    switch(logical_physical_conversion_scheme) {
        case LogPhysRowIDScheme::SEQUENTIAL: {
            return physical_row_id;
        }
        case LogPhysRowIDScheme::SAMSUNG: {
            if(physical_row_id & 0x8) {
                LogicalRowID log_row_id = physical_row_id & 0xFFFFFFF9;
                log_row_id |= (~physical_row_id & 0x00000006); // 反演位3和位2
                return log_row_id;
            } else {
                return physical_row_id;
            }
        }
        default: {
            std::cout << "ERROR: unimplemented physical to logical row id conversion scheme!" << std::endl;
            exit(1);
        }
    }

    return 0;
}
