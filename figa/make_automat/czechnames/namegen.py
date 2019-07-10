#!/usr/bin/env python3
# encoding: utf-8
"""
namegen -- Generátor tvarů jmen.

namegen je program pro generování tvarů jmen osob a lokací.

:author:     Martin Dočekal
:contact:    xdocek09@stud.fit.vubtr.cz
"""

import sys
import os
import locale
import regex as re
from argparse import ArgumentParser
import traceback
from namegenPack import Errors
import logging
import namegenPack.Grammar
import namegenPack.morpho.MorphoAnalyzer
import namegenPack.morpho.MorphCategories
import configparser

from namegenPack.Name import *
from namegenPack.Filters import NamesFilter
from _ast import Try, Or
from namegenPack.Grammar import Token, Grammar
import time
import copy

outputFile = sys.stdout


class ConfigManagerInvalidException(Errors.ExceptionMessageCode):
    """
    Nevalidní konfigurace
    """
    pass

class ConfigManager(object):
    """
    Tato třída slouží pro načítání konfigurace z konfiguračního souboru.
    """
    
    sectionDefault="DEFAULT"
    sectionFilters="FILTERS"
    sectionDataFiles="DATA_FILES"
    sectionGrammar="GRAMMAR"
    sectionMorphoAnalyzer="MA"
    
    
    
    
    def __init__(self):
        """
        Inicializace config manažéru.
        """
        
        self.configParser = configparser.ConfigParser()
    
        
    def read(self, filesPaths):
        """
        Přečte hodnoty z konfiguračních souborů. Také je validuje a převede do jejich datových typů.
        
        :param filesPaths: list s cestami ke konfiguračním souborům.
        :returns: Konfigurace.
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """
        try:
            self.configParser.read(filesPaths)
        except configparser.ParsingError as e:
            raise ConfigManagerInvalidException(Errors.ErrorMessenger.CODE_INVALID_CONFIG, "Nevalidní konfigurační soubor: "+str(e))
                                       
        
        return self.__transformVals()
        
    def getAbsolutePath(self, path):
        return ("{}/".format(os.path.dirname(os.path.abspath(__file__))) if path[:1] == '.' else "") + path
        
    def __transformVals(self):
        """
        Převede hodnoty a validuje je.
        
        :returns: dict -- ve formátu jméno sekce jako klíč a k němu dict s hodnotami.
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """
        result={}

        result[self.sectionDefault]=self.__transformDefaults()
        result[self.sectionFilters]=self.__transformFilters()
        result[self.sectionDataFiles]=self.__transformDataFiles()
        result[self.sectionGrammar]=self.__transformGrammar()
        result[self.sectionMorphoAnalyzer]=self.__transformMorphoAnalyzer()
        
        
        return result
    
    def __transformDefaults(self):
        """
        Převede hodnoty pro DEFAULT a validuje je.
        
        :returns: dict -- ve formátu jméno prametru jako klíč a k němu hodnota parametru
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """
        
        result={
            "ALLOW_PRIORITY_FILTRATION":self.getAbsolutePath(self.configParser[self.sectionDefault]["ALLOW_PRIORITY_FILTRATION"])=="True"
            }
        
        #nastavení locale
        if self.configParser[self.sectionDefault]["LC_ALL"]:
            try:
                locale.setlocale(locale.LC_ALL, self.configParser[self.sectionDefault]["LC_ALL"])
            except:
                raise ConfigManagerInvalidException(
                            Errors.ErrorMessenger.CODE_INVALID_CONFIG, 
                            "Nevalidní konfigurační soubor. Nepodařilo se nastavit LC_ALL: "+self.configParser[self.sectionDefault]["LC_ALL"])
        return result
    
    
    def __transformFilters(self):
        """
        Převede hodnoty pro FILTERS a validuje je.
        
        :returns: dict -- ve formátu jméno prametru jako klíč a k němu hodnota parametru
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """
        result={"LANGUAGES":None, "REGEX_NAME":None, "ALLOWED_ALPHABETIC_CHARACTERS":None, "SCRIPT":None}
        
        if self.configParser[self.sectionFilters]["LANGUAGES"]:
            result["LANGUAGES"]=set(l for l in self.configParser[self.sectionFilters]["LANGUAGES"].split())
            if "UNKNOWN" in result["LANGUAGES"]:
                #chceme prázdný řetězec
                result["LANGUAGES"].remove("UNKNOWN")
                result["LANGUAGES"].add("")
            
        if self.configParser[self.sectionFilters]["REGEX_NAME"]:
            try:
                result["REGEX_NAME"]=re.compile(self.configParser[self.sectionFilters]["REGEX_NAME"])
            except re.error:
                #Nevalidní regex
                        
                raise ConfigManagerInvalidException(
                    Errors.ErrorMessenger.CODE_INVALID_CONFIG, 
                    "Nevalidní konfigurační soubor. Nevalidní regulární výraz v "+self.sectionFilters+" u REGEX_NAME.")
                
        if self.configParser[self.sectionFilters]["ALLOWED_ALPHABETIC_CHARACTERS"]:
            result["ALLOWED_ALPHABETIC_CHARACTERS"]=set(c for c in self.configParser[self.sectionFilters]["ALLOWED_ALPHABETIC_CHARACTERS"].split())
        
        if self.configParser[self.sectionFilters]["SCRIPT"]:
            result["SCRIPT"]=self.configParser[self.sectionFilters]["SCRIPT"]
            
        return result
    
    def __transformMorphoAnalyzer(self):
        """
        Převede hodnoty pro MA a validuje je.
        
        :returns: dict -- ve formátu jméno prametru jako klíč a k němu hodnota parametru
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """

        result={
            "PATH_TO":self.getAbsolutePath(self.configParser[self.sectionMorphoAnalyzer]["PATH_TO"])
            }

        return result
    
    def __transformGrammar(self):
        """
        Převede hodnoty pro GRAMMAR a validuje je.
        
        :returns: dict -- ve formátu jméno prametru jako klíč a k němu hodnota parametru
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """

        result={
            "TITLES":self._readTitles(self.getAbsolutePath(self.configParser[self.sectionGrammar]["TITLES"])),
            "PARSE_UNKNOWN_ANALYZE": True if self.configParser[self.sectionGrammar]["PARSE_UNKNOWN_ANALYZE"]=="True" else False,
            "PARSE_UNKNOWN_ANALYZE_TERMINAL_MATCH":set(),
            "TIMEOUT":None,
            }
        
        if result["PARSE_UNKNOWN_ANALYZE"]:

            for t in self.configParser[self.sectionGrammar]["PARSE_UNKNOWN_ANALYZE_TERMINAL_MATCH"].split():
                try:
                    result["PARSE_UNKNOWN_ANALYZE_TERMINAL_MATCH"].add(Terminal.Type(t))
                except ValueError:
                    #Nevalidní druh terminálu
                    
                    raise ConfigManagerInvalidException(
                        Errors.ErrorMessenger.CODE_INVALID_CONFIG, 
                        "Nevalidní konfigurační soubor. PARSE_UNKNOWN_ANALYZE_TERMINAL_MATCH: "+t)
        
        try:
            if self.configParser[self.sectionGrammar]["TIMEOUT"].upper()!="NONE":
                result["TIMEOUT"]=int(self.configParser[self.sectionGrammar]["TIMEOUT"])
                if result["TIMEOUT"]<=0:
                    raise ValueError
        except ValueError:
            #Nevalidní hodnota pro timeout.
                    
            raise ConfigManagerInvalidException(
                    Errors.ErrorMessenger.CODE_INVALID_CONFIG, 
                        "Nevalidní konfigurační soubor. "+self.sectionGrammar+"/TIMEOUT: "+self.configParser[self.sectionGrammar]["TIMEOUT"])
        return result
    
    def _readTitles(self, pathT):
        """
        Získá tituly ze souboru s tituly.
        
        :param pathT: Cesta k souboru
        :type pathT: str
        """
        titles=set()
        with open(pathT, "r") as titlesF:
            for line in titlesF:
                content=line.split("#",1)[0].strip()
                if content:
                    for t in content.split():
                        titles.add(t)
                    
        
        return titles
    
    def __transformDataFiles(self):
        """
        Převede hodnoty pro DATA_FILES a validuje je.
        
        :returns: dict -- ve formátu jméno prametru jako klíč a k němu hodnota parametru
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """

        result={
            "GRAMMAR_MALE":None,
            "GRAMMAR_FEMALE":None,
            "GRAMMAR_LOCATIONS":None,
            "GRAMMAR_EVENTS":None
            }
        self.__loadPathArguments(self.configParser[self.sectionDataFiles], result)

        return result
    
    def __loadPathArguments(self, parConf, result):
        """
        Načtení argumentů obsahujícíh cesty.

        :param parConf: Sekce konfiguračního souboru v němž hledáme naše hodnoty.
        :type parConf: dict
        :param result: Zde se budou načítat cesty. Názvy klíčů musí odpovídat názvům argumentů.
        :type result: dict
        :raise ConfigManagerInvalidException: Pokud je konfigurační soubor nevalidní.
        """
        
        for k in result.keys():
            if parConf[k]: 
                result[k]=self.__makePath(parConf[k])
            else:
                raise ConfigManagerInvalidException(Errors.ErrorMessenger.CODE_INVALID_CONFIG, "Nevalidní konfigurační soubor. Chybí "+self.sectionDataFiles+" -> "+k)


    def __makePath(self, pathX):
        """
        Převede cestu na bezpečný tvar.
        Absolutní cesty jsou ponechány, tak jak jsou. K relativním
        je připojena cesta ke skriptu.
        
        :param pathX: cesta
        :type pathX: str
        """
        if os.path.isabs(pathX):
            return pathX
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),pathX)
        

