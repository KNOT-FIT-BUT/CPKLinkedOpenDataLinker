# CPKSemanticEnrichment

## Závislosti
Pro správnou funkčnost je nutné doinstalovat následující závislosti:
* numpy
* python_dateutil
* sources
* pattern
* swig

Pro instalaci je možné použít nástroj pip (pip3). Například takto:

    pip install numpy

Dále je nutné mít nainstalovaný swig (http://www.swig.org). Pokud máte některou z linuxových distribucí je možné, že jej lze nainstalovat pomocí vašeho package manageru:

    sudo apt install swig

nebo

    sudo yum install swig

## KnowledgeBase

Nástroj pro svojí činnost vyžaduje českou KnowledgeBase (dále jako KB). KB je uložená ve formátu TSV (tab-separated value), kdy na každém jednom řádku jsou uložené informace o jedné entitě. Každá entita má svůj typ, pomocí typů je definováno rovněž pořadí sloupců v KB - definice typů a jejich sloupců je uložena v souboru `HEAD-KB`, který je vydáván společně s KB. Pokud je v některém sloupci více hodnot, pak jsou tyto hodnoty oddělovány znakem `|` (roura).

Některé sloupce mají všechny entity společné - jsou jimi například tyto:
* **`ID`** - jednoznačný identifikátor řádku KB
* **`TYPE`** - informace o typu entity (skrze soubor HEAD-KB tak lze díky pořadí sloupce vyhledat význam dané hodnoty)
* **`NAME`** - název dané entity (zkrácený o upřesňující popisky - např. *(okres Žďár nad Sázavou)*)
* **`DISAMBIGUATION NAME`** *(`ORIGINAL_WIKINAME`)* - úplný název dané entity (včetně původních upřesňujících popisků)
* **`ALIASES`** - obsahuje další názvy, na základě kterých má být entita rozpoznána
* **`REDIRECTS`** - stránky přesměrování, na základě kterých jsou entity rovněž rozpoznávány
* **`DESCRIPTION`** - první věta dané zdrojové stránky
* **`IMAGES`** - obrázky ze zdrojové stránky, které byly k dané entitě nalezeny
* **`WIKI BACKLINKS`**, **`WIKI HITS`**, **`WIKI PRIMARY SENSE`**, **`SCORE WIKI`**, **`SCORE METRICS`**, **`CONFIDENCE`** - metriky pro disambiguaci
* *...a další*

V KB jsou uloženy následující typy entit (každá z nich má své specifické sloupce, z nichž některé jsou uvedeny jako příklady pod daným typem entity):
* **`person`** - pro osoby:
  * **`GENDER`** - pohlaví osoby
  * **`DATE OF BIRTH`** - datum narození
  * **`PLACE OF BIRTH`** - místo narození
  * **`DATE OF DEATH`** - datum úmrtí
  * **`PLACE OF DEATH`** - místo úmrtí
  * *...a další*
* **`geo`** - pro grografické objekty (jako například města, státy, pohoří, řeky, ...):
  * **`LATITUDE`** - zeměpisná šířka
  * **`LONGITUDE`** - zeměpisná délka
  * **`ELEVATION`** - nadmořská výška
  * **`COUNTRY`** - země umístění
  * *...a další*
* **`organisation`** - pro organizace:
  * **`FOUNDED`** - datum založení
  * **`LOCATION`** - sídlo organizace
  * *...a další*
* **`event`** - pro události:
  * **`START DATE`** - začátek události
  * **`END DATE`** - konec události
  * *...a další*

## Příprava slovníků, nástrojů, ...
Celý proces přípravy je zjednodušen tak, že stačí spustit jediný skript, který zařídí vše potřebné:
[`./start.sh`](start.sh)

Tento skript zkompiluje potřebné nástroje, zároveň stáhne nejnovější KB (`KBstatsMetrics.all`) a z ní vytvoří slovníky. Pro tvorbu slovníků z české KB se používá více skriptů z adresáře [`figa/make_automat`](figa/make_automat). Ve složce [`figa/make_automat/czechnames/`](figa/make_automat/czechnames/) se nacházejí skripty pro generování alternatívních jmen entit. 
Tvorba slovníků pro NER i pro autocomplete je prováděna pomocí skriptů [`create_cedar.sh`](figa/make_automat/create_cedar.sh) a [`create_cedar_autocomplete.sh`](figa/make_automat/create_cedar_autocomplete.sh). Tyto skripty pracují se souborem `KBstatsMetrics.all`, z něhož získají seznam jmen, který se následně předloží nástroji `figa` (aktuální verze: figav1.0), který dané automaty vytvoří (vše je zahrnuto do inicializačního skriptu [`./start.sh`](start.sh)).

## Nástroj ner_cz.py

Nástroj na rozpoznávání a disambiguaci (anotaci) entit je implementovaný ve skriptu [`ner_cz.py`](ner_cz.py) (pro jeho činnost je potřeba provést kroky uvedené v předchozí kapitole). Skript [`ner_cz.py`](ner_cz.py) využívá ke svojí činnosti KB, která je nahraná ve sdílené paměti pomocí nástrojů z adresáře SharedKB (není třeba nic dalšího spouštět, vše je zahrnuto v inicializačním skriptu `./start.sh`), rovněž využívá nástroje `figa`, který pomocí několika slovníků dokáže v textu rozpoznávat entity. 

Nástroj pracuje s KB s přidanými sloupci, které obsahují statistická data z Wikipedie a předpočítané skóre pro disambiguaci.

```
 použití: ner_cz.py [-h] [-a | -s] [-d] [-f FILE]

 Nepovinné argumenty:
   -h, --help            vypíše nápovědu a skončí
   -a, --all             Vypíše všechny entity ze vstupu bez rozpoznání.
   -s, --score           Vypíše pro každou entitu v textu všechny její možné významy a ohodnocení každého z těchto významů.
   -d, --daemon-mode     "mód Daemon" (viz níže)
   -f FILE, --file FILE  Použije zadaný soubor jako vstup.
   -r, --remove-accent   Odstraní diakritiku ze vstupu.
   -l, --lowercase       Převod vstupu na malá písmena a použití
                         zvláštního automatu pouze s malými písmeny.
Je také možné vstup načítat ze standardního vstupu (možnost využití přesměrování).
```

### Výstup

Na standardní výstup nástroj vypisuje seznam nalezených entit v pořadí, v jakém se vyskytují ve vstupním textu. Každé jedné entitě patří jeden řádek; sloupce jsou odděleny znakem tabulátor. Řádky vstupu mají formát:

```
BEGIN_OFFSET    END_OFFSET      TYPE    TEXT    OTHER
```

`BEGIN_OFFSET` a `END_OFFSET` vyjadřují pozici začátku a konce entity v textu.

`TYPE` označuje typ entity: `kb` pro položku KB, `date` a `interval` pro datum a interval, `coref` pro koreferenci zájménem nebo částí jména osoby.

`TEXT` obsahuje textovou podobu entity tak, jak se vyskytla ve vstupním textu.

`OTHER` pro typy `kb` a `coref` má podobu seznamu odpovídajících čísel řádků v KB oddělených znakem středník (`;`). Pokud je zapnutá disambiguace, zvolený je pouze jeden řádek odpovídající nejpravděpodobnějšímu významu. Při použití skriptu s parametrem `-s` se zobrazí dvojice číslo řádku a ohodnocení entity, dvojice jsou od sebe odděleny středníkem. Pro typy `date` a `interval` obsahuje údaj v normalizovaném ISO formátu.

### Příklad použití a výstupu nástroje ner_cz.py
```
python ner_cz.py <<< "Prvním československým prezidentem se stal 14. listopadu 1918 Tomáš Garrigue Masaryk (opětovně zvolen v květnu v letech 1920, 1927, 1934), kterého po jeho abdikaci 14. prosince v roce 1935 vystřídal Edvard Beneš."
43      61      date    14. listopadu 1918      1918-11-14
62      84      kb      Tomáš Garrigue Masaryk  33550
120     124     date    1920    1920-00-00
126     130     date    1927    1927-00-00
132     136     date    1934    1934-00-00
184     188     date    1935    1935-00-00
199     211     kb      Edvard Beneš    245
```

### Popis činnosti
V prvním kole se pro jednotlivé odstavce ukládají informace o rozpoznaných entitách podle jejich typů. V druhém kole se tyto informace využívají pro lepší určení konkrétní entity.

U osob se pro výpočet skóre využívají informace o předešlých výskytech dané osoby v odstavci. Kromě toho se pracuje i s výskytem lokací v daném odstavci, kde se sleduje výskyt lokací, které jsou spojené s danou osobou, tedy místem její narození apod. Využívají se i datumy spojené s touto osobou a jejich výskyt v odstavci a taktéž zaměstnání dané osoby apod.

U ostatních entit je postup podobný. Sledují se informace z odstavce, které jsou s danou entitou spojené a pomáhají tak s větší jistotou vybrat správnou entitu.

Nástroj taktéž ropoznává jmenné koreference, koreference zájmen a datumy v textu.
