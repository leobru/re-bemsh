#!/usr/bin/env perl
# Reassemble the parts of БЕМШ and compare them with the original binaries.
#
# Usage: tools/reasm.pl [-v] [-t] parts/NAME[.variant].be ...
#   -t  translate only (for the listing), no linking;
#   -v  print the РВС log.
# 0. The macro library: macros.be compiled with ЗПКОМП into zones 040-046
#    of 2222, kept in macros.lib (rebuilt when older than macros.be).
# 1. Translates each source with БЕМШ (from disk 2048, as re-dispak/asm.pl
#    does) and that library (ЧТКОМП430040). The object module goes to the
#    scratch disk 2222, zone 0100+010*i (i - line of the part in
#    parts.txt); for parts/NAME.be it is kept in parts/NAME.obj. The
#    listing is left in SOURCE.lst.
# 2. Unless -t: one РВС run (disk 2248, zones 0105-0106) links all parts of
#    parts.txt, each a group of its own at its address (НАЗ) into zones
#    0400+010*i of 2222 (ЗОНГП); the object modules come from parts/*.obj
#    (translated first when missing or older than parts/NAME.be), so the
#    ВНЕШ/ВХОД links between the parts are resolved.
# 3. Dumps each image to parts/NAME.new and compares it with parts/NAME.bin.
use utf8;
use feature 'unicode_strings';
use open ':encoding(UTF-8)';
use open ':std', ':encoding(UTF-8)';

$verbose = $tonly = 0;
while (@ARGV && $ARGV[0] =~ /^-/) {
    my $o = shift @ARGV;
    if ($o eq '-v') { $verbose = 1 } elsif ($o eq '-t') { $tonly = 1 }
    else { die "Unknown option $o\n" }
}
die "Usage: reasm.pl [-v] [-t] parts/NAME.be ...\n" unless @ARGV || !$tonly;

open(P, 'parts.txt') || die "No parts.txt\n";
$i = 0;
while (<P>) {
    next if /^#/ || !/\S/;
    my ($n, $m, $a, @z) = split;
    push @parts, $n;
    $pnaz{$n} = $a; $pnz{$n} = @z; $pidx{$n} = $i++; $pmod{$n} = $m;
}
close(P);
sub objzone { sprintf('%04o', 0100 + 010 * $pidx{$_[0]}) }
sub imgzone { sprintf('%04o', 0400 + 010 * $pidx{$_[0]}) }

$ENV{BESM6_PATH} = '.:' . ($ENV{BESM6_PATH} || '/usr/local/share/besm6');
system('touch 2222');

# Translate SRC into the object zone of part P (none for the library),
# CARDS - control cards after ТРН$$$. The listing goes to SRC.lst.
sub translate {
    my ($src, $p, $cards) = @_;
    my ($base) = $src =~ /^(.*)\.be$/;
    $cards = "ЧТКОМП430040^\n0-0^\nЗОНМОД43" . objzone($p) . "  0010^\n"
        unless defined $cards;
    my $mod;
    open(F, $src) || die "Cannot open $src\n";
    while (<F>) {
        my ($name, $start) = split;
        if ($start =~ /^(старт|start)$/i) { $mod = $name; last; }
    }
    close(F);
    die "No СТАРТ in $src\n" unless defined $mod || !defined $p;
    $mod = $src unless defined $mod;
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
    print B "КВЧ\$\$\$^\nТРН\$\$\$^\n${cards}КНЦ\$\$\$^\n_\$ЕКОНЕЦ\n";
    close(B);
    system("dispak $base.asm.b6 > $src.lst");
    my $res = `grep ОШИБОК= $src.lst`;
    print STDERR "$mod: $res";
    system("besmtool dump 2222 --start=" . objzone($p) .
           " --length=010 --to-file=parts/$p.obj > /dev/null")
        if defined $p && $src eq "parts/$p.be";
}

# Macro library
if (!-e 'macros.lib' || -M 'macros.lib' > -M 'macros.be') {
    translate('macros.be', undef, "ЗПКОМП430040^\n1-1^\n");
    system("besmtool dump 2222 --start=040 --length=7 --to-file=macros.lib > /dev/null");
}
system("besmtool write 2222 --start=040 --from-file=macros.lib > /dev/null");

for $src (@ARGV) {
    my ($p) = $src =~ m|([^/.]+)[^/]*\.be$|;
    die "$src: $p not in parts.txt\n" unless defined $pidx{$p};
    die "$src: a variant can only be translated (-t)\n"
        unless $tonly || $src eq "parts/$p.be";
    translate($src, $p);
}
exit 0 if $tonly;

# Link job: the loader stub from re-dispak/rvs.pl, all parts at once
for $p (@parts) {
    translate("parts/$p.be", $p)
        if !-e "parts/$p.obj" || -M "parts/$p.obj" > -M "parts/$p.be";
    system("besmtool write 2222 --start=" . objzone($p) .
           " --from-file=parts/$p.obj > /dev/null");
    system("besmtool zero 2222 --start=" . imgzone($p) .
           " --length=$pnz{$p} > /dev/null");
}
open(B, '>parts/link.rvs.b6') || die;
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
/;
for $p (@parts) {
    # an image loaded at 0 is disassembled from word 1 (word 0 must be zero)
    printf B "мдл   %-6s43%s^\nназ   %06o^\nзонгп 43%s     %d^\n",
        $pmod{$p}, objzone($p), oct($pnaz{$p}) || 1, imgzone($p), $pnz{$p};
}
print B "конец ^\n_\$\nеконец\n";
close(B);
$log = `dispak -s parts/link.rvs.b6`;
print $log if $verbose;
print grep(/ОШИБ|НЕТ |КОНФУС/, split /^/, $log);

$bad = 0;
for $p (@parts) {
    my ($orig, $new) = ("parts/$p.bin", "parts/$p.new");
    system("besmtool dump 2222 --start=" . imgzone($p) .
           " --length=$pnz{$p} --to-file=$new > /dev/null");
    my $diff = `cmp -l $orig $new | wc -l`;
    chop $diff;
    if ($diff == 0) {
        print "\033[1;32m$new matches $orig\033[22;39m\n";
    } else {
        my ($byte) = `cmp $orig $new` =~ /byte (\d+)/;
        printf("\033[1;31m$new differs from $orig in $diff bytes, first at word %05o\033[22;39m\n",
            ((oct($pnaz{$p}) || 1) & ~01777) + int(($byte - 1) / 6));
        $bad = 1;
    }
}
exit $bad;
