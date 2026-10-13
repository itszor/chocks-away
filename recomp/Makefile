# Static recompilation of Chocks Away: the BASIC front end (basic.c, from
# $(SS)/tools/bas2c.py, on the BASIC runtime $(SS)/runtime/basic_runtime.c),
# the machine code (gen/, from SuperSpider's analyse and gen via
# ../tools/images.py) and game.c, linked with libroger (the RISC OS runtime).
ROGER   ?= $(HOME)/stuff/libroger
SS      ?= $(HOME)/stuff/superspider
CC      ?= gcc
CFLAGS  ?= -O2 -g -w -fno-strict-aliasing $(if $(TRACE),-DRECOMP_TRACE)
GEN     := $(wildcard gen/*/code*.c) $(wildcard gen/*/entries.c)
OBJ     := $(GEN:.c=.o) basic.o basic_runtime.o game.o
LIBS    := $(shell pkg-config --libs sdl3) -lm -lpthread
INC     := -I$(ROGER)/include
PROG    := $(wildcard ../game/!Chocks/ChocksAway,*)

chocksaway: $(OBJ) $(ROGER)/libroger.a
	$(CC) $(CFLAGS) -o $@ $(OBJ) $(ROGER)/libroger.a $(LIBS)

$(ROGER)/libroger.a: FORCE
	$(MAKE) -C $(ROGER) libroger.a

gen/%.o: gen/%.c $(ROGER)/include/roger_cpu.h
	$(CC) $(CFLAGS) $(INC) -c -o $@ $<

basic.c: $(PROG) $(SS)/tools/bas2c.py
	python3 -I $(SS)/tools/bas2c.py '$(PROG)' $@

%.o: %.c $(SS)/runtime/basic_runtime.h $(ROGER)/include/roger.h
	$(CC) $(CFLAGS) $(INC) -I$(SS)/runtime -c -o $@ $<

basic_runtime.o: $(SS)/runtime/basic_runtime.c $(SS)/runtime/basic_runtime.h $(ROGER)/include/roger.h
	$(CC) $(CFLAGS) $(INC) -I$(SS)/runtime -c -o $@ $<

# make regen: assemble the core image, analyse and translate the machine code
regen:
	python3 -I ../tools/images.py assemble analyse gen

LOG ?= untranslated.log
roots:
	python3 -I ../tools/images.py roots $(LOG)

clean:
	rm -f gen/*/*.o *.o basic.c chocksaway

.PHONY: FORCE regen roots clean

game.o: gen/modules.inc