class ArgumentParserError(Exception): pass
class ExceptionsArgumentParser(ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)
    
class ArgumentsManager(object):
    """
    Arguments manager pro namegen.
    """
    
    @classmethod
    def parseArgs(cls):
        """
        Parsování argumentů.
        
        :param cls: arguments class
        :returns: Parsované argumenty.
        """
        
        parser = ExceptionsArgumentParser(description="namegen je program pro generování tvarů jmen osob a lokací.")
        
        parser.add_argument("-o", "--output", help="Výstupní soubor. Pokud není uvedeno vypisuje na stdout.", type=str, required=False)
        parser.add_argument("-ew", "--error-words", help="Cesta k souboru, kde budou uložena slova, která poskytnutý morfologický analyzátor nezná. Výsledek je v lntrf formátu s tím, že provádí odhad značko-pravidel pro ženská a mužská jména.", type=str)
        parser.add_argument("-gn", "--given-names", help="Cesta k souboru, kde budou uložena slova označená jako křestní. Výsledek je v lntrf formátu.", type=str)
        parser.add_argument("-sn", "--surnames", help="Cesta k souboru, kde budou uložena slova označená jako příjmení. Výsledek je v lntrf formátu.", type=str)
        parser.add_argument("-l", "--locations", help="Cesta k souboru, kde budou uložena slova označená jako lokace. Výsledek je v lntrf formátu.", type=str)
        parser.add_argument("-in", "--include-no-morphs", help="Vytiskne i názvy/jména, u kterých se nepodařilo získat tvary, mezi výsledky.", action='store_true')
        parser.add_argument("-w", "--whole", help="Na výstupu se budou vyskytovat pouze tvary jmen ve všech pádech.", action='store_true')
        parser.add_argument("-v", "--verbose", help="Vypisuje i příslušné derivace jmen/názvů.", action='store_true')
        parser.add_argument('input', nargs="?", help='Vstupní soubor se jmény. Pokud není uvedeno očekává vstup na stdin.', default=None)


        try:
            parsed=parser.parse_args()
            
        except ArgumentParserError as e:
            parser.print_help()
            print("\n"+str(e), file=sys.stderr, flush=True)
            Errors.ErrorMessenger.echoError(Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_INVALID_ARGUMENTS), Errors.ErrorMessenger.CODE_INVALID_ARGUMENTS)

        return parsed

def priorityDerivationFilter(aTokens):
    """
    Filtrování derivací na základě priorit terminálů.
    
    Příklad:
            1. derivace: Adam F    P:::M    Adam[k1gMnSc1]#G F[k1gNnSc1]#S ...
                Adam    1{p=0, c=1, t=G, g=M, r="^(?!^([sS]vatý|[sS]aint)$).*$", note=jG, n=S}
                F    1{t=S, c=1, p=0, note=jS, g=N, n=S}
            2. derivace (vítězná): Adam F    P:::M    Adam[k1gMnSc1]#G F#I ...
                Adam    1{p=0, c=1, t=G, g=M, r="^(?!^([sS]vatý|[sS]aint)$).*$", note=jG, n=S}
                F    ia{p=1, t=I}
        
            Díky prioritě p=1 u F ve druhé derivaci bude vybrána pouze tato derivace.

            Samotný výběr probíhá tak, že procházíme pomyslným stromem od kořena( první slovo) a postupně, jak procházíme úrovně,
            tak odstraňujeme větve, kde je menší priorita.
            Příklad (pouze priority):
                0 0 0 4
                2 0 0 0
                
                Bude vybrána druhá derivace, protože jsme první odstřihli již při prvním slově, tudiž vyšší priorita není brána v úvahu.
            
    :param aTokens: Derivace reprezentované pomocí analyzovaných tokenů.
    :type aTokens: List[List[AnalyzedToken]]
    :return: Indexy derivací pro odstranění.
    :rtype: List[int]
    """
    
    if len(aTokens)<=1:
        #není co filtrovat
        return []

    allIndexes=set(x for x in range(len(aTokens)))
    derivationsLeft=copy.copy(allIndexes)   # z tohoto setu budeme postupně odebírat

    
    for iW in range(len(aTokens[0])):     
        #pojďme najít maximální prioritu pro aktuální slovo    
        maxP=max(aTokens[derivIndex][iW].matchingTerminal.getAttribute(Terminal.Attribute.Type.PRIORITY).value for derivIndex in derivationsLeft)        
        
        #odfiltrujeme derivace, které nemají na aktuálním slově maximální prioritu
        derivationsLeft=set(derivIndex for derivIndex in derivationsLeft 
                            if aTokens[derivIndex][iW].matchingTerminal.getAttribute(Terminal.Attribute.Type.PRIORITY).value >=maxP)
        
        if len(derivationsLeft)<=1:
            break
    
    #Odfiltrovat se mají ty, které se nedostaly až na konec.
    return list(set(x for x in range(len(aTokens))) - derivationsLeft)



