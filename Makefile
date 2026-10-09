
SIM = verilator
TOPLEVEL_LANG = verilog
TOPLEVEL = axi_dma
COCOTB_TEST_MODULES = test_axi_dma,test_axi_dma_model,test_axi_dma_errors,test_axi_dma_bursts,test_axi_dma_backpressure,test_axi_dma_response_delays,test_axi_dma_queue,test_axi_dma_randomized,test_axi_dma_reset

VERILOG_SOURCES = $(PWD)/rtl/axi_dma.sv
PYTHONPATH := $(PWD)/tb/tests:$(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += --assert

include $(shell cocotb-config --makefiles)/Makefile.sim
