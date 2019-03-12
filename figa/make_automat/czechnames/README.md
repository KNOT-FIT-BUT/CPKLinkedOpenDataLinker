# namegen
Program pro generování tvarů jmen osob a lokací.

## Závislosti

Je nutné mít k dispozici Morfologický analyzátor pro češtinu ( [MA - odkaz na interní wiki](http://knot.fit.vutbr.cz/wiki/index.php/Morfologick%C3%BD_slovn%C3%Adk_a_morfologick%C3%BD_analyz%C3%A1tor_pro_%C4%8De%C5%A1tinu#Morfologick.C3.BD_analyz.C3.A1tor_pro_.C4.8De.C5.A1tinu) ). 

Cestu k analyzátoru (příkaz ke spuštění) lze nastavovat v konfiguračním souboru v sekci MA položka PATH_TO. 

## Nápověda
Nápovědu lze vyvolat zadáním chybných/žádných parametrů či například přímo pomocí:

	./namegen.py -h

## Příklad
Chceme vygenerovat  tvary jmen uložených v souboru example.txt a výsledek uložit do souboru gen.txt:

	./namegen.py -o gen.txt example.txt 

## Formát vstupu
Formát vstupního souboru je následující:

	název \t druh

Kde druh může být jeden z:

* F
	* Ženské jméno.
* M
	* Mužské jméno.
* L
	* Název lokace.

Také je možné druh vynechat. V tom případe namegen předpokládá, že se jedná o jméno osoby a odhadne, zda-li jde o ženské, či mužské.
	
Příklad:

	Anna Sychravová	F
	Michal Šušák	M
	Malý Javorový štít	L
	
## Gramatiky

Pro generování tvarů jmen používá gramatik, které jsou uloženy v:

	data/grammars

Z těchto gramatik například určuje části jména/názvu, které se mají ohýbat.
Více informací ke gramatikám lze získat ve zmiňované složce v souboru README.md.

Jaká z gramatik bude na konkrétní jméno použita je určeno dle druhu jména/názvu a mapování

	druh -> soubor s gramatikou
	
je uvedeno v konfiguračním souboru.
	
## Konfigurační soubor

Konfigurační soubor se nachází přímo v kořenovém adresáři a jeho název je:

	namegen_config.ini
	
Konfigurační soubor obsahuje i popis jednotlivých parametrů.