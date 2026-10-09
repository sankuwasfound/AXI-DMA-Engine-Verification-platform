
SIM = verilator
TOPLEVEL_LANG = verilog
TOPLEVEL = axi_dma
COCOTB_TEST_MODULES = test_axi_dma,test_axi_dma_model,test_axi_dma_errors,test_axi_dma_bursts,test_axi_dma_backpressure

VERILOG_SOURCES = $(PWD)/rtl/axi_dma.sv
PYTHONPATH := $(PWD)/tb/tests:$(PWD)/tb:$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim
