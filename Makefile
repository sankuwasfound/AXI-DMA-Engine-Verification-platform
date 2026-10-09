
SIM = verilator
TOPLEVEL_LANG = verilog
TOPLEVEL = axi_dma
COCOTB_TEST_MODULES = test_axi_dma,test_axi_dma_model

VERILOG_SOURCES = $(PWD)/rtl/axi_dma.sv
PYTHONPATH := $(PWD)/tb/tests:$(PWD)/tb:$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim
