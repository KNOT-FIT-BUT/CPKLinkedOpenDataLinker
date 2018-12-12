#!/bin/bash
#Spuštění experimentů pro testování namegenu.

mkdir testRes/wm/error_words

./namegen.py -o testRes/wm/res.txt testData/entities_with_gendertype_1537441121 -pwm -ew testRes/wm/error_words/error_words.lntrf -gn testRes/wm/given_names.lntrf -sn testRes/wm/surnames.lntrf -l testRes/wm/locations.lntrf 2> testRes/wm/log.txt


cd testRes/wm/error_words/
grep -P "\tjG" error_words.lntrf > error_given_names.lntrf
grep -P "\tjL" error_words.lntrf > error_locations.lntrf
grep -P "\tjS" error_words.lntrf > error_surnames.lntrf

