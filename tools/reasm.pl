#!/usr/bin/env perl
# Reassemble a part of БЕМШ and compare it with the original binary.
#
# Usage: tools/reasm.pl [-v] parts/NAME[.variant].be
#   load address and zone count are taken from parts.txt, the original
#   from parts/NAME.bin.
# 1. Translates NAME.be with БЕМШ (from disk 2048, as re-dispak/asm.pl does);
#    the object module goes to the scratch disk 2222, zone 0000 (ЗОНМОД).
# 2. Links it with РВС (disk 2248, zones 0105-0106) at the part's address
#    into zones 0010.. of 2222 (ЗОНГП).
# 3. Dumps those zones to parts/NAME.new and compares them with NAME.bin.
# The listing of the translation is left in parts/NAME.be.lst.
use utf8;
use feature 'unicode_strings';
use open ':encoding(UTF-8)';
use open ':std', ':encoding(UTF-8)';

$verbose = 0;
if ($#ARGV >= 0 && $ARGV[0] eq '-v') { $verbose = 1; shift @ARGV; }
die "Usage: reasm.pl [-v] parts/NAME.be\n" unless $#ARGV == 0;
($src) = @ARGV;
($base = $src) =~ s/\.be$//;
($part = $base) =~ s|.*/||;
$part =~ s/\..*//;            # parts/mred2.plain.be is a variant of mred2
$orig = "parts/$part.bin";
open(P, 'parts.txt') || die "No parts.txt\n";
while (<P>) {
    next if /^#/;
    my ($n, $m, $a, @z) = split;
    if ($n eq $part) { $naz = $a; $nz = @z; }
}
close(P);
die "$part not in parts.txt\n" unless defined $naz;
# an image loaded at 0 is disassembled from word 1 (word 0 must be zero)
$naz = sprintf('%06o', oct($naz) || 1);

$ENV{BESM6_PATH} = '.:' . ($ENV{BESM6_PATH} || '/usr/local/share/besm6');
system('touch 2222');

# Module name: label of the СТАРТ line
open(F, $src) || die "Cannot open $src\n";
while (<F>) {
    my ($name, $start) = split;
    if ($start =~ /^(старт|start)$/i) { $mod = $name; last; }
}
close(F);
die "No СТАРТ in $src\n" unless defined $mod;

# Translation job (same template as re-dispak/asm.pl), listing on
open(B, ">$base.asm.b6") || die;
print B qq/шифр 419999^
трак 64^
лент 30(2048-6200)^
лент 42(2099)^
лент 43(2222-ЗП)^
ацп 40^
росп 0^
врем 240^
лист 0-37^
вход 4000^
е
в 4000
к 00 010 4003
к 15 24 04000
к 00 066 0001 00 000 0100
с 3000 67
в 14000
а1
ВВД\$\$\$^
/;
open(F, $src) || die;
while (<F>) {
    chop;
    $_ = '*' if /^\s*$/;
    print B "$_^\n";
}
close(F);
print B qq/
КВЧ\$\$\$^
ТРН\$\$\$^
ЧТКОМП420070^
0-0^
ЗОНМОД430000  0004^
КНЦ\$\$\$^
_\$ЕКОНЕЦ
/;
close(B);
system("dispak $base.asm.b6 > $src.lst");
$res = `grep ОШИБОК= $src.lst`;
print STDERR "$mod: $res";

# Link job: the loader stub from re-dispak/rvs.pl
$name = sprintf('%-6s', $mod);
open(B, ">$base.rvs.b6") || die;
print B qq/шифр 419999^
лен 67(2248)42(2113)^
лен 43(2222-зп)^
росп 0^
вход 1000^
е
в 1000
к 00 070 1003
к 00 070 1004
к 00 30 70000
с 0010 3400 0067 0105
с 0010 3500 0067 0106
в 2000
а1
мдл   ${name}430000^наз   $naz^зонгп 430010     $nz^
конец ^
_\$
еконец
/;
close(B);
system("besmtool zero 2222 --start=010 --length=$nz > /dev/null");
$log = `dispak -s $base.rvs.b6`;
print $log if $verbose;
print grep(/ЗОНГП|ОШИБ/, split /^/, $log);
system("besmtool dump 2222 --start=010 --length=$nz --to-file=$base.new > /dev/null");
$diff = `cmp -l $orig $base.new | wc -l`;
chop $diff;
if ($diff == 0) {
    print "\033[1;32m$base.new matches $orig\033[22;39m\n";
} else {
    $first = `cmp $orig $base.new`;
    ($byte) = $first =~ /byte (\d+)/;
    printf("\033[1;31m$base.new differs from $orig in $diff bytes, first at word %05o\033[22;39m\n",
        (oct($naz) & ~01777) + int(($byte - 1) / 6));
    exit 1;
}