def main():
    """
    Vstupní bod programu.
    """
    try:
        logging.basicConfig(stream=sys.stderr,format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
        #zpracování argumentů
        args=ArgumentsManager.parseArgs()
        
        #načtení konfigurace
        configManager=ConfigManager()
        configAll=configManager.read(os.path.dirname(os.path.realpath(__file__))+'/namegen_config.ini')
        
        if configAll[configManager.sectionGrammar]["PARSE_UNKNOWN_ANALYZE"]:
            #nastavní druhů terminálů UNKNOWN_ANALYZE_TERMINAL_MATCH
            Terminal.UNKNOWN_ANALYZE_TERMINAL_MATCH=configAll[configManager.sectionGrammar]["PARSE_UNKNOWN_ANALYZE_TERMINAL_MATCH"]
        
        if configAll[configManager.sectionGrammar]["TITLES"]:
            #nastavíme řetězce, které se mají brát jako tituly
            namegenPack.Grammar.Lex.setTitles(configAll[configManager.sectionGrammar]["TITLES"])
        
        logging.info("načtení gramatik")
        #načtení gramatik
        try:
            grammarMale=namegenPack.Grammar.Grammar(configAll[configManager.sectionDataFiles]["GRAMMAR_MALE"],
                                                    configAll[configManager.sectionGrammar]["TIMEOUT"])
        except Errors.ExceptionMessageCode as e:
            raise Errors.ExceptionMessageCode(e.code, configAll[configManager.sectionDataFiles]["GRAMMAR_MALE"]+": "+e.message)
        
        try:
            grammarFemale=namegenPack.Grammar.Grammar(configAll[configManager.sectionDataFiles]["GRAMMAR_FEMALE"],
                                                    configAll[configManager.sectionGrammar]["TIMEOUT"])
        except Errors.ExceptionMessageCode as e:
            raise Errors.ExceptionMessageCode(e.code, configAll[configManager.sectionDataFiles]["GRAMMAR_FEMALE"]+": "+e.message)
        
        try:
            grammarLocations=namegenPack.Grammar.Grammar(configAll[configManager.sectionDataFiles]["GRAMMAR_LOCATIONS"],
                                                    configAll[configManager.sectionGrammar]["TIMEOUT"])
            
        except Errors.ExceptionMessageCode as e:
            raise Errors.ExceptionMessageCode(e.code, configAll[configManager.sectionDataFiles]["GRAMMAR_LOCATIONS"]+": "+e.message)
        
        try:
            grammarEvents=namegenPack.Grammar.Grammar(configAll[configManager.sectionDataFiles]["GRAMMAR_EVENTS"],
                                                    configAll[configManager.sectionGrammar]["TIMEOUT"])
            
        except Errors.ExceptionMessageCode as e:
            raise Errors.ExceptionMessageCode(e.code, configAll[configManager.sectionDataFiles]["GRAMMAR_EVENTS"]+": "+e.message)
        
        
        namesFilter=NamesFilter(configAll[configManager.sectionFilters]["LANGUAGES"],
                                configAll[configManager.sectionFilters]["REGEX_NAME"],
                                configAll[configManager.sectionFilters]["ALLOWED_ALPHABETIC_CHARACTERS"],
                                configAll[configManager.sectionFilters]["SCRIPT"])
        
        logging.info("\thotovo")
        logging.info("čtení jmen")
        #načtení jmen pro zpracování
        namesR=NameReader(args.input)
        logging.info("\thotovo")
        logging.info("analýza slov")
        
        #přiřazení morfologického analyzátoru
        #Tento analyzátor je nastaven tak, že z ma ignoruje všechny hovorové tvary.
        Word.setMorphoAnalyzer(
            namegenPack.morpho.MorphoAnalyzer.MorphoAnalyzerLibma(
                configAll[configManager.sectionMorphoAnalyzer]["PATH_TO"], 
                namesR.allWords(True, True, namesFilter)))
        
        logging.info("\thotovo")
        logging.info("generování tvarů")
        
        #čítače chyb
        errorsOthersCnt=0   
        errorsGrammerCnt=0  #není v gramatice
        errorsUnknownNameType=0  #není v gramatice
        errorsDuplicity=0   #více stejných jmen (včetně typu)
        errorsTimout=0 # U kolika jmen došlo k timeoutu při syntaktické analýze.

        errorWordsShouldSave=True if args.error_words is not None else False
        
        #slova ke, kterým nemůže vygenerovat tvary, zjistit POS... 
        #Klíč trojice (druh názvu (mužský, ženský, lokace),druhu slova ve jméně, dané slovo).
        #Hodnota množina jmen/názvů, kde se problém vyskytl.
        errorWords={}
        

        #slouží pro výpis křestních jmen, příjmení atd.
        wordRules={}
        writeWordsOfTypeTo={}
        if args.given_names is not None:
            #uživatel chce vypsat křestní jména do souboru
            wordRules[WordTypeMark.GIVEN_NAME]={}
            writeWordsOfTypeTo[WordTypeMark.GIVEN_NAME]=args.given_names
            
        if args.surnames is not None:
            #uživatel chce příjmení jména do souboru
            wordRules[WordTypeMark.SURNAME]={}
            writeWordsOfTypeTo[WordTypeMark.SURNAME]=args.surnames
            
        if args.locations is not None:
            #uživatel chce vypsat slova odpovídají lokacím do souboru
            wordRules[WordTypeMark.LOCATION]={}
            writeWordsOfTypeTo[WordTypeMark.LOCATION]=args.locations
            
        
         
        cnt=0   #projito jmen
        
        #nastaveni logování
        duplicityCheck=set()    #zde se budou ukládat jména pro zamezení duplicit
        
        grammarsForTypeGuesser={Name.Type.PersonGender.FEMALE: grammarFemale,Name.Type.PersonGender.MALE:grammarMale}
        
        
        #get output
        outF= open(args.output, "w") if args.output else sys.stdout
        
        startOfGenMorp = time.time()
        
        for name in namesR:
            #filtrování
            if not namesFilter(name):
                
                #Na základě uživatelských filtrů nemají být pro toto jméno
                #generovány tvary.
                
                if args.include_no_morphs:
                    #uživatel chce vytisknout i slova bez tvarů
                    print(name.printName(), file=outF) 

                continue
            
            morphsPrinted=False
            try:
                if name in duplicityCheck:
                    #již jsme jednou generovali
                    errorsDuplicity+=1
                    continue
                
                duplicityCheck.add(name)
                
                tokens=namegenPack.Grammar.Lex.getTokens(name)
                
                wNoInfo=set()
                for t in tokens:
                    if t.type==Token.Type.ANALYZE_UNKNOWN:
                        #Vybíráme ty tokeny, pro které není dostupná analýza a měla by být.
                        wNoInfo.add(t.word)
                
                if not configAll[configManager.sectionGrammar]["PARSE_UNKNOWN_ANALYZE"] or len(wNoInfo)==len(name.words):
                    #Nechceme vůbec používat grammatiku na názvy/jména, které obsahují slova, které morfologický analyzátor nezná nebo
                    #jméno/název je složen pouze z takovýchto slov.
                    
                    if len(wNoInfo)>0:
                        wordsMarks=name.simpleWordsTypesGuess(tokens)
                        print(str(name)+"\t"+Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_WORD_ANALYZE)+"\t"+(", ".join(str(w)+"#"+str(wordsMarks[name.words.index(w)]) for w in wNoInfo)), file=sys.stderr, flush=True)
    
                        for w in wNoInfo:
                            #přidáme informaci o druhu slova ve jméně a druh jména
                            try:
                                errorWords[(name.type,wordsMarks[name.words.index(w)], w)].add(name)
                            except KeyError:
                                errorWords[(name.type,wordsMarks[name.words.index(w)], w)]=set([name])
                        
                        if args.include_no_morphs:
                            #uživatel chce vytisknout i slova bez tvarů
                            print(name.printName(), file=outF)
                        #nemá cenu pokračovat, jdeme na další
                        continue
                
                    
                #zpochybnění odhad typu jména
                #protože guess type používá také gramatky
                #tak si případný výsledek uložím, abychom nemuseli dělat 2x stejnou práci
                tmpRes=name.guessType(grammarsForTypeGuesser, tokens)
                if tmpRes is not None:
                    rules, aTokens=tmpRes
                else:
                    rules, aTokens=None,None
                    
                if name.type == None:
                    #Nemáme dostatečnou informaci o druhu jména, jdeme dál.
                    print(Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_NAME_WITHOUT_TYPE).format(str(name)), file=sys.stderr, flush=True)
                    errorsUnknownNameType+=1
                    if args.include_no_morphs:
                        #uživatel chce vytisknout i slova bez tvarů
                        print(name.printName(), file=outF)
                    continue
                #Vybrání a zpracování gramatiky na základě druhu jména.
                #získáme aplikovatelná pravidla, ale hlavně analyzované tokeny, které mají v sobě informaci,
                #zda-li se má dané slovo ohýbat, či nikoliv a další
                
                
                
                if aTokens is None: #Nedostaly jsme aTokeny při určování druhu slova?
                    
                    #rules a aTokens může obsahovat více než jednu možnou derivaci
                    if name.type==Name.Type.MainType.LOCATION:
                        rules, aTokens=grammarLocations.analyse(tokens)
                    elif name.type==Name.Type.MainType.EVENTS:
                        rules, aTokens=grammarEvents.analyse(tokens)
                    elif name.type==Name.Type.PersonGender.MALE:
                        rules, aTokens=grammarMale.analyse(tokens)
                    elif name.type==Name.Type.PersonGender.FEMALE:
                        rules, aTokens=grammarFemale.analyse(tokens)
                    else:
                        #je cosi prohnilého ve stavu tohoto programu
                        raise Errors.ExceptionMessageCode(Errors.ErrorMessenger.CODE_ALL_VALUES_NOT_COVERED)

                completedMorphs=set()    #pro odstranění dualit používáme set
                noMorphsWords=set()
                missingCaseWords=set()
                wNoInfo=set()
                
                if configAll[configManager.sectionDefault]["ALLOW_PRIORITY_FILTRATION"]:
                    #filtr derivací na základě priorit terminálů
                    for r in sorted(priorityDerivationFilter(aTokens), reverse=True):    #musíme jít od konce, protože se při odstranění mění indexy
                        #odstranění derivací na základě priorit
                        del rules[r]
                        del aTokens[r]

                alreadyGenerated=set()  #mnozina ntic analyzovanych terminalu, ktere byly jiz generovany
                for ru, aT in zip(rules, aTokens):

                    aTTuple=tuple(aT)
                    if aTTuple in alreadyGenerated:
                        #Nechceme zpracovávat co jsme již zpracovávali.
                        #K jedné větě může existovat vícero derivací, proto je nutná tato kontrola.
                        continue

                    alreadyGenerated.add(aTTuple)
                    try:

                        if configAll[configManager.sectionGrammar]["PARSE_UNKNOWN_ANALYZE"]: 
                            
                            
                            for t in aT:
                                if t.token.type==Token.Type.ANALYZE_UNKNOWN:
                                    #zaznamenáme slova bez analýzy
                                    
                                    # přidáme informaci o druhu slova ve jméně a druh jména
                                    #používá se pro výpis chybových slov
                                    
                                    wNoInfo.add((t.token.word, t.matchingTerminal.getAttribute(namegenPack.Grammar.Terminal.Attribute.Type.WORD_TYPE).value))
                                    try:
                                        errorWords[(name.type, 
                                            t.matchingTerminal.getAttribute(namegenPack.Grammar.Terminal.Attribute.Type.WORD_TYPE).value, 
                                            t.token.word)].add(name)
                                    except KeyError:
                                        errorWords[(name.type,
                                            t.matchingTerminal.getAttribute(namegenPack.Grammar.Terminal.Attribute.Type.WORD_TYPE).value,
                                            t.token.word)] = set([name])
                                        
                            
                        #Získáme tvary a pokud budou pro nějaké slovo problémy, při získání tvarů,
                        #tak si necháme uložit korespondující token ke slovo do množiny missingCaseWords (společně s problémovým pádem).
                        morphs=name.genMorphs(aT, missingCaseWords)
                        if args.whole and len(morphs)<len(Case):
                            #Uživatel chce tisknout pouze pokud máme tvary pro všechny pády.
                            continue
                        resAdd=str(name)+"\t"+str(name.language)+"\t"+str(name.type)+"\t"+("|".join(morphs))
                        if len(name.additionalInfo)>0:
                            resAdd+="\t"+("\t".join(name.additionalInfo))
                        completedMorphs.add(resAdd)
                        if args.verbose:
                            logging.info(str(name)+"\tDerivace:")
                            for r in ru:
                                logging.info("\t\t"+str(r))
                            logging.info("\tTerminály:")
                            for a in aT:
                                if a.token.word is not None:
                                    logging.info("\t\t"+str(a.token.word)+"\t"+str(a.matchingTerminal))
                                
                            
                            

                    except Word.WordNoMorphsException as e:
                        #chyba při generování tvarů slova
                        #odchytáváme již zde, jeikož pro jedno slovo může být více alternativ
                        for x in aT:
                            #hledáme AnalyzedToken pro naše problémové slovo, abychom mohli ke slovu
                            #přidat i odhadnutý druh slova ve jméně (křestní, příjmení, ...)
                            if x.token.word==e.word:
                                noMorphsWords.add((x.matchingTerminal,e.word))
                                break
                            
                if len(wNoInfo)>0:
                    #vypíšeme slova, kdy analýza selhala
                    print(str(name)+"\t"+Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_WORD_ANALYZE)+"\t"+(", ".join(str(w)+"#"+str(m) for w, m in wNoInfo)), file=sys.stderr, flush=True)
                if len(noMorphsWords)>0 or len(missingCaseWords)>0:
                    #chyba při generování tvarů jména
                    

                    if len(noMorphsWords)>0:
                        print(Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_NAME_NO_MORPHS_GENERATED).format(str(name),", ".join(str(w)+" "+str(m) for m,w in noMorphsWords)), file=sys.stderr, flush=True)
                         
                    for aTerm, c in missingCaseWords:
                        print(str(name)+"\t"+Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_WORD_MISSING_MORF_FOR_CASE)+"\t"+str(c.value)+"\t"+str(aTerm.token.word)+"\t"+str(aTerm.matchingTerminal), file=sys.stderr, flush=True)
                
                #vytiskneme
                for m in completedMorphs:
                    print(m, file=outF)
                    
                if len(completedMorphs)>0:
                    morphsPrinted=True
                
                #zjistíme, zda-li uživatel nechce vypsat nějaké typy jmen do souborů

                for wordType in wordRules:
                    #chceme získat včechny slova daného druhu a k nim příslušná pravidla

                    #sjednotíme všechny derivace
                    for aT in aTokens:
                        for w, rules in Name.getWordsOfType(wordType, aT):
                            try:
                                wordRules[wordType][str(w)]=wordRules[wordType][str(w)]|rules
                            except KeyError:
                                wordRules[wordType][str(w)]=rules

                
            except namegenPack.Grammar.Grammar.TimeoutException as e:
                #Při provádění syntaktické analýzy, nad aktuálním jménem, došlo k timeoutu.
                errorsTimout+=1
                print(e.message+"\t"+str(name)+"\t"+str(name.type), file=sys.stderr, flush=True)
                
            except (Word.WordException) as e:
                Word.WordCouldntGetInfoException
                if isinstance(e, Word.WordCouldntGetInfoException) and not configAll[configManager.sectionGrammar]["PARSE_UNKNOWN_ANALYZE"]: 
                    #jen v případě, kdy nemá být použita gramatika
                    print(str(name)+"\t"+e.message, file=sys.stderr, flush=True)
                    
                    wordsMarks=name.simpleWordsTypesGuess(tokens)
                    for i, w in enumerate(name.words):
                        if w == e.word:
                            try:
                                errorWords[(name.type,wordsMarks[i], e.word)].add(name)
                            except KeyError:
                                errorWords[(name.type,wordsMarks[i], e.word)]=set([name])
                            break
                    
            except namegenPack.Grammar.Grammar.NotInLanguage as e:
                errorsGrammerCnt+=1
                print(Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_NAME_IS_NOT_IN_LANGUAGE_GENERATED_WITH_GRAMMAR)+\
                          "\t"+str(name)+"\t"+str(name.type), file=sys.stderr, flush=True)

            except Errors.ExceptionMessageCode as e:
                #chyba při zpracování slova
                errorsOthersCnt+=1
                print(str(name)+"\t"+e.message, file=sys.stderr, flush=True)
                
            if args.include_no_morphs and not morphsPrinted:
                #uživatel chce vytisknout i slova bez tvarů
                print(name.printName(), file=outF)
            cnt+=1
            if cnt%100==0:
                logging.info("Projito jmen/názvů: "+str(cnt))
        
        endOfGenMorp = time.time()
        
        if args.output:
            #close the output file
            outF.close()
            
        logging.info("\thotovo")
        #vypíšeme druhy slov, pokud to uživatel chce
        
        for wordType, pathToWrite in writeWordsOfTypeTo.items():
            logging.info("\tVýpis slov typu: "+str(wordType))
            with open(pathToWrite, "w") as fileW:
                for w, rules in wordRules[wordType].items():
                    print(str(w)+"\t"+"j"+str(wordType)+"\t"+(" ".join(sorted(r.lntrf+"::" for r in rules))), file=fileW)
            logging.info("\thotovo")
            
                
        
        print("-------------------------", file=sys.stderr)
        print("Celkem jmen: "+ str(namesR.errorCnt+len(namesR.names)), file=sys.stderr)
        print("\tNenačtených jmen: "+ str(namesR.errorCnt), file=sys.stderr)
        print("\tDuplicitních jmen: "+ str(errorsDuplicity), file=sys.stderr)
        print("\tNačtených jmen/názvů celkem: ", len(namesR.names), file=sys.stderr)
        print("\tPrůměrný čas strávený nad generováním tvarů jednoho jména/názvu: ", 
              round((endOfGenMorp - startOfGenMorp)/len(namesR.names),3) if len(namesR.names)>0 else 0 , file=sys.stderr)
        print("\tPrůměrný čas strávený nad jednou syntaktickou analýzou napříč gramatikami:", 
              (grammarFemale.grammarEllapsedTime+grammarLocations.grammarEllapsedTime+grammarEvents.grammarEllapsedTime+grammarMale.grammarEllapsedTime)/(grammarFemale.grammarNumOfAnalyzes+grammarMale.grammarNumOfAnalyzes+grammarLocations.grammarNumOfAnalyzes+grammarEvents.grammarNumOfAnalyzes)
              if (grammarFemale.grammarNumOfAnalyzes+grammarMale.grammarNumOfAnalyzes+grammarLocations.grammarNumOfAnalyzes+grammarEvents.grammarNumOfAnalyzes)>0 else 0, file=sys.stderr)
        print("\t\t FEMALE", file=sys.stderr)
        print("\t\t\t Průměrný čas strávený nad jednou syntaktickou analýzou:", 
              grammarFemale.grammarEllapsedTime/grammarFemale.grammarNumOfAnalyzes if grammarFemale.grammarNumOfAnalyzes>0 else 0, file=sys.stderr)
        print("\t\t\t Počet analýz:", grammarFemale.grammarNumOfAnalyzes, file=sys.stderr)
        print("\t\t MALE", file=sys.stderr)
        print("\t\t\t Průměrný čas strávený nad jednou syntaktickou analýzou:", 
              grammarMale.grammarEllapsedTime/grammarMale.grammarNumOfAnalyzes if grammarMale.grammarNumOfAnalyzes>0 else 0, file=sys.stderr)
        print("\t\t\t Počet analýz:", grammarMale.grammarNumOfAnalyzes, file=sys.stderr)
        print("\t\t LOCATION", file=sys.stderr)
        print("\t\t\t Průměrný čas strávený nad jednou syntaktickou analýzou:", 
              grammarLocations.grammarEllapsedTime/grammarLocations.grammarNumOfAnalyzes if grammarLocations.grammarNumOfAnalyzes>0 else 0, file=sys.stderr)
        print("\t\t\t Počet analýz:", grammarLocations.grammarNumOfAnalyzes, file=sys.stderr)
        print("\t\t EVENTS", file=sys.stderr)
        print("\t\t\t Průměrný čas strávený nad jednou syntaktickou analýzou:", 
              grammarEvents.grammarEllapsedTime/grammarEvents.grammarNumOfAnalyzes if grammarEvents.grammarNumOfAnalyzes>0 else 0, file=sys.stderr)
        print("\t\t\t Počet analýz:", grammarEvents.grammarNumOfAnalyzes, file=sys.stderr)
        print("\tNeznámý druh jména:", errorsUnknownNameType, file=sys.stderr)
        print("\tNepokryto gramatikou:", errorsGrammerCnt, file=sys.stderr)
        print("\tPočet jmen, u kterých došlo k timeoutu při syntaktické analýze:", errorsTimout, file=sys.stderr)
        print("\tPočet slov, které poskytnutý morfologický analyzátor nezná:", len(set(w for (_, _, w), _ in errorWords.items())), file=sys.stderr)

        if errorWordsShouldSave:
            #save words with errors into a file
            with open(args.error_words, "w") as errWFile:
                for (nT, m, w), names in errorWords.items():#druh názvu (mužský, ženský, lokace),označení typu slova ve jméně(jméno, příjmení), společně se jménem
                    #u ženských a mužských jmen přidáme odhad lntrf značky
                    resultStr=str(w)+"\t"+"j"+str(m)
                    if m in {WordTypeMark.GIVEN_NAME, WordTypeMark.SURNAME}:
                        if nT == Name.Type.PersonGender.FEMALE:
                            resultStr+="\tk1gFnSc1::"
                        if nT == Name.Type.PersonGender.MALE:
                            resultStr+="\tk1gMnSc1::"
                    #přidáme jména/názvy kde se problém vyskytl
                    resultStr+="\t"+str(nT)+"\t@\t"+"\t".join(str(name)+("\t"+name.additionalInfo[0] if len(name.additionalInfo)>0 else "") for name in names)   #name.additionalInfo by mělo na první pozici obsahovat URL zdroje
                    print(resultStr, file=errWFile)
  

    except Errors.ExceptionMessageCode as e:
        Errors.ErrorMessenger.echoError(e.message, e.code)
    except IOError as e:
        Errors.ErrorMessenger.echoError(Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_COULDNT_WORK_WITH_FILE)+"\n"+str(e), 
                                 Errors.ErrorMessenger.CODE_COULDNT_WORK_WITH_FILE)

    except Exception as e: 
        print("--------------------", file=sys.stderr)
        print("Detail chyby:\n", file=sys.stderr)
        traceback.print_tb(e.__traceback__)
        
        print("--------------------", file=sys.stderr)
        print("Text: ", end='', file=sys.stderr)
        print(e, file=sys.stderr)
        print("--------------------", file=sys.stderr)
        Errors.ErrorMessenger.echoError(Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_UNKNOWN_ERROR), Errors.ErrorMessenger.CODE_UNKNOWN_ERROR)

    

if __name__ == "__main__":
    main()