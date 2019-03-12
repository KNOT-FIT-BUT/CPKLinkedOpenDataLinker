#!/bin/bash
#Spuštění experimentů pro testování namegenu.

mkdir testRes/newFormat/error_words

./namegen.py -o testRes/newFormat/res.txt testData/draft_entities_with_typeflags_20181201-1547022551 -in -ew testRes/newFormat/error_words/error_words.lntrf -gn testRes/newFormat/given_names.lntrf -sn testRes/newFormat/surnames.lntrf -l testRes/newFormat/locations.lntrf 2> testRes/newFormat/log.txt


cd testRes/newFormat/error_words/
grep -P "\tjG" error_words.lntrf > error_given_names.lntrf
grep -P "\tjL" error_words.lntrf > error_locations.lntrf
grep -P "\tjS" error_words.lntrf > error_surnames.lntrf

