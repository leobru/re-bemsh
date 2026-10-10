# Транслятор БЕМШ (ИПМ МАКРО-БЕМШ ВЕР.06/78) с диска 2048, зоны 0147-0177.
DISBESM6 ?= $(HOME)/git/leobru/dispak-tools/disbesm6
export DISBESM6
PARTS := $(shell grep -v '^\#' parts.txt | awk '{print $$1}')
ZONES := $(shell grep -v '^\#' parts.txt | awk '{for (i = 4; i <= NF; i++) print $$i}')
JOBS  := avmd spe66 macros inmac errmac blmak asm1 zongp zgr rvs75

all: check

# Зоны с диска 2048
zones: $(addprefix zones/,$(addsuffix .bin,$(ZONES)))
zones/%.bin:
	@mkdir -p zones
	besmtool dump 2048 --start=$* --length=1 --to-file=$@ > /dev/null

# Задания: avmd из re-dispak (с ЧТКОМП и ЗОНМОД), spe66 и macros из dispak,
# свои тесты макросов. Трасса t2 -> покрытие по зонам (traces/ИМЯ.cov/).
jobs/avmd.b6:
	tools/job.pl -k -z $(HOME)/git/re-dispak/avmd.be > $@
jobs/spe66.b6:
	tools/job.pl $(HOME)/git/dispak/dispak/spe66.b6 > $@
jobs/macros.b6:
	tools/job.pl $(HOME)/git/dispak/dispak/macros.b6 > $@
jobs/inmac.b6: jobs/inmac.be
	tools/job.pl -k -l -c ПЕЧМАК $< > $@
jobs/errmac.b6: jobs/errmac.be
	tools/job.pl -k -l -c ПЕЧМАК $< > $@
jobs/blmak.b6: jobs/inmac.be
	tools/job.pl -k -l -c БЛМАК $< > $@
jobs/colon.b6: jobs/colon.be
	tools/job.pl -l $< > $@
jobs/colonb.b6: jobs/colon.be
	tools/job.pl -k -l -c БЛМАК $< > $@
jobs/asm1.b6: jobs/asm1.be
	tools/job.pl -k -l -z $< > $@
jobs/zongp.b6: jobs/zongp.be
	tools/job.pl -l -c "НАЗ   003000,ЗОНГП 430010     1" $< > $@
jobs/zgr.b6: jobs/zgr.be
	tools/job.pl -l -z -c "ЗОНМЕТ430020,НАЗ   004000,ЗОНГП 430010     2" $< > $@
# РВС 10/75 (зона 0144) отдельной задачей: колода jobs/rvs75.job, модуль -
# из прогона jobs/zgr.b6 (ЗОНМОД)
jobs/rvs75.b6: jobs/rvs75.job
	cp $< $@
traces/rvs75.ev: jobs/rvs75.b6 jobs/zgr.b6
	@mkdir -p traces
	tools/run.sh jobs/zgr.b6 traces/rvs75.2222 > /dev/null
	IN2222=traces/rvs75.2222 tools/trace.sh $< traces/rvs75.txt | tools/phases.py - traces/rvs75.cov > $@
traces: $(addprefix traces/,$(addsuffix .ev,$(JOBS)))
traces/%.ev: jobs/%.b6
	@mkdir -p traces
	tools/trace.sh $< traces/$*.txt | tools/phases.py - traces/$*.cov > $@

# Части (parts.txt): образ, покрытие, сырой вывод disbesm6
parts: zones traces
	tools/parts.py

# Размеченные исходники из notes/ЧАСТЬ.py (остальные части - сырой вывод)
be:
	tools/mkbe.py $(basename $(notdir $(wildcard notes/*.py)))

# Обратная сборка каждой части и побайтное сравнение
check:
	@tools/reasm.pl $(addprefix parts/,$(addsuffix .be,$(PARTS)))

clean:
	rm -f 2222 parts/*.new parts/*.b6 parts/*.lst

.PHONY: all zones traces parts be check clean
