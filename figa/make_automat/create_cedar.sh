#!/bin/sh

# Author: Lubomir Otrusina, iotrusina@fit.vutbr.cz

export LC_ALL="C.UTF-8"

# default values
KB="KBstatsMetrics.all"
KB_GIVEN=false
LOWERCASE=false
URI=false
CEDAR=false
DARTS=false
EXT=".ct"

# saved values
LAUNCHED=$0
KB_WORKDIR=$PWD

#=====================================================================
# nastavovani parametru prikazove radky

usage()
{
    echo "Usage: create_cedar.sh [-h] [-l|-u] [-c|-d] --knowledge-base=KBstatsMetrics.all"
    echo ""
    echo -e "\t-h --help"
    echo -e "\t-l --lowercase"
    echo -e "\t-u --uri"
    echo -e "\t-c --cedar (default)"
    echo -e "\t-d --darts"
    echo -e "\t-k --knowledge-base=$KB"
    echo ""
}


makeAutomata() {
    EXT=$1

    if $LOWERCASE
    then
        ../figav1.0 -d namelist -n -w ../automata-lower"$EXT"
    elif $URI
    then
        ../figav1.0 -d namelist -n -w ../automata-uri"$EXT"
    else
        ../figav1.0 -d namelist -n -w ../automata"$EXT"
    fi
}


while [ "$1" != "" ]; do
    PARAM=`echo $1 | awk -F= '{print $1}'`
    VALUE=`echo $1 | awk -F= '{print $2}'`
    case $PARAM in
        -h | --help)
            usage
            exit
            ;;
        -l | --lowercase)
            LOWERCASE=true
            ;;
        -u | --uri)
            URI=true
            ;;
        -c | --cedar)
            CEDAR=true
            ;;
        -d | --darts)
            DARTS=true
            ;;
        -k | --knowledge-base)
            if [ "$PARAM" = "-k" ]; then
              if [ "$2" = "" ]; then
                usage
                exit
              else
                VALUE="$2"
                shift
              fi
            fi

            KB=$VALUE
            KB_GIVEN=true
            ;;
        *)
            echo "ERROR: unknown parameter \"$PARAM\""
            usage
            exit 1
            ;;
    esac
    shift
done


if ! $DARTS
then
    CEDAR=true
fi


if [ ! -f "$KB" ]; then
  echo "ERROR: Could not found KB on path: ${KB}" >&2
  if ! $KB_GIVEN ; then
    echo "Did you forget to set the parameter \"-k\"? (Default \"${KB}\" was used.)\n" >&2

    usage
  fi
  exit
fi

#=====================================================================
# zmena spousteci cesty na tu, ve ktere se nachazi create_cedar.sh
cd `dirname "${LAUNCHED}"`
# ale soucasne je treba zmenit cestu ke KB, jinak bychom problem posunuli jinam
KB="${KB_WORKDIR}/${KB}"

# cesta pro import modulů do Python skriptů
export PYTHONPATH=../../:$PYTHONPATH

#=====================================================================
CURRENT_VERSION=`cat ../../VERSION`
F_ENTITIES_WITH_TYPEFLAGS="entities_with_typeflags_${CURRENT_VERSION}"
F_CZECHNAMES="czechnames_${CURRENT_VERSION}.out"
F_CZECHNAMES_INVALID="${F_CZECHNAMES}.invalid"
# temporary files to avoid skipping of generating target files, when generating failed or aborted
F_TMP_ENTITIES_WITH_TYPEFLAGS="_${F_ENTITIES_WITH_TYPEFLAGS}"
F_TMP_CZECHNAMES="_${F_CZECHNAMES}"
# Skip generating some files if exist, because they are very time consumed
if ! test -f "${F_ENTITIES_WITH_TYPEFLAGS}"; then
  # Be careful > "Ά" or "Α" in "sed" is foreign char not "A" from Latin(-base) chars.
  python3 get_entities_with_typeflags.py -k "$KB" | awk -F"\t" 'NF>2{key = $1 "\t" $2 "\t" $3; a[key] = a[key] (a[key] ? " " : "") $4;};END{for(i in a) print i "\t" a[i]}' | LC_ALL=C sort -u > "${F_TMP_ENTITIES_WITH_TYPEFLAGS}"
  cat "${F_TMP_ENTITIES_WITH_TYPEFLAGS}" | sed '/^[ΆΑ]/Q' | grep -P "^[^\t]+\t(cs)?\t" | cut -f2 --complement > "${F_ENTITIES_WITH_TYPEFLAGS}"
fi

if ! test -f "${F_CZECHNAMES}" || test `stat -c %Y "${F_CZECHNAMES}"` -lt `stat -c %Y "${F_ENTITIES_WITH_TYPEFLAGS}"`; then
  python3 czechnames/namegen.py -o "${F_TMP_CZECHNAMES}" "${F_ENTITIES_WITH_TYPEFLAGS}" >"${F_TMP_CZECHNAMES}.log" 2>"${F_TMP_CZECHNAMES}.err.log" #-x "${F_CZECHNAMES_INVALID}_gender" -X "${F_CZECHNAMES_INVALID}_inflection" "${F_ENTITIES_WITH_TYPEFLAGS}"
  mv "${F_TMP_CZECHNAMES}" "${F_CZECHNAMES}"

fi

rm -f "${F_TMP_ENTITIES_WITH_TYPEFLAGS}"

#=====================================================================
# vytvoreni seznamu klicu entit v KB, pridani fragmentu jmen a prijmeni entit a zajmen

if $LOWERCASE ; then
  python3 KB2namelist.py -l < "$KB" | tr -s ' ' > intext_lower
elif $URI ; then
  python3 KB2namelist.py -u < "$KB" > intext_uri
else
  python3 KB2namelist.py < "$KB" | tr -s ' ' > intext
fi

#=====================================================================
# uprava stoplistu (kapitalizace a razeni)

if ! $URI ; then
  python get_morphological_forms.py < CzechStoplist.txt | sort -u > stop_list.var
  cp stop_list.var stop_list.all
  sed -e 's/\b\(.\)/\u\1/g' < stop_list.var >> stop_list.all
  tr 'a-z' 'A-Z' < stop_list.var >> stop_list.all
  tr 'A-Z' 'a-z' < stop_list.var >> stop_list.all
  sort -u stop_list.all > stop_list.all.sorted
fi

#=====================================================================
# parsovanie confidence hodnot do samostatneho suboru
# redukcia duplicit, abecedne zoradenie entit
# odstranovani slov ze stop listu

if ! $URI ; then
  awk '{print $(NF)}' < "$KB" > KB_confidence
  intext_namelist_suffix=

  if $LOWERCASE
  then
     intext_namelist_suffix="_lower"
  fi

  python uniq_namelist.py -s "KB_confidence" < "intext${intext_namelist_suffix}" > "namelist${intext_namelist_suffix}"
else
  python uniq_namelist.py < intext_uri > namelist_uri
fi

#=====================================================================
# vytvoreni konecneho automatu
if $CEDAR
then
    makeAutomata ".ct"
fi

if $DARTS
then
    makeAutomata ".dct"
fi

#=====================================================================
# smazani pomocnych souboru

#rm -f names
#rm -f fragments
#rm -f intext intext_lower intext_uri
#rm -f stop_list.all stop_list.var stop_list.all.sorted
#rm -f namelist namelist_lower namelist_uri
#rm -f KB_confidence

