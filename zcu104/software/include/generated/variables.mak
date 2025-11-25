PACKAGES=libc libcompiler_rt libbase libfatfs liblitespi liblitedram libliteeth liblitesdcard liblitesata bios
PACKAGE_DIRS=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libc /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libcompiler_rt /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libbase /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libfatfs /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitespi /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitedram /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libliteeth /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitesdcard /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitesata /home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/bios
LIBS=libc libcompiler_rt libbase libfatfs liblitespi liblitedram libliteeth liblitesdcard liblitesata
TRIPLE=riscv64-unknown-elf
CPU=vexriscv
CPUFAMILY=riscv
CPUFLAGS=-march=rv32i2p0       -mabi=ilp32 -D__vexriscv__
CPUENDIANNESS=little
CLANG=0
CPU_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/cores/cpu/vexriscv
SOC_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc
PICOLIBC_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/venv/lib/python3.10/site-packages/pythondata_software_picolibc/data
COMPILER_RT_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/venv/lib/python3.10/site-packages/pythondata_software_compiler_rt/data
export BUILDINC_DIRECTORY
BUILDINC_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/build/zcu104/software/include
LIBC_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libc
LIBCOMPILER_RT_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libcompiler_rt
LIBBASE_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libbase
LIBFATFS_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libfatfs
LIBLITESPI_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitespi
LIBLITEDRAM_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitedram
LIBLITEETH_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/libliteeth
LIBLITESDCARD_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitesdcard
LIBLITESATA_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/liblitesata
BIOS_DIRECTORY=/home/hc/rowhammer-tester-ZCU104/third_party/litex/litex/soc/software/bios
LTO=0
BIOS_CONSOLE_FULL=1