# Транслятор БЕМШ (ИПМ МАКРО-БЕМШ ВЕР.06/78) с диска 2048, зоны 0147-0177.
DISBESM6 ?= $(HOME)/git/leobru/dispak-tools/disbesm6
export DISBESM6
PARTS := $(shell grep -v '^\#' parts.txt | awk '{print $$1}')
ZONES := $(shell grep -v '^\#' parts.txt | awk '{for (i = 4; i <= NF; i++) print $$i}')

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
# остальные задания - по jobs/OPTS (параметры tools/job.pl на каждое имя);
# "make jobs" пересобирает все, у которых изменился текст
jobs:
	tools/mkjobs.py
jobs/%.b6: jobs/OPTS FORCE
	tools/mkjobs.py $*
FORCE:
# РВС 10/75 (зона 0144) отдельной задачей: колода jobs/rvs75.job, модуль -
# из прогона jobs/zgr.b6 (ЗОНМОД)
jobs/rvs75.b6: jobs/rvs75.job
	cp $< $@
traces/rvs75.ev: jobs/rvs75.b6 jobs/zgr.b6
	@mkdir -p traces
	tools/run.sh jobs/zgr.b6 traces/rvs75.2222 > /dev/null
	IN2222=traces/rvs75.2222 tools/trace.sh $< traces/rvs75.txt | tools/phases.py - traces/rvs75.cov > $@
# все трассы: задания jobs/OPTS и три внешних (tools/cover.py), РВС 10/75
traces: jobs/avmd.b6 jobs/spe66.b6 jobs/macros.b6 traces/rvs75.ev
	tools/cover.py
traces/%.ev: jobs/%.b6
	@mkdir -p traces
	tools/trace.sh $< traces/$*.txt | tools/phases.py - traces/$*.cov > $@

# Части (parts.txt): образ, покрытие, сырой вывод disbesm6
parts: zones traces
	tools/parts.py

# Размеченные исходники из notes/ЧАСТЬ.py (остальные части - сырой вывод)
be:
	tools/mkbe.py $(basename $(notdir $(wildcard notes/*.py)))

# Текст фрагмента исходника (source.txt: диск 2053, зоны 0650-0653, код
# БЕМШ) в notes/src/*.py:
# операнды, макровызовы и комментарии для совпавших строк mred74 и mred2
source.txt:
	besmtool dump 2053 --start=0650 --length=4 --to-file=$@ > /dev/null
src: source.txt
	tools/t8text.py source.txt > source.utf8
	tools/srcapply.py source.utf8 mred74 mred2

# Покрытие кода частей всеми заданиями (трассы обновляются по надобности)
cover: traces

# Обратная сборка каждой части и побайтное сравнение
check:
	@tools/reasm.pl $(addprefix parts/,$(addsuffix .be,$(PARTS)))

clean:
	rm -f 2222 parts/*.new parts/*.b6 parts/*.lst

.PHONY: all zones traces parts be src check clean jobs cover
