#!/usr/bin/env perl
# Make a БЕМШ translation job (same passport and loader as re-dispak/asm.pl).
# Usage: tools/job.pl [-k] [-z] [-l] [-c КАРТА,...] src > job.b6
#   src  - a .be text, or a .b6 job: then only its ВВД$$$..КНЦ$$$ part is used
#          and taken as is (its own control cards);
#   -k   - add ЧТКОМП420070 (read the macro library from 2099, zone 070);
#   -z   - add ЗОНМОД430000  0004 (object module to 2222, zone 0);
#   -l   - full listing (0-0), otherwise 1-1 as in asm.pl;
#   -c   - extra control cards after ТРН$$$ (e.g. ПЕЧМАК,БТМАЛФ).
use utf8;
use open ':encoding(UTF-8)';
use open ':std', ':encoding(UTF-8)';
use Getopt::Std;
use Encode qw(decode);
@ARGV = map { decode("UTF-8", $_) } @ARGV;
getopts('kzlc:', \%o) && @ARGV == 1 or die "Usage: job.pl [-k] [-z] [-l] [-c cards] src\n";
open(F, $ARGV[0]) or die "Cannot open $ARGV[0]\n";
my @src = <F>;
close F;
chomp @src;
print qq/шифр 419999^
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
/;
if (grep /^ВВД\$\$\$/i, @src) {
    my $in = 0;
    for (@src) {
        $in = 1 if /^ВВД\$\$\$/i;
        next unless $in;
        print "$_^\n" unless /\^$/;
        print "$_\n" if /\^$/;
        last if /^КНЦ\$\$\$/i;
    }
} else {
    print "ВВД\$\$\$^\n";
    for (@src) {
        $_ = '*' if /^\s*$/;
        print "$_^\n";
    }
    print "КВЧ\$\$\$^\nТРН\$\$\$^\n";
    print "ЧТКОМП420070^\n" if $o{k};
    print map { "$_^\n" } split /,/, $o{c} if $o{c};
    print $o{l} ? "0-0^\n" : "1-1^\n";
    print "ЗОНМОД430000  0004^\n" if $o{z};
    print "КНЦ\$\$\$^\n";
}
print "_\$ЕКОНЕЦ\n";
