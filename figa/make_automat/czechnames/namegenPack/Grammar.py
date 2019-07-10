"""
Created on 17. 6. 2018

Modul pro práci s gramatikou (Bezkontextovou).

:author:     Martin Dočekal
:contact:    xdocek09@stud.fit.vubtr.cz
"""
from namegenPack import Errors
import regex as re
from typing import Set, Dict, List, Tuple
from namegenPack.morpho.MorphCategories import MorphCategory, Gender, Number,\
    MorphCategories, POS, StylisticFlag, Case, Note, Flag
from enum import Enum
from builtins import isinstance
from namegenPack.Word import Word, WordTypeMark
import itertools
import copy
import time

class Nonterminal(object):
    """
    Reprezentace parametrizovaného neterminálu.
    Používá se k vygenerování běžného neterminálu (stringu), který je použit
    pro analýzu pomocí gramatiky.
    """
    NONTERMINAL_REGEX=re.compile(r"^([^\s()]+)\s*(\(([^()]+)\))?$", re.IGNORECASE)
    
    def __init__(self, n):
        """
        Vytvoření neterminálu z řetězcové reprezentace.
        
        :param n: Neterminál reprezentovaný řetězcem.
        :type n: str
        """
        self.params={}
        self.name=None
        self.allParamsWithValue=True
        self._parse(n)
        
    def __str__(self):
        if len(self.params)>0:
            return "{}({})".format(self.name, ",".join([ p if v is None else p+"="+v for p,v in sorted(self.params.items())]))
        else:
            return self.name
        
    
    def __eq__(self, other):
        """
        Dva neterminály jsou si rovny, pokud mají stejný název.
        
        :param other: Druhý neterminál pro porovnání.
        :type other: Nonterminal
        """
        if isinstance(other, self.__class__):
            return self.name == other.name
        else:
            return False 
        
    def __hash__(self):
        return hash(self.name)
    
    def addDefault(self, defVal):
        """
        Přiřzení defaultních hodnot chybějícím parametrům.
        
        :param defVal: Defaultní hodnoty, které budeme přiřazovat.
        :type defVal: Dict[str,str]
        """
        self.params=dict([(p,v) for p,v in defVal.items() if v is not None]+list(self.params.items()))
        
    
    def generateLeft(self,v):
        """
        Vygeneruje neterminál pro dané hodnoty ve formátu vhodném pro levou stranu pravidla.
        
        :param v: Hodnoty, které budou přiřazeny parametrům neterminálu.
            Klíč je název parametru. Pokud dict obsahuje klíč, který neni
            v nonterminálu, tak se nic neděje, ale pokud neobsahuje klíč, který
            je v neterminálu (a daný parametr nema defualtní hodnotu), pak vyhodí vyjímku.
        :type v: Dict[str,str]
        :return: běžný neterminál
        :rtype: str
        :raise InvalidGrammarException: 
            Pokud v neobsahuje všechny potřebné parametry
        """

        if len(self.params)>0:
            resV={}
            for par, defV in self.params.items():
                if par in v:
                    #máme hodnotu
                    resV[par]=v[par]
                elif defV is None:
                    #máme alespoň výchozí hodnotu
                    resV[par]=defV
                else:
                    #nemáme defaultní hodnotu a ani předanou v argumentu metody
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_NO_PAR_VALUE, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_NO_PAR_VALUE).format(str(self)+" <- "+par))
            
            params=["{}={}".format(p,val) for p,val in sorted(resV.items())]
            return self.name if len(resV)==0 else "{}({})".format(self.name, ",".join(params))
        else:
            return self.name
        
    def _parse(self, n):    
        """
        Najde název a parametry (případně i jejich hodnoty) v daném neterminálu.
        Mimo to provádí validaci formátu neterminálu.
        Příklad:
            NEXT(x,y)    ->    Název: NEXT, Parametry: x,y
            NEXT(x=1,y)    ->    Název: NEXT, Parametry: x,y, Hodnoty: x=1
            NEXT    ->    Název: NEXT
        
        :param n: Daný neterminál.
        :type n: str
        :raise InvalidGrammarException: 
            Pokud je předhozena nevalidní podoba neterminálu.
        """

        #pojďmě získat název a případné paramety
        
        matchNamePar=self.NONTERMINAL_REGEX.match(n)
        
        if not matchNamePar:
            #zdá se, že neterminál je v nesprávném formátu
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX).format(n))
        #máme match
        #Příklad pro osvětlení čísel skupin:
        #    NEXT(x=1,y)
        #        Full match    NEXT(x=1,y)
        #        Group 1.    NEXT
        #        Group 2.    (x=1,y)
        #        Group 3.    x=1,y

        self.name=matchNamePar.group(1)
        
        if matchNamePar.group(3):
            #má parametry
            for pv in [x.split("=") for x in matchNamePar.group(3).split(",")]:
                if len(pv)>2:
                    #více než jedno rovnáse
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX).format(n))
                
                if pv[0] in self.params:
                    #2x stejný parametr
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX).format(n))
                if pv[0][0]=="$":
                    #špatně pojmenovaný parametr
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX).format(n))
                
                if len(pv)==2:
                    self.params[pv[0]]=pv[1]
                else:
                    self.allParamsWithValue=False
                    self.params[pv[0]]=None
        

    
class Terminal(object):
    """
    Reprezentace parametrizovaného terminálu.
    """
    
    #Množina druhů terminálů, kterým odpovídá token ANALYZE_UNKNOWN.
    UNKNOWN_ANALYZE_TERMINAL_MATCH=set()
    
    class Type(Enum):
        """
        Druh terminálu.
        """
        EOF= 0 #konec vstupu
        
        N= "1"    #podstatné jméno
        A= "2"    #přídavné jméno
        P= "3"    #zájméno
        C= "4"    #číslovka
        V= "5"    #sloveso
        D= "6"    #příslovce
        R= "7"    #předložka
        RM= "7m"    #předložka za níž se ohýbají slova (von, da, de)
        J= "8"    #spojka
        T= "9"    #částice
        I= "10"   #citoslovce
        ABBREVIATION= "a"  #zkratka

        DEGREE_TITLE= "t"   #titul
        ROMAN_NUMBER= "r"   #římská číslice
        NUMBER="n"          #číslovka (pouze z číslic) Příklady: 12., 12
        INITIAL_ABBREVIATION= "ia"    #Iniciálová zkratka.
        X= "x"    #neznámé

        
        @property
        def isPOSType(self):
            """
            Určuje zda-li se jedná o typ terminálu odpovídajícím slovnímu druhu + zkratka.
            
            :return: True odpovídá slovnímu druhu. False jinak.
            :rtype: bool
            """
            try:
                return self.isPOS
            except AttributeError:
                #ptáme se poprvé
                self.isPOS=self in self.POSTypes
                return self.isPOS
            
        def toPOS(self):
            """
            Provede konverzi do POS.
            Pokud nelze vrací None
            
            :return: Mluvnická kategorie.
            :rtype: POS
            """
            try:
                return self.toPOSMap[self]
            except KeyError:
                #lze převést pouze určité typy terminálu
                #a to pouze typy terminálu, které vyjadřují slovní druhy
                return None
        
    Type.POSTypes={Type.N, Type.A,Type.P,Type.C,Type.V,Type.D,Type.R,Type.RM,Type.J,Type.T, Type.I, Type.ABBREVIATION}
    """Typy, které jsou POS"""
    
    Type.toPOSMap={
                    Type.N: POS.NOUN,           #podstatné jméno
                    Type.A: POS.ADJECTIVE,      #přídavné jméno
                    Type.P: POS.PRONOUN,        #zájméno
                    Type.C: POS.NUMERAL,        #číslovka
                    Type.V: POS.VERB,           #sloveso
                    Type.D: POS.ADVERB,         #příslovce
                    Type.R: POS.PREPOSITION,    #předložka
                    Type.RM: POS.PREPOSITION_M,    #předložka za níž se ohýbají slova
                    Type.J: POS.CONJUNCTION,    #spojka
                    Type.T: POS.PARTICLE,       #částice
                    Type.I: POS.INTERJECTION,    #citoslovce
                    Type.ABBREVIATION: POS.ABBREVIATION    #zkratka
                    }
    """Zobrazení typu do POS."""
    
    class Attribute(object):
        """
        Terminálový atributy.
        """
        VOLUNTARY_ATTRIBUTE_SIGN="?"    #znak volitelného atributu
        
        class Type(Enum):
            """
            Druh atributu.
            """
            
            #Žádný název by neměl obsahovat znak ? na konci, jelikož určuje volitelný atribut.
            GENDER="g"  #rod slova musí být takový    (filtrovací atribut)
            NUMBER="n"  #mluvnická kategorie číslo. Číslo slova musí být takové. (filtrovací atribut)
            CASE="c"    #pád slova musí být takový    (filtrovací atribut)
            NOTE="note" #poznámka slova musí být taková    (filtrovací atribut)
            FLAGS="f"   #Flagy, které musí mít skupina z morfologické analýzy.    (Speciální atribut)
            WORD_TYPE="t"    #druh slova ve jméně Křestní, příjmení atd. (Informační atribut)
            MATCH_REGEX="r"    #Slovo samotné sedí na daný regulární výraz. (Speciální atribut)
            PRIORITY="p"    #Přenastavuje prioritu terminálu (výchozí 0). Ve fázi generování tvarů je možné filtrovat na základě priority. (Speciální atribut)
            #Pokud přidáte nový je třeba upravit Attribute.createFrom a isFiltering
            
            def __init__(self, *args):
                self._voluntary=False

            @property
            def voluntary(self):
                """
                Určuje zda tento typ atributu je voluntary.
                Tato vlastnost se používá při syntaktické analýze a generování tvarů. Pravidlo/tvar je
                použito pouze tehdy, když má tento typ nebo když ani jeden z ostatních pravidel/tvarů
                jej nemá.
                """
                return self._voluntary
                
            @voluntary.setter
            def voluntary(self, v):
                """
                Nastaví voluntary flag. Popis voluntary je v getteru.
                
                :param v: Má být voluntary nebo ne?
                    True znamená voluntary.
                :type v: bool
                """
                self._voluntary=v

            @property
            def isFiltering(self):
                """
                Určuje zda-li daný typ je filtrovacím (klade dodatečné restrikce).
                
                :return: True filtrovací. False jinak.
                :rtype: bool
                """

                return self in self.FILTERING_TYPES
            
        Type.FILTERING_TYPES={Type.GENDER, Type.NUMBER, Type.CASE, Type.NOTE}
        """Filtrovací atributy. POZOR filtrovací atributy musí mít value typu MorphCategory!"""
        
        def __init__(self, attrType, val):
            """
            Vytvoří atribut terminálu.
            
            :param attrType: Druh attributu.
            :type attrType: self.Type
            :param val: Hodnota atributu.
            :raise InvalidGrammarException: Při nevalidní hodnotě atributu.
            """
            
            self._type=attrType
            if self.type.isFiltering :
                #u filtrovacích atributů musí být hodnota typu MorphCategory
                if self._type==self.Type.FLAGS:
                    #je možných více hodnot
                    for f in val:
                        if not isinstance(f, MorphCategory):
                            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)
                else:
                    if not isinstance(val, MorphCategory):
                        raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)
            self._val=val
            
        @classmethod
        def createFrom(cls, s):
            """
            Vytvoří atribut z řetězce.
            
            :param s: Řetezec reprezentující atribut a jeho hodnotu
                Příklad: "g=M"
            :type s: str
            :raise InvalidGrammarException: Při nevalidní hodnotě atributu.
            """
            
            aT, aV= s.strip().split("=", 1)

            try:
                vol=False;
                if aT[-1]==cls.VOLUNTARY_ATTRIBUTE_SIGN:
                    #volitelný atribut
                    vol=True
                    aT=aT[:-1]

                t=cls.Type(aT)
                
                t.voluntary=vol
                
            except ValueError:
                #neplatný argumentu
                
                raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_ARGUMENT, \
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_ARGUMENT).format(s))
            v=None
            
            #vytvoříme hodnotu atributu
            if cls.Type.GENDER==t:
                v=Gender.fromLntrf(aV)
            elif cls.Type.NUMBER==t:
                v=Number.fromLntrf(aV)
            elif cls.Type.CASE==t:
                v=Case.fromLntrf(aV)
            elif cls.Type.NOTE==t:
                v=Note.fromLntrf(aV)
            elif cls.Type.FLAGS==t:
                if aV[0]=='"' and aV[-1]=='"':
                    aV=aV[1:-1]  #[1:-1] odstraňujeme " ze začátku a konce
                v=frozenset(Flag(x.strip()) for x in aV.split(",")) 
            elif cls.Type.MATCH_REGEX==t:
                try:
                    v=re.compile(aV[1:-1])  #[1:-1] odstraňujeme " ze začátku a konce
                except re.error:
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_ARGUMENT, \
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_ARGUMENT).format(s))
            elif cls.Type.PRIORITY==t:
                try:
                    v=int(aV)
                    if v<0:
                        #negativní hodnoty nejsou povoleny
                        raise ValueError()
                except ValueError:
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_ARGUMENT, \
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_ARGUMENT).format(s))
            else:
                v=WordTypeMark(aV)
            
            return cls(t,v)
        
        @property
        def type(self):
            return self._type
        
        @property
        def value(self):
            """
            :return: Hodnota attributu.
            """
            return self._val
        
        @property
        def valueRepresentation(self):
            """
            :return: Reprezentace hodnoty attributu.
            """
            return self._val if self.type!=self.Type.MATCH_REGEX else "\""+self._val.pattern+"\""
            
        
        def __str__(self):
            return str(self._type.value)+"="+str(self.valueRepresentation)
                        
        def __hash__(self):
            return hash((self._type, self.valueRepresentation))
        
        def __eq__(self, other):
            if self.__class__ is other.__class__:
                return self._type==other._type and self.valueRepresentation==other.valueRepresentation
            
            return False
        
    
    def __init__(self, terminalType, attr=set(), morph=True):
        """
        Vytvoření terminálu.
        Pokud není předán atribut s typem slova ve jméně, tak je automaticky přidán
        attribut s hodnotou WordTypeMark.UNKNOWN
        
        :param terminalType: Druh terminálu.
        :type terminalType: Type
        :param attr: Attributy terminálu. Určují dodatečné podmínky/informace na vstupní slovo.
                Musí vždy obsahovat atribut daného druhu pouze jedenkrát. Jinak může způsobit nedefinované chování
                u nějakých metod.
        :type attr: Attribute
        :param morph: True terminál semá ohýbat. False terminál je neohebný.
        :type morph: bool

        """
        
        self._type=terminalType
        self.morph=morph
        
        #zjistíme, zda-li byl předán word type mark
        if not any(a.type==self.Attribute.Type.WORD_TYPE for a in attr):
            #nebyl, přidáme neznámý
            attr=attr|set([self.Attribute(self.Attribute.Type.WORD_TYPE, WordTypeMark.UNKNOWN)])
            
        #zjistíme jestli byla přepsána defaultní priorita
        if not any(a.type==self.Attribute.Type.PRIORITY for a in attr):
            #nebyla, přidáme defaultní
            attr=attr|set([self.Attribute(self.Attribute.Type.PRIORITY, 0)])
        
        self._attributes=frozenset(attr)
        
        #pojďme zjistit hodnoty filtrovacích atributů
        self._fillteringAttrVal=set(a.value for a in self._attributes if a.type.isFiltering)
        self._fillteringAttrValWithoutVoluntary=set(a.value for a in self._attributes if a.type.isFiltering and not a.type.voluntary)
        
        if len(self._fillteringAttrVal)-len(self._fillteringAttrValWithoutVoluntary)>1:
            #dovolujeme pouze 1 volitelny atribut
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_MULTIPLE_VAL_ATTRIBUTES, \
                Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_MULTIPLE_VAL_ATTRIBUTES))
            
        self._hasVoluntaryAttribut=len(self._fillteringAttrVal)!=len(self._fillteringAttrValWithoutVoluntary)

        #cache pro zrychlení tokenMatch
        self._matchCache={}
        
    def getAttribute(self, t):
        """
        Vrací atribut daného druhu.
        
        :param t: druh attributu
        :type t: self.Attribute.Type
        :return: Atribut daného druhu a None, pokud takový atribut nemá.
        :rtype: self.Attribute | None
        """
        
        for a in self._attributes:
            if a.type==t:
                return a
        
        return None
    
    @property
    def type(self):
        """
        Druh terminálu.
        
        :rtype: self.Type
        """
        return self._type
        
    @property
    def fillteringAttrValues(self):
        """
        Získání všech hodnot attributů, které kladou dodatečné podmínky (např. rod musí být mužský).
        Všechny takové attributy mají value typu MorphCategory.
        Nevybírá informační atributy.
        
        :return: Hodnoty filtrovacích atributů, které má tento terminál.
        :rtype: Set[MorphCategory]
        """
    
        return self._fillteringAttrVal
    
    @property
    def hasVoluntaryAttr(self):
        """
        Určuje zda terminál má nějaké volitelný atribut.
        """
        return self._hasVoluntaryAttribut
    
    @property
    def fillteringAttrValuesWithoutVoluntary(self):
        """
        Získání všech hodnot nevolitelných attributů, které kladou dodatečné podmínky (např. rod musí být mužský).
        Všechny takové attributy mají value typu MorphCategory.
        Nevybírá informační atributy.
        
        :return: Hodnoty filtrovacích atributů, které má tento terminál a nejsou volitelné.
        :rtype: Set[MorphCategory]
        """
    
        return self._fillteringAttrValWithoutVoluntary
    
    def tokenMatch(self, t):
        """
        Určuje zda daný token odpovídá tomuto terminálu.
        
        :param t: Token pro kontrolu.
        :type t: Token
        :return: Vrací True, pokud odpovídá. Jinak false.
        :rtype: bool
        :raise WordCouldntGetInfoException: Problém při analýze slova.
        """
        
        try:
            return self._matchCache[t]
        except KeyError:
            #zatím není v cache
            res= self.tokenMatchWithoutCache(t)
            self._matchCache[t]=res
            return res
        
        
    def tokenMatchWithoutCache(self, t):
        """
        Stejně jako tokenMatch určuje zda daný token odpovídá tomuto terminálu, ale bez použití cache
        
        :param t: Token pro kontrolu.
        :type t: Token
        :return: Vrací True, pokud odpovídá. Jinak false.
        :rtype: bool
        :raise WordCouldntGetInfoException: Problém při analýze slova.
        """
        
        
        mr=self.getAttribute(self.Attribute.Type.MATCH_REGEX)
        if mr is not None and not mr.value.match(str(t.word)):
            #kontrola na regex match neprošla
            return False
        
        if t.type==Token.Type.ANALYZE_UNKNOWN and self.type in self.UNKNOWN_ANALYZE_TERMINAL_MATCH:
            #tento druh tokenu sedí na každý termínal druhu z self.UNKNOWN_ANALYZE_TERMINAL_MATCH
            return True
            
        #Zjistíme zda-li se jedná o token, který potenciálně potřebuje analyzátor.
        
        if t.type in Lex.TOKEN_TYPES_THAT_NEEDS_MA:
            #potřebujeme analýzu
            #Musíme zjistit jaký druh terminálu máme
            if self._type.isPOSType:
                groupFlags=self.getAttribute(self.Attribute.Type.FLAGS)
                groupFlags= set() if groupFlags is None else groupFlags.value
                #jedná se o typ terminálu používající analyzátor
                pos=t.word.info.getAllForCategory(MorphCategories.POS, self.fillteringAttrValues, 
                                                  set(), groupFlags)
                
                #máme všechny možné slovní druhy, které prošly atributovým filtrem 
                if len(pos)==0 and self.hasVoluntaryAttr:
                    
                    #zkusme štěstí ještě pro variantu bez volitelných
                    pos=t.word.info.getAllForCategory(MorphCategories.POS, self.fillteringAttrValuesWithoutVoluntary, 
                                                  set(), groupFlags)
                    
                    return self._type.toPOS() in pos
                
                return self._type.toPOS() in pos
            else:
                #pro tento terminál se nepoužívá analyzátor
                
                return t.type.value==self._type.value
        else:
            #Jedná se o jednoduchý token bez nutnosti morfologické analýzy.
            return t.type.value==self._type.value   #V tomto případě požívá terminál a token stejné hodnoty u typů
            
            

    def __str__(self):

        s=str(self._type.value) if self.morph else Grammar.NON_GEN_MORPH_SIGN+str(self._type.value)
        if self._attributes:
            s+="{"+", ".join( str(a) for a in self._attributes )+"}"
        return s
    
    def __hash__(self):
        return hash((self._type,self._attributes))
        
    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self._type==other._type and self._attributes==other._attributes
        
        return False
class Token(object):
    """
    Token, který je získán při lexikální analýze.
    """
    
    class Type(Enum):
        """
        Druh tokenu
        """
        ANALYZE=1   #komplexní typ určený pouze morfologickou analýzou slova
        ANALYZE_UNKNOWN=2   #Přestože by měl mít token analýzu, tak se ji nepodařilo získat.
        NUMBER=Terminal.Type.NUMBER.value          #číslice (pouze z číslovek) Příklady: 12., 12
        ROMAN_NUMBER= Terminal.Type.ROMAN_NUMBER.value   #římská číslice Je třeba zohlednit i analýzu kvůli shodě s předložkou V
        DEGREE_TITLE= Terminal.Type.DEGREE_TITLE.value  #titul
        INITIAL_ABBREVIATION= Terminal.Type.INITIAL_ABBREVIATION.value   #Iniciálová zkratka. Je třeba zohlednit i analýzu kvůli shodě s některými předložkami.
        EOF= Terminal.Type.EOF.value #konec vstupu
        X= Terminal.Type.X.value    #neznámé
        #Pokud zde budete něco měnit je třeba provést úpravy v Terminal.tokenMatch.

        def __str__(self):
            return str(self.value)
                
        def __hash__(self):
            return hash(self.value)
        
        def __eq__(self, other):
            if self.__class__ is other.__class__:
                return self.value==other.value
            
            return False
    
    def __init__(self, word:Word, tokenType):
        """
        Vytvoření tokenu.
        
        :param word: Slovo ze, kterého token vznikl.
        :type word: namegenPack.Name.Word
        :param tokenType: Druh tokenu.
        :type tokenType: self.Type
        """
        self._word=word
        self._type=tokenType
        
    @property
    def word(self):
        """
        Slovo ze vstupu, které má přiřazeno tento token.
        """
        
        return self._word;
    
    @property
    def type(self):
        """
        Druh tokenu.
        
        :rtype: Type 
        """
        return self._type
    
    @type.setter
    def type(self, t):
        """
        Nastav druh tokenu.

        :param t: Nový druh.
        :type t: Type
        """
        
        self._type=t
    
    def __str__(self):
        return str(self._type)+"("+str(self._word)+")"
    
    def __hash__(self):
        return hash((self._type,self._word))
        
    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self._type==other._type and self._word==other._word
        
        return False

class Lex(object):
    """
    Lexikální analyzátor pro jména.
    """
    __TITLES=set()
    """Banka titulů je načtena na začátku z konfiguračního souboru. Pro přiřazení použijte
    metodu setTitles"""
    
    __TITLES_PREFIXES=set()
    """Banka prefixů titulů. Příklady titulových prefixů pro titul  Ing.arch.:
        Ing."""

    ROMAN_NUMBER_REGEX=re.compile(r"^((X{1,3}(IX|IV|V?I{0,3}))|((IX|IV|I{1,3}|VI{0,3})))\.?$", re.IGNORECASE)
    NUMBER_REGEX=re.compile(r"^[0-9]+\.?$", re.IGNORECASE)
    
    TOKEN_TYPES_THAT_NEEDS_MA={Token.Type.ANALYZE, Token.Type.ROMAN_NUMBER, Token.Type.INITIAL_ABBREVIATION}
    
    @classmethod
    def setTitles(cls, titles:Set[str]):
        """
        Nastaví řetězce, které mají být brány za tituly.
        Zabezpečuje, aby byly brány i různé varianty u titulů typu:
            Ing.arch.
            Varianty: Ing.arch.    Ing. arch.
        
        :param titles: Množina titulů.
        :type titles: Set[str]
        """
        cls.__TITLES=titles
        
        #Přidáme i všechny prefixy, tak abysme později lépe detekovali získanou část titulu.
        #Příklady titulových prefixů pro titul  Ing.arch.:
        #Ing.
        
        for t in titles:
            
            pref=""
            for i,c in enumerate(t):
                pref+=c
                if c == "." and i!=len(t)-1:    #i!=len(t)-1 poslední ne
                    cls.__TITLES_PREFIXES.add(pref)

        
        
        
    @classmethod
    def getTokens(cls, name):
        """
        Získání tokenů pro sémantický analyzátor.

        :param name: Jméno pro analýzu
        :type name: Name
        :return: List tokenů pro dané jméno.
        :rtype: [str]
        """
        tokens=[]

        wCnt=0
        while wCnt<len(name):
            
            #prvně zjistíme tituly
            wT=cls.isTitle(name, wCnt)
            for _ in range(wT):
                #zjistíme všechna slova, která tvoří titul
                #Návratové hodnoty isTitle
                #    0 na této pozici se nenacházi titul
                #    1 titul je tvořen aktuálním slovem
                #    2    titul tvoří více slov
                tokens.append(Token(name[wCnt], Token.Type.DEGREE_TITLE)) 
                wCnt+=1
            if wT>0:
                #našli jsme titul
                #můžeme začít dalším
                continue
            
            w=name[wCnt]
            wCnt+=1
            
            if cls.ROMAN_NUMBER_REGEX.match(str(w)):
                #římská číslovka
                token=Token(w, Token.Type.ROMAN_NUMBER)
            elif cls.NUMBER_REGEX.match(str(w)):
                #číslovka z číslic, volitelně zakončená tečkou
                token=Token(w, Token.Type.NUMBER)
            elif (w[-1] == "." and len(w)==2 and not str.isdigit(w[0])) or (len(w)==1 and str(w).isupper()):
                #Jedná se o slovo, které má jedno písmeno (tečku nepočítáme).
                #Slovo má na konci tečku nebo nemá a pak je písmeno velké.
                #slovo neobsahuje číslovku.
                # =>
                #předpokládáme iniciálovou zkratku
                token=Token(w, Token.Type.INITIAL_ABBREVIATION)
            else:
                #ostatní
                token=Token(w, Token.Type.ANALYZE)
                
                
            #podíváme se, zdali máme analýzu tam, kde ji potřebujeme
            if token.type in cls.TOKEN_TYPES_THAT_NEEDS_MA:
                try:
                    _=token.word.info
                    #analýzu máme
                except Word.WordCouldntGetInfoException:
                    #bohužel analýza není, musíme změnit druh tokenu
                    token.type=Token.Type.ANALYZE_UNKNOWN
                
            tokens.append(token)
            
        
            
        tokens.append(Token(None, Token.Type.EOF)) 
    
        return tokens  
    
    @classmethod
    def isTitle(cls, name, pos):
        """
        Zjistí zdali se na aktuální pozici vyskytuje titul.
        
        :param name: Jméno, ve kterém hledáme.
        :type name: Name
        :param pos: Pozice slova, kde začínáme hledat titul.
        :type pos: int
        :return: Počet slov, které tvoří titul.
            Pokud 0 není zde titul
        :rtype: int
        """
        w=name[pos]
        
        pos+=1
        
        if str(w) in cls.__TITLES or (str(w) in cls.__TITLES_PREFIXES and pos<len(name)):
            #jedná se o titul nebo o jeho potencionální část
            if str(w) in cls.__TITLES_PREFIXES and pos<len(name):
                #může se jednat o část delšího titulu
                #musíme se tedy podívat dopředu
                
                #Bereme nejdelší možný titul, protože jinak bychom nemohli pracovat s tituly jako je
                #Ing.Arch. kvůli existenci titulu Ing.

                lookAhead=pos
                lastEvaluatedAsTitle=lookAhead if str(w) in cls.__TITLES else None
                actTitlePrefix=str(w)+str(name[lookAhead])
                
                lookAhead+=1
  
                while str(actTitlePrefix) in cls.__TITLES_PREFIXES and lookAhead<len(name):
                    if actTitlePrefix in cls.__TITLES:
                        lastEvaluatedAsTitle=lookAhead
                    actTitlePrefix+=str(name[lookAhead])

                    lookAhead+=1
                
                if actTitlePrefix in cls.__TITLES:
                    lastEvaluatedAsTitle=lookAhead-1
                        
                if lastEvaluatedAsTitle is not None:
                    #našli jsme nejdelší možný
                    #můsíme označit všechny slova, ze kterých se skládá jako tituly
                    return lastEvaluatedAsTitle-pos+2
                    
            elif str(w) in cls.__TITLES:
                #slovo je titulem nebo jeho částí
                return 1
            
        #nejedná se o titul
        return 0
                    
class AnalyzedToken(object):
    """
    Jedná se o analyzovaný token, který vzniká při syntaktické analýze.
    Přidává k danému tokenu informace získané analýzou. Informace jako je například zda se má
    dané slovo ohýbat, či nikoliv.
    """
    
    def __init__(self, token:Token, morph:bool=None, matchingTerminal:Terminal=None):
        """
        Pro běžný token vyrobí jaho analyzovanou variantu.

        :param token: Pro kterého budujeme analýzu.
        :type token: Token
        :param morph:Příznak zda se slovo, jenž je reprezentováno tímto tokenem, má ohýbat. True ohýbat. False neohýbat.
        :type morph: bool
        :param matchingTerminal: Získaný terminál při analýze, který odpovídal tokenu.
        :type matchingTerminal: Terminal
        """
        self._token=token
        self._morph=morph    #příznak zda-li se má dané slovo ohýbat
        self._matchingTerminal=matchingTerminal #Příslušný terminál odpovídající token (získaný při analýze).
    
    
    def __hash__(self):
        return hash((self._token,self._morph,self._matchingTerminal))
        
    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self._token==other._token and self._morph==other._morph and self._matchingTerminal==other._matchingTerminal
        
    @property
    def token(self):
        """
        :param token: Pro který máme tuto analýzu.
        :type token: Token
        """
        return self._token
    
    @property
    def morph(self):
        """
        Příznak zda se slovo, jenž je reprezentováno tímto tokenem, má ohýbat.
        
        :return: None neznáme. True ohýbat. False neohýbat.
        :rtype: bool
        """
        return self._morph
        
    @morph.setter
    def morph(self, val:bool):
        """
        Určení zda-li se má slovo, jenž je reprezentováno tímto tokenem, ohýbat.
        
        :param val: True ohýbat. False neohýbat.
        :type val: bool
        """
        self._morph=val
    
    @property
    def matchingTerminal(self)->Terminal:
        """
        Získaný terminál při analýze, který odpovídal tokenu.
        
        :return: Odpovídající terminál z gramatiky.
        :rtype: Terminal
        """
        
        return self._matchingTerminal
    
    @matchingTerminal.setter
    def matchingTerminal(self, t:Terminal):
        """
        Přiřazení terminálu.
        
        :param t: Odpovídající terminál.
        :type t: Terminal
        """
        
        self._matchingTerminal=t
    
    @property
    def morphCategories(self) -> Set[MorphCategory]:
        """
        Získání morfologických kategorií, které na základě analýzy má dané slovo patřící k tokenu mít.
        Vybere jen ty hodnoty, které v nějaké z kategorii zpřesňují odhad , tedy pokud analýza určí, že dané slovo
        může mít pouze hodnoty v kategorii DegreeOfComparison 1 a 2, tak tyto hodnoty vrátí. Kdyby mohlo slovo nabývat všech
        hodnot, tak je vůbec nevrací.

        Příklad: Analýzou jsme zjistili, že se může jednat pouze o podstatné jméno rodu mužského v jednotném čísle.

        Tyto dodatečné podmínky jsou přímo uzpůsobeny pro použití výsledku ke generování tvarů.
        
        :rtype: Set[MorphCategory]
        """
        
        #nejprve vložíme filtrovací atributy
        categories=self.matchingTerminal.fillteringAttrValues.copy()
        groupFlags=self.matchingTerminal.getAttribute(self.matchingTerminal.Attribute.Type.FLAGS)
        groupFlags= set() if groupFlags is None else groupFlags.value
        
        
        #můžeme získat další kategorie na základě morfologické analýzy
        if self.matchingTerminal.type.isPOSType:
            #pro práci s morfologickou analýzou musí byt POS type
            
            categories.add(self.matchingTerminal.type.toPOS()) #vložíme požadovaný slovní druh do filtru
            
            #nejprve zkusím s volitelnými atributy
            
            #jedná se o typ terminálu používající analyzátor
            morphsInfo = self._token.word.info.getAll(categories, set(), groupFlags)  # hovorové nechceme
            
            if len(morphsInfo)==0:
                # zkusme štěstí ještě pro variantu bez volitelných atributů
                categories=self.matchingTerminal.fillteringAttrValuesWithoutVoluntary.copy()
                categories.add(self.matchingTerminal.type.toPOS())
                
                morphsInfo = self._token.word.info.getAll(categories, set(), groupFlags)
                
            #Například pokud víme, že máme přídavné jméno rodu středního v jednotném čísle
            #a morf. analýza nám řekne, že přídavné jméno může být pouze prvního stupně, tak tuto informaci zařadíme
            #k filtrům
                
            for mCat, morphCategoryValues in morphsInfo.items():
                if mCat == MorphCategories.NOTE:
                    #nechceme použít, jelikož se jedná o nepovinný atribut
                    continue
                if len(next(iter(morphCategoryValues)).__class__)>len(morphCategoryValues):
                    #danou kategorii má cenu filtrovat jelikož analýza určila, že slovo nemá všechny
                    #hodnoty z této kategorie.
                    categories|=morphCategoryValues
   
        return categories

class InvalidGrammarException(Errors.ExceptionMessageCode):
    pass

    
class Rule(object):
    """
    Reprezentace pravidla pro gramatiku.
    """
    
    TERMINAL_REGEX=re.compile("^(.+?)(\{(.*)\})?$") #oddělení typu a attrbutů z terminálu
    
    def __init__(self, fromString, terminals=None, nonterminals=None, leftSide:str=None, rightSide=None):
        """
        Vytvoření pravidla z řetězce.
        formát pravidla: Neterminál -> Terminály a neterminály
        
        :param fromString: Pravidlo v podobě řetězce.
        :type fromString: str
        :param terminals: Zde bude ukládat nalezené terminály.
        :type terminals: set
        :param nonterminals: Zde bude ukládat nalezené neterminály.
        :type nonterminals: set
        :param leftSide: Pokud je zadáno, tak se ignoruje levá strana z fromString a použije se tato.
            Jedná se o jeden neterminál.
        :type leftSide: str
        :param rightSide:  Pokud je zadáno, tak se ignoruje pravá strana z fromString a použije se tato.
            Jedná se o jeden terminály či prázdný řetězec Grammar.EMPTY_STR. Neprovádí kontroly jako v případě kdy je hodnota brána z fromString.
        :type rightSide: List[Terminal|Grammar.EMPTY_STR]
        :raise InvalidGrammarException: 
             pokud je pravidlo v chybném formátu.
        """
        if leftSide is None or rightSide is None:
            try:
                self._leftSide, self._rightSide=fromString.split("->")
            except ValueError:
                #špatný formát pravidla
                raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE,
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+fromString)
                
        self._leftSide=self._parseSymbol(self._leftSide) if leftSide is None else leftSide
        if isinstance(self._leftSide, Terminal) or self._leftSide==Grammar.EMPTY_STR:
            #terminál nebo prázdný řetězec
            #ovšem v naší gramatice může být na levé straně pouze neterminál
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE,
                                          Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+fromString)
        
        #neterminál, vše je ok
        if nonterminals is not None:
            nonterminals.add(self._leftSide)

        if rightSide is None:
            self._rightSide=[x for x in self._rightSide.split()]
            #vytvoříme ze řetězců potřebné struktury a přidáváme nalezené (ne)terminály do množiny (ne)terminálů
            for i, x in enumerate(self._rightSide):
                try:
                    self.rightSide[i]=self._parseSymbol(x)
                    
                    if terminals is not None or nonterminals is not None:
                        if isinstance(self.rightSide[i], Terminal):
                            # terminál
                            if terminals is not None:
                                terminals.add(self.rightSide[i])
                        else:
                            #neterminál nebo prázdný řetězec
                            if self.rightSide[i]!=Grammar.EMPTY_STR:
                                #neterminál
                                if nonterminals is not None:
                                    nonterminals.add(self.rightSide[i])
                except InvalidGrammarException as e:
                    #došlo k potížím s aktuálním pravidlem
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE, 
                                                  Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+x+"\t"+fromString
                                                  +"\n\t"+e.message)
                except:
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE, 
                                                  Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+x+"\t"+fromString)
        else:
            self._rightSide=rightSide
            if terminals is not None or nonterminals is not None:
                for i, x in enumerate(self._rightSide):
                    if isinstance(self.rightSide[i], Terminal):
                        # terminál
                        if terminals is not None:
                            terminals.add(self.rightSide[i])
                    else:
                        #neterminál nebo prázdný řetězec
                        if self.rightSide[i]!=Grammar.EMPTY_STR:
                            #neterminál
                            if nonterminals is not None:
                                nonterminals.add(self.rightSide[i])
    @classmethod
    def _parseSymbol(cls, s):
        """
        Získá z řetězce symbol z gramatiky.
        
        :param s: Řetězec, který by měl obsahovat neterminál, terminál či symbol prázdného řetězce.
        :type s: str
        :return: Symbol v gramatice
        :raise InvalidGrammarException: 
             pokud je symbol nevalidní
        """
        x=s.strip()
        
        if x==Grammar.EMPTY_STR:
            #prázdný řetězec není třeba dále zpracovávat
            return x
            
        mGroups=cls.TERMINAL_REGEX.match(x)
        #máme naparsovaný terminál/neterminál
        #příklad: rn{g=M,t=G}
        #Group 1.    0-2    `rn`
        #Group 2.    2-11    `{g=M,t=G}`
        #Group 3.    3-10    `g=M,t=G`

        termType=None
        termMorph=True  #terminál je ohebný
        try:
            ts=mGroups.group(1)
            if ts[0]==Grammar.NON_GEN_MORPH_SIGN:
                termMorph=False
                ts=ts[1:]
            termType=Terminal.Type(ts)
        except ValueError:
            #neterminál, nemusíme nic měnit
            #stačí původní reprezentace
            return x
            
        
        #máme terminál
        attrs=set()
        attrTypes=set() #pro kontorolu opakujicich se typu
        if mGroups.group(3):
            #terminál má argumenty
            
            state="R"   #Read
            attribute=""
            
            #Budeme číst attributy oddělené ,
            #Pokud však narazíme na ", tak čárka nemusí být oddělovačem attributu
             
            for s in mGroups.group(3):
                if state=="R":
                    #Read
                    if s==",":
                        #máme potenciální atribut
                        ta=Terminal.Attribute.createFrom(attribute)
                        if ta.type in attrTypes:
                            #typ argumentu se opakuje
                            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_ARGUMENT_REPEAT, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_ARGUMENT_REPEAT).format(attribute))
                        attrTypes.add(ta.type)
                        attrs.add(ta)
                        attribute=""
                    elif s=='"':
                        state="Q"  #QUOTATION MARKS
                        attribute+=s
                    else:
                        attribute+=s
                elif "Q":
                    #QUOTATION MARKS
                    if s=='"':
                        state="R"
                        attribute+=s
                    elif s=="\\":
                        state="B" #BACKSLASH
                        attribute+=s
                    else:
                        attribute+=s
                else:
                    #BACKSLASH
                    state="Q"
                    if s=='"':
                        attribute=attribute[:-1]
                        attribute+=s
            
            if len(attribute)>0:
                #máme potenciální atribut
                ta=Terminal.Attribute.createFrom(attribute)
                
                if ta.type in attrTypes:
                    
                    #typ argumentu se opakuje
                    raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_ARGUMENT_REPEAT, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_ARGUMENT_REPEAT).format(attribute))
                
                attrTypes.add(ta.type)
                attrs.add(ta)
        
        return Terminal(termType, attrs, termMorph)
        
        
    def getSymbols(self):
        """
        Vrací všechny terminály a neterminály.
        
        :return: Množinu terminálů a neterminálů figurujících v pravidle.
        :rtype: set
        """
        
        return set(self._leftSide)+set(self._rightSide)
    
    @property
    def leftSide(self):
        """
        Levá strana pravidla.
        :return: Neterminál.
        :rtype: str
        """
        return self._leftSide
    
    @leftSide.setter
    def leftSide(self, value):
        """
        Nová levá strana pravidla.
        
        :param value:Nová hodnota na levé straně prvidla.
        :type value: string
        :return: Neterminál.
        :rtype: str
        """
        self._leftSide=value
    
    @property
    def rightSide(self):
        """
        Pravá strana pravidla.
        
        :return: Terminály a neterminály (epsilon) na právé straně pravidla.
        :rtype: list
        """
        return self._rightSide
    
    @rightSide.setter
    def rightSide(self, value): 
        """
        Nová pravá strana pravidla.
        
        :param value: Nová pravá strana.
        :type value: List()
        :return: Terminály a neterminály (epsilon) na právé straně pravidla.
        :rtype: list
        """
        self._rightSide=value
    
    
    def __str__(self):
        return self._leftSide+"->"+" ".join(str(x) for x in self._rightSide)
    
    def __repr(self):
        return str(self)
    
    def __hash__(self):
        return hash((self._leftSide, tuple(self._rightSide)))
        
    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self._leftSide==other._leftSide and self._rightSide==other._rightSide
            
        return False


class RulePrefixTree(object):
    """
    Prefixový strom vhodný pro získání skupin pravidel o stejných prefixech na pravé straně pravidla.
    
    Strom je tvořen dalšími stromy.
    """

    def __init__(self, rules:Set[Rule], level=0):
        """
        Inicializace prefixoveho stromu.
        
        :param rules: Pravidla pro zpracování
        :type rules: Set[Rule]
        :param level: Uroveň zanoření stromu.
        :type level: int
        """
        pref = {}
        for r in rules:
            if level >= len(r.rightSide):
                if None not in pref:
                    # listový
                    pref[None] = set()
                continue
            try:
                pref[r.rightSide[level]].add(r)
            except KeyError:
                pref[r.rightSide[level]] = set([r])
    
        self._rules = rules
        self._offsprings = {}
        for p, x in pref.items():
            if p is None:
                self._offsprings[p] = RulePrefixTree(x, level + 1)
            else:
                # zkusme najít další větvení
                move = 1
                toCompare = next(iter(x)).rightSide
                try:
                    while all(toCompare[level + move] == c.rightSide[level + move] for c in x):
                        # všichni začínají stejně a nevětví se tedy
                        # můžeme posunout délku prefixu
                        move += 1
                except IndexError:
                    # překročeno, už nemůžeme dál
                    pass
                    
                self._offsprings[tuple(toCompare[level:level + move])] = RulePrefixTree(x, level + move)

    @property
    def rules(self):
        """
        Všechny pravidla v tomto stromě.
        """
        return self._rules
    
    @property
    def offsprings(self):
        """
        Potomci v prefixovém stromě v podobě dict.
        
        Příklad
            1 2 3 4
            1 2 3
            1 2
            4 5
        
        Vrátí:
            (1,2):RulePrefixTree
            (4,5):RulePrefixTree
        :return: Dict kde key je nejdelší možný prefix (jako touple) 
            než dojde k větvení a value je prefixový strom (pro větvení).
        :rtype: Dict[Tuple,RulePrefixTree]
        """
        return self._offsprings


class RuleTemplate(object):
    """
    Reprezentace šablony pro generování pravidla.
    """
    
    
    TERMINAL_REGEX=re.compile("^(.+?)(\{(.*)\})?$") #oddělení typu a attrbutů z terminálu
    VARIABLE_REGEX=re.compile("\$([A-z])+")#hledání proměnncýh $x
    
    def __init__(self, fromString):
        """
        Vytvoření šablony pravidla z řetězce.
        formát pravidla: Neterminál -> Terminály a neterminály
        
        :param fromString: Šablona v podobě řetězce.
        :type fromString: str
        :raise InvalidGrammarException: 
             pokud je pravidlo v chybném formátu.
        """
        try:
            self._leftSide, self._rightSide=fromString.split("->")
            self._leftSide=self._leftSide.strip()
            self._rightSide=self._rightSide.strip()
            self._variables=set(self.VARIABLE_REGEX.findall(self._rightSide))
        except ValueError:
            #špatný formát šablony
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE,
                                          Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+fromString)
        
        
        if self.VARIABLE_REGEX.search(self._leftSide):
            #na levé straně se nesmí vyskytovat proměnné
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE,
                                          Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+fromString)
            
        self._leftSide=self._parseSymbol(self._leftSide)
        
        if isinstance(self._leftSide, str) or self._leftSide==Grammar.EMPTY_STR:
            #terminál nebo prázdný řetězec
            #ovšem v naší gramatice může být na levé straně pouze neterminál
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE,
                                          Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+fromString)
        
        #neterminál, vše je ok
        if not self._variables.issubset(set(self._leftSide.params)):
            #Některé proměnné jsou v pravidle na levé straně navíc.
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE, 
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+fromString)
        
        
        
        #vytvoříme ze řetězců potřebné struktury
        self.nontermsOnRightSide=[]
        
        self._rightSide=[x for x in self._rightSide.split()]

        for i, x in enumerate(self._rightSide):
            try:
                act=self._parseSymbol(x)
                if isinstance(act, Nonterminal):
                    self.nontermsOnRightSide.append(act)
                    #na pravá straně musí mít všechny parametry neterminálu přiřazenou hodnotu
                    if not act.allParamsWithValue:
                        raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_INVALID_SYNTAX).format(act))
                    
                self._rightSide[i]=act
            except InvalidGrammarException as e:
                #došlo k potížím s aktuálním pravidlem
                raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE, 
                                         Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+x+"\t"+fromString
                                         +"\n\t"+e.message)
            except:
                raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE, 
                                         Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_INVALID_FILE)+"\n\t"+x+"\t"+fromString)

    @classmethod
    def _parseSymbol(cls, s):
        """
        Získá z řetězce symbol z gramatiky.
        
        :param s: Řetězec, který by měl obsahovat neterminál, terminál či symbol prázdného řetězce.
        :type s: str
        :return: Symbol v gramatice
        :raise InvalidGrammarException: 
             pokud je symbol nevalidní
        """
        x=s.strip()
        
        if x==Grammar.EMPTY_STR:
            #prázdný řetězec není třeba dále zpracovávat
            return x
            
        mGroups=cls.TERMINAL_REGEX.match(x)
        #máme naparsovaný terminál/neterminál
        #příklad: rn{g=M,t=G}
        #Group 1.    0-2    `rn`
        #Group 2.    2-11    `{g=M,t=G}`
        #Group 3.    3-10    `g=M,t=G`

        try:
            ts=mGroups.group(1)
            if ts[0]==Grammar.NON_GEN_MORPH_SIGN:
                #pro urceni typu je treba odstranit
                ts=ts[1:]
            Terminal.Type(ts)
        except ValueError:
            #neterminál
            return Nonterminal(s)
        
        
        #máme terminál
        #stačí string
        return x
        
    
    def generate(self, v):
        """
        Vygeneruje string v podobě finálního pravidla.
        
        :param v: Hodnoty parametrů, použité pro generování
        :type v: Dict[str,str]
        :return: Vygenerované pravidlo
        :rtype: str
        """
        if len(self._leftSide.params)==0:
            #jednoduché pravidlo
            return str(self)
                
        #Máme všechny parametry?
        if v.keys()!=self._leftSide.params.keys():
            #nemáme
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_COULDNT_GENERATE_RULE, 
                                         Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_COULDNT_GENERATE_RULE).format(str(self)))
        
        
        
        s=self._leftSide.generateLeft(v)+"->"+" ".join(str(x) for x in self._rightSide)
        
        #přiřadíme hodnoty proměnným
        for p,pval in v.items():
            s=s.replace("$"+p, pval)
        return s
    
    @property
    def leftSide(self):
        """
        Levá strana pravidla.
        
        :return: Neterminál.
        :rtype: str
        """
        return self._leftSide
    
    @leftSide.setter
    def leftSide(self, value):
        """
        Nová levá strana pravidla.
        
        :param value:Nová hodnota na levé straně prvidla.
        :type value: string
        :return: Neterminál.
        :rtype: str
        """
        self._leftSide=value
    
    @property
    def rightSide(self):
        """
        Pravá strana pravidla.
        
        :return: Terminály a neterminály (epsilon) na právé straně pravidla.
        :rtype: list
        """
        return self._rightSide
    
    @rightSide.setter
    def rightSide(self, value): 
        """
        Nová pravá strana pravidla.
        
        :param value: Nová pravá strana.
        :type value: List()
        :return: Terminály a neterminály (epsilon) na právé straně pravidla.
        :rtype: list
        """
        self._rightSide=value
    
    
    
    def __str__(self):
        return str(self._leftSide)+"->"+" ".join(str(x) for x in self._rightSide)
    
    def __repr(self):
        return str(self)
    
    def __hash__(self):
            return hash((self._leftSide, tuple(self._rightSide)))
        
    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self._leftSide==other._leftSide and self._rightSide==other._rightSide
            
        return False

class Symbol(object):
        """
        Reprezentace symbolu na zásobníku
        """
        
        def __init__(self, s, isTerm=True, morph=True):
            """
            Vytvoření symbolu s typu t.
            :param s: Symbol
            :type s:
            :param isTerm: Druh terminál(True)/neterminál(False).
            :type isTerm: bool
            :param morph: Příznak zda se má slovo odpovídající termínálu ohýbat.
                V případě neterminálu tento příznak určuje zda se mají slova odpovídající všem
                terminálů, které je možné vygenerovat z daného neterminálu ohýbat/neohýbat.
                Alternativní definice:
                Flag, který určuje zda-li se nacházíme v části stromu, kde se slova mají ohýbat, či ne.
                Jedná se o zohlednění příznaku self.NON_GEN_MORPH_SIGN z gramatiky.
            :type morph: bool
            """
            
            self._s=s
            self._isTerm=isTerm
            self._morph=morph
            
        @property
        def val(self):
            return self._s
        
        @property
        def isTerm(self):
            """
            True jedná se o terminál. False jedná se neterminál.
            """
            return self._isTerm
        
        @property
        def isMorph(self):
            """
            True ohýbat. False jinak.
            """
            return self._morph
    
class Grammar(object):
    """
    Používání a načtení gramatiky ze souboru.
    Provádí sémantickou analýzu
    """
    EMPTY_STR="ε"   #Prázdný řetězec.
    
    #Má-li neterminál tuto značku na začátku znamená to, že všechny derivovatelné řetězce z něj
    #se nemají ohýbat.
    NON_GEN_MORPH_SIGN="!"   
    
    GEN_NONTERM_CNT_SEPPARATOR="$"
    """
    Separátor používány v auto. generovaných neterminálech pro oddělení původního jména s počítadlem.
    """
    
    class NotInLanguage(Errors.ExceptionMessageCode):
        """
        Řetězec není v jazyce generovaným danou gramatikou.
        """
        def __init__(self):
            super().__init__(Errors.ErrorMessenger.CODE_GRAMMAR_NOT_IN_LANGUAGE)
    
    class TimeoutException(Errors.ExceptionMessageCode):
        """
        Při provádění syntaktické analýzy, nad daným řetězcem, došlo k timeoutu.
        """
        def __init__(self):
            super().__init__(Errors.ErrorMessenger.CODE_GRAMMAR_SYN_ANAL_TIMEOUT)
    
    class ParsingTableSymbolRow(dict):
        """
        Reprezentuje řádek parsovací tabulky, který odpovídá symbolu.
        Chová se jako dict() s tím rozdílem, že
        pokud je namísto běžného SymbolRow[Terminal] použito SymbolRow[Token], tak pro daný symbol na zásobníku
        vybere všechna pravidla (vrací množinu pravidel), která je možné aplikovat pro daný token (jeden token může odpovídat více terminálům).
    
        Vkládané klíče musí být Terminály.
        
        Používá cache pro rychlejší vyhodnocení.
        
        """
        def __init__(self,*arg,**kw):
            super().__init__(*arg, **kw)
            self._cache={}
            
        
        
        def __getitem__(self, key):
            """
            Pokud je namísto běžného SymbolRow[Terminal] použito SymbolRow[Token], tak pro daný symbol na zásobníku
            vybere všechna pravidla (vrací množinu pravidel), která je možné aplikovat pro daný token (jeden token může odpovídat více terminálům).
            :param key: Terminal/token pro výběr.
            :type key: Terminal | Token
            :raise WordCouldntGetInfoException: Problém při analýze slova.
            """
            if isinstance(key, Token):
                #Nutné zjistit všechny terminály, které odpovídají danému tokenu.
                try:
                    #zkusíme použít cache
                    return self._cache[str(key)]
                except KeyError:
                    #bohužel nelze použít cache
                    res=set()
                    for k in self.keys():
                        if k.tokenMatch(key):
                            #daný terminál odpovídá tokenu, přidejme pravidla
                            res|=dict.__getitem__(self, k)
                            
                    self._cache[str(key)]=res
                    return res
            else:
                #běžný výběr
                return dict.__getitem__(self, key)
            

    

    def __init__(self, filePath, timeout=None):
        """
        Inicializace grammatiky jejim načtením ze souboru.
        
        :param filePath: Cesta k souboru s gramatikou
        :type filePath: str
        :param timeout: TimeoutException pro syntaktickou analýzu. Po kolik max milisekundách má přestat.
            TimeoutException je kontrolován vždy na začátku metody crawling.
        :type timeout: None | int
        :raise exception:
            Errors.ExceptionMessageCode pokud nemůže přečíst vstupní soubor.
            InvalidGrammarException pokud je problém se samotnou gramtikou.
        """
        self._terminals=set([Terminal(Terminal.Type.EOF)])  #implicitní terminál je konec souboru
        self._nonterminals=set()
        self._rules=set()
        
        self._load(filePath)


        self._simplify()
        
        #vytvoříme si tabulku pro parsování
        self._makeTable()
        
        self.timeout=timeout
        self.grammarEllapsedTime=0
        self.grammarNumOfAnalyzes=0

    
    def _load(self,filePath):
        """
        Načtení gramatiky ze souboru.
        
        :param filePath: Cesta k souboru s gramatikou.
        :type filePath: str
        :raise exception:
            Errors.ExceptionMessageCode pokud nemůže přečíst vstupní soubor.
            InvalidGrammarException pokud je problém se samotnou gramtikou.
            
        """
        try:
            with open(filePath, "r") as fG:
    
                firstNonEmptyLine=""
                for line in fG:
                    firstNonEmptyLine=self._procGFLine(line)
                    if len(firstNonEmptyLine)>0:
                        break
                
                #první řádek je startovací neterminál
                self._startS=self._procGFLine(firstNonEmptyLine)
                if len(self._startS) == 0:
                    raise InvalidGrammarException(code=Errors.ErrorMessenger.CODE_GRAMMAR_NO_START_SYMBOL)
                
                #parametrizované neterminály na levé straně pravidla
                #Neterminál se mapuje na dvojici neterminál  a list pravidel, kde se neterminál
                #vyskytuje na levé straně. 
                nontermsOnLeft={}
                
                
                
                for line in fG:
                    line=self._procGFLine(line)
                    if len(line)==0:
                        #prázdné přeskočíme
                        continue
                    #formát pravidla/šablony: Neterminál -> Terminály a neterminály
                    #přidáváme nové šablony
                    r=RuleTemplate(line)
                    #pro lepší rozgenerování uložíme do pomocné struktury
                    try:
                        if nontermsOnLeft[r.leftSide][0].params!=r.leftSide.params:
                            #Neprošla kontrola na stejné parametry. Na levé straně pravidel
                            #musí mít neterminály stejného jména stejné parametry včetně výchozích hodnot.
                            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_W_SAME_NAME_DIFF_PAR, \
                                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_W_SAME_NAME_DIFF_PAR).format(str(r.leftSide), str(nontermsOnLeft[r.leftSide][0])))
                        nontermsOnLeft[r.leftSide][1].append(r)
                    except KeyError:
                        #první výskyt
                        nontermsOnLeft[r.leftSide]=(r.leftSide,[r])
                
                #nejprve přiřadíme výchozí hodnoty
                self._addDefValNon(nontermsOnLeft)
                #rozgenerujeme šablony
                self._generateRules(nontermsOnLeft, Nonterminal(self._startS))
                
                
                if len(self._rules) == 0:
                    raise InvalidGrammarException(code=Errors.ErrorMessenger.CODE_GRAMMAR_NO_RULES)

                if self._startS not in self._nonterminals:
                    #startovací symbol není v množině neterminálů
                    raise InvalidGrammarException(code=Errors.ErrorMessenger.CODE_GRAMMAR_START_SYMBOL)
            
        except IOError:
            raise Errors.ExceptionMessageCode(Errors.ErrorMessenger.CODE_COULDNT_READ_INPUT_FILE,
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_COULDNT_READ_INPUT_FILE)+"\n\t"+filePath)
            
        
    def _addDefValNon(self, nontermsToRules:Dict[Nonterminal,Tuple[Nonterminal, List[RuleTemplate]]]):
        """
        Přiřadí parametrizovaným neterminálům defaulní hodnoty pro parametry, kde není přiřazena hodnota.
        Pracuje in-situ.
        
        :param nontermsToRules: Mapuje neterminály na dvojici neterminál a pravidla na jejichž levé straně
            se vyskytuje.
        :type nontermsToRules: Dict[Nonterminal,Tuple(Nonterminal, List[RuleTemplate])]
        :raise InvalidGrammarException: Pokud netermínál na pravé straně pravidla, se nevyskytuje nikde na levé straně nějakého pravidla.
        """
        
        for _, templates in nontermsToRules.values():
            for t in templates:
                #projdeme neterminály na pravé straně
                for n in t.nontermsOnRightSide:
                    #přiřadíme defaultní hodnoty
                    try:
                        n.addDefault(nontermsToRules[n][0].params)
                    except KeyError:
                        raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERMINAL_NO_CORESPONDING_RULE,
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERMINAL_NO_CORESPONDING_RULE).format(n))



    def _generateRules(self, nontermsToRules:Dict[Nonterminal,Tuple[Nonterminal, List[RuleTemplate]]], s:Nonterminal):
        """
        Rozgenerování providlových šablon, do klasických pravidel.
        
        Předpokládá, že již byly vloženy defaultní hodnoty a parametry k neterminálům na pravých stranách pravidel, kterým nějaký
        takový parametr úplně chyběl.
        
        :param nontermsToRules: Mapuje neterminály na dvojici neterminál a pravidla na jejichž levé straně
            se vyskytuje.
        :type nontermsToRules: Dict[Nonterminal,Tuple(Nonterminal, List[RuleTemplate])]
        :param s: Startovací neterminál pro generování. Určuje i přiřazení hodnot parametrům
            Mělo by se tedy jednat o neterminál z pravé strany.
        :type s: Nonterminal
        :param paramsValues: Přiřazení hodnot parametrům neterminálů.
        :type paramsValues: Dict[str,str]
        :raise InvalidGrammarException:
            InvalidGrammarException pokud je problém se samotnou gramtikou.
        """
        #najdeme pravidla na jejichž levé straně je daný neterminál
        
       
        try:
            templates=nontermsToRules[s][1]
        except KeyError:
            raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERMINAL_NO_CORESPONDING_RULE,
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERMINAL_NO_CORESPONDING_RULE).format(s))

        for t in templates:
            #procházíme korespondující pravidla
            #vygenerujeme nové pravidlo a přidáme terminály a neterminály
            
            r=Rule(t.generate(s.params), self._terminals, self._nonterminals)
            
            if r not in self._rules:
                #máme nové pravidlo
                self._rules.add(r)
            
                #projdeme neterminály na pravé straně
                for n in t.nontermsOnRightSide:
                    #přiřadíme hodnoty proměnným
                    #výchozí hodnoty zde vkládat nemusíme, prože mají být vloženy před
                    #voláním této funkce
                    n=copy.deepcopy(n)
                    try:
                        for varName, varValue in n.params.items():
                            if RuleTemplate.VARIABLE_REGEX.search(varValue):
                                #jedná se o proměnnou
                                n.params[varName]=s.params[varName]
                    except KeyError:
                        #nemáme asi hodnotu pro některou proměnnou
                        raise InvalidGrammarException(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_NO_PAR_VALUE,
                                              Errors.ErrorMessenger.getMessage(Errors.ErrorMessenger.CODE_GRAMMAR_NONTERM_NO_PAR_VALUE).format(n))
                        
                    self._generateRules(nontermsToRules, n)
            
            
    
    def __str__(self):
        """
        Converts grammar to string.
        in format:
        S=start_symbol
        N={nonterminals}
        T={terminals}
        P={
            rules
        }
        """
        s="S="+self._startS+"\n"
        s+="N={"+", ".join(sorted( str(n) for n in self._nonterminals))+"}\n"
        s+="T={"+", ".join(sorted( str(t) for t in self._terminals))+"}\n"
        s+="P={\n"
        for r in sorted( str(r) for r in self._rules):
            s+="\t"+str(r)+"\n"
        s+="}"
        return s
        
    @staticmethod
    def _procGFLine(line):
        """
        Před zpracování řádku ze souboru s gramatikou. Odstraňuje komentáře a zbytečné bíle znaky.
        
        :param line: Řádek ze souboru s gramatikou.
        :type line: str
        """
        return line.split("#",1)[0].strip()
            
    def analyse(self, tokens):
        """
        Provede syntaktickou analýzu pro dané tokeny.
        Poslední token předpokládá EOF. Pokud jej neobsahuje, tak jej sám přidá na konec tokens.
        
        :param tokens: Tokeny pro zpracování.
        :type tokens: list
        :return: Dvojici s listem listu pravidel určujících všechny možné derivace a list listů analyzovaných tokenů.
            Pokud vrací None došlo k timeoutu.
        :rtype: (list(list(Rule)), list(list(AnalyzedToken))) | None
        :raise NotInLanguage: Řetězec není v jazyce generovaným danou gramatikou.
        :raise WordCouldntGetInfoException: Problém při analýze slova.
        :raise TimeoutException: Při provádění syntaktické analýzy, nad daným řetězcem, došlo k timeoutu.
        """
        
        #provedeme samotnou analýzu a vrátíme výsledek
        self.analyzeStartTime = time.time()
        if tokens[-1].type!=Token.Type.EOF:
            tokens.append(Token(None,Token.Type.EOF))
            
        # Přidáme na zásoník konec vstupu a počáteční symbol
        stack=[Symbol(Terminal(Terminal.Type.EOF), True, True), Symbol(self._startS, False, self._startS[0]!=self.NON_GEN_MORPH_SIGN)]
        position=0
        
        res=self.crawling(stack, tokens, position)

        self.grammarEllapsedTime+=time.time()-self.analyzeStartTime
        self.grammarNumOfAnalyzes+=1
        return res
    
    def crawling(self, stack, tokens, position):
        """
        Provádí analýzu zda-li posloupnost daných tokenů patří do jazyka definovaného gramatikou.
        Vrací posloupnost použitých pravidel. Nezastaví se na první vhodné posloupnosti pravidel, ale hledá všechny možné.
        
        Tato metoda slouží především pro možnost implementace zpětného navracení při selhání, či hledání další vhodné posloupnosti
        pravidel.
        
        :param stack: Aktuální obsah zásobníku. (modifukuje jej)
        :type stack: list(Symbol)
        :param tokens: posloupnost tokenů na vstupu
        :type tokens: list(Token)
        :param position: Index aktuálního tokenu. Definuje část vstupní posloupnosti tokenů, kterou budeme procházet.
            Od předaného indexu do konce.
        :type position: integer
        :return: Dvojici s listem listu pravidel určujících všechny možné derivace a list listů analyzovaných tokenů.
        :rtype: (list(list(Rule)), list(list(AnalyzedToken)))
        :raise NotInLanguage: Řetězec není v jazyce generovaným danou gramatikou.
        :raise WordCouldntGetInfoException: Problém při analýze slova.
        :raise TimeoutException: Při provádění syntaktické analýzy, nad daným řetězcem, došlo k timeoutu.
        """
        if self.timeout is not None:
            #kontrola na timeout
            if (time.time()-self.analyzeStartTime)*1000 >=self.timeout:
                #překročen timeout -> končíme
                raise self.TimeoutException()
                
        aTokens=[]  #analyzované tokeny
        rules=[]    #použitá pravidla

        while(len(stack)>0):
            s=stack.pop()
            token=tokens[position]
            
            if s.isTerm:
                #terminál na zásobníku
                if s.val.tokenMatch(token):
                    #stejný token můžeme se přesunout
                    #token odpovídá terminálu na zásobníku
                    position+=1
                    

                    aTokens.append(AnalyzedToken(token,
                                                False if token.type==Token.Type.ANALYZE_UNKNOWN else s.isMorph and s.val.morph,
                                                s.val))# s je odpovídající terminál
                    
                else:
                    #chyba rozdílný terminál na vstupu a zásobníku
                    raise self.NotInLanguage()
            else:
                #neterminál na zásobníku

                #vybereme všechna možná pravidla pro daný token na vstupu a symbol na zásobníku
                
                actRules=self._table[s.val][token]  #díky použité třídě ParsingTableSymbolRow si můžeme dovolit použít přímo token
                
                if not actRules:
                    #v gramatice neexistuje vhodné pravidlo
                    raise self.NotInLanguage()
                
                if len(actRules)==1:
                    #jedno možné pravidlo
                    r=next(iter(actRules))
                    self.putRuleOnStack(r, stack, s.isMorph)
                    rules.append(r)
                    
                else:
                    #více možných pravidel
                    #pro každou možnou derivaci zavoláme rekurzivně tuto metodu
                    newRules=[]
                    newATokens=[]

                    for r in actRules:
                        try:
                            #prvně aplikujeme pravidlo na nový stack
                            newStack=stack.copy()
                            self.putRuleOnStack(r, newStack, s.isMorph)
                            
                            #zkusíme zdali s tímto pravidlem uspějeme                            
                            resRules, resATokens=self.crawling(newStack, tokens, position)
                            

                            if resRules and resATokens:
                                #zaznamenáme aplikováná pravidla a analyzované tokeny
                                #může obsahovat i více různých derivací
                                for x in resRules:
                                    #musíme předřadit aktuální pravidlo a pravidla předešlá
                                    newRules.append(rules+[r]+x)
                                    
                                for x in resATokens:
                                    #musíme předřadit předešlé analyzované tokeny
                                    newATokens.append(aTokens+x)
                                    
                        except self.NotInLanguage:
                            #tato větev nikam nevede, takže ji prostě přeskočíme
                            pass
            
                    if len(newRules) == 0:
                        #v gramatice neexistuje vhodné pravidlo
                        raise self.NotInLanguage()
    
                        
                    #jelikož jsme zbytek prošli rekurzivním voláním, tak můžeme již skončit
                    return (newRules,newATokens)
                    
        
        
        #Již jsme vyčerpali všechny možnosti. Příjmáme naši část vstupní pousloupnosti a končíme.
        #Zde se dostaneme pouze pokud jsme po cestě měli možnost aplikovat pouze jen přímo 
        #terminály a nebo vždy právě jedno pravidlo.
        return ([rules], [aTokens])
     
    def putRuleOnStack(self, rule:Rule, stack, morph):
        """
        Vloží pravou stranu pravidla na zásobník.
        
        :param rule: Pravidlo pro vložení.
        :type rule: Rule
        :param stack: Zásobník pro manipulaci. Obsahuje výsledek.
        :type stack:list
        :param morph: Příznak ohýbání slov.
        :type morph: bool
        """
        
        for rulePart in reversed(rule.rightSide):
            if rulePart!=self.EMPTY_STR: #prázdný symbol nemá smysl dávat na zásobník
                isTerminal=rulePart in self._terminals or rulePart==self.EMPTY_STR
                #aby se jednalo o ohebnou část jména musíme se nacházet v ohebné částistromu (morph=true)
                #a navíc pokud máme neterminál, tak musím zkontrolovat zda-li se nedostáváme do neohebné části
                #rulePart.val[0]!=self.NON_GEN_MORPH_SIGN
                shouldMorph=morph and (True if isTerminal else rulePart[0]!=self.NON_GEN_MORPH_SIGN)
                stack.append(Symbol(rulePart, isTerminal, shouldMorph))
                
    
    @classmethod
    def getMorphMask(cls, rules, morph=True):
        """
        Zjistí pro jaká slova má generovat tvary.
        Tím, že si tvoří z pravidel syntaktický strom.
        
        :param rules: (MODIFIKUJE TENTO PARAMETR!) Pravidla získaná z analýzy (metoda analyse).
        :type rules: list
        :param morph: Pokud je false znamená to, že v této části syntaktického stromu negenerujeme tvary.
        :type morph: boolean
        :return: Maska v podobě listu, kde pro každé slovo je True (generovat) nebo False (negenerovat).
        :rtype: list
        """

        actRule=rules.pop(0)

        if morph:
            #zatím jsme mohli ohýbat, ale to se může nyní změnit
            morph=actRule.leftSide[0]!=cls.NON_GEN_MORPH_SIGN  #příznak toho, že v tomto stromu na tomto místě se mají/nemají ohýbat slova

        morphMask=[]  #maska určující zda-li se má ohýbat. True znamená, že ano. 
        
        
        #máme levou derivaci, kterou budeme symulovat a poznamenáme si vždy
        #zda-li zrovna nejsme v podstromě, který má příznak pro neohýbání.
        #pravidlo je vždy pro první neterminál z leva
        
        for x in [p for p in  actRule.rightSide if p!=cls.EMPTY_STR]:
            if any( x==r.leftSide for r in rules):
                #lze dále rozgenerovávat
                #přidáme masku od potomka
                
                morphMask+=cls.getMorphMask(rules, morph)#rovnou odstraní použitá pravidla v rules
            else:
                #nelze
                morphMask.append(morph)  

        return morphMask
                
    def _simplify(self):
        """
        Provede zjednodušení gramatiky.
        """
        self._removeAllUsellesSymbols()
        self._eliminatingEpRules()
        #self._removeUnaryRules()
        self._makeGroups()
  
    def _removeAllUsellesSymbols(self):
        """
        Provede odstranění zbytečných symbolů.
        
        Neterminál je zbytečný pokud se z něj nedá proderivovat k řetězci.
        Neterminál je také zbytečný pokud se z k němu nedá proderivovat z počátečního neterminálu.
        """
        
        #které neterminály nevedou k řetězci?
        #vytvoříme si množinu obsahující bezpečné symboly, které se určitě derivují k řetězci.
        #Prvně vložíme terminály a epsilon. Ty se sice nederivují, ale zpřehledníme si tím práci.
        deriveToTerminals=self._terminals.copy()
        deriveToTerminals.add(self.EMPTY_STR)

        #Nejprve vezme všechny neterminály, které přímo derivují terminály (i epsilon).
        #Dále nás budou zajímat i pravidla, která obsahují i neterminály, o kterých víme, že vedou na řetězec.
        change=True
        while change:
            #Procházíme dokud dostáváme nové symboly, které také vedou k řetězci
            change=False
            
            for r in self._rules:
                if all(x in deriveToTerminals for x in r.rightSide):
                    if r.leftSide not in deriveToTerminals:
                        deriveToTerminals.add(r.leftSide)
                        change=True
                    
        #odstraníme všechny pravidla obsahující nepovolené neterminály a i samotné nepovolené neterminály
        self._rules={r for r in self._rules if r.leftSide in deriveToTerminals and not any( s not in deriveToTerminals for s in r.rightSide)}
        self._nonterminals={ n for n in self._nonterminals if n in deriveToTerminals}
        
        #Teď budeme odstraňovat neterminály, ke kterým se nedostaneme z počátečního symbolu.
        #začínáme od počátečního symbolu
        usedRules=set()
        usedSymbols={self._startS}
        change=True
        while change:
            change=False
            for r in self._rules:
                if r.leftSide in usedSymbols:
                    if r not in usedRules:
                        #přidáme pravidlo
                        usedRules.add(r)
                        change=True
                        for s in r.rightSide:
                            #přidáme symboly
                            usedSymbols.add(s)
                
        #odstraníme všechny nepoužitá pravidla a symboly
        self._rules=usedRules
        self._nonterminals=self._nonterminals & usedSymbols
        self._terminals=self._terminals & usedSymbols
        
        #musíme přidat ještě terminál s koncem souboru, protože byl zrovna odstraněn
        self._terminals.add(Terminal(Terminal.Type.EOF))
    
    def _eliminatingEpRules(self):
        """
        Provede eliminaci epsilon pravidel.
        """
        
        #vytvoříme empty množinu
        self._makeEmptySets()
        
        tmpRules=set()
        for r in self._rules:
            if not r.rightSide==[self.EMPTY_STR]:   #pravidla A ->ε vynecháváme
                #vytvoříme všechny kombinace z pravidla, kde můžeme vynechat 0-x neterminálu, které se derivují na empty
                
                #0-vynechání
                tmpRules.add(r)
                
                allEmptyOnRSide=[i for i, n in enumerate(r.rightSide) if self._empty[n]]
                
                for i in range(1, len(allEmptyOnRSide)+1):
                    #vynecháváme 1-x symbolů
                    for shouldRemove in itertools.combinations(allEmptyOnRSide, i):
                        #vybraná kombinace pro odstranění
                        newRule=copy.copy(r)
                        #upravíme pravou stranu
                        newRule.rightSide=[s for pi,s in enumerate(newRule.rightSide) if pi not in shouldRemove]
                        if len(newRule.rightSide)>0:
                            tmpRules.add(newRule)
        if self._empty[self._startS]:
            tmpRules.add(Rule("S->"+self.EMPTY_STR))
        self._rules=tmpRules
        
        
    def _removeUnaryRules(self):
        """
        Provede odstranění jednoduchých pravidel ve formě: A->B, kde A,B jsou neterminály.
        POZOR!: Předpokládá gramatiku, na kterou bylo použito eliminatingEpRules.
        """
        #Inspirováno:
        #Source: https://courses.engr.illinois.edu/cs373/sp2009/lectures/lect_12.pdf
        #Lecture 12: Cleaning upCFGs and Chomsky Nor-mal form, CS 373: Theory of Computation ̃Sariel Har-Peled and Madhusudan Parthasarathy
        
        #zjistíme takzvané jednotkové páry (Unit pair).
        #X,Y z N je jednotkový pár, pokud  X =>* Y
        
        unitPairs={r for r in self._rules if len(r.rightSide)==1 and not isinstance(r.rightSide[0], Terminal) and r.rightSide[0]!=self.EMPTY_STR}#na pravé straně je pouze 1 neterminál
        numberOfPairs=0
        while numberOfPairs!=len(unitPairs):
            numberOfPairs=len(unitPairs)
            
            tmpUnitPair=unitPairs.copy()
            for unitPairRule in tmpUnitPair:  #(X->Y)
                for unitPairRuleOther in {r for r in tmpUnitPair if r.leftSide==unitPairRule.rightSide[0] }:#(Y->Z)
                    newRule=copy.copy(unitPairRule)
                    newRule.rightSide=[unitPairRuleOther.rightSide[0]]
                    
                    if unitPairRuleOther.leftSide[0]==self.NON_GEN_MORPH_SIGN and \
                        unitPairRuleOther.rightSide[0][0]!=self.NON_GEN_MORPH_SIGN:
                        #Nesmíme zapomenout přidat příznak, že se nemá ohýbat,
                        #pokud je třeba.
                        newRule.rightSide[0]=self.NON_GEN_MORPH_SIGN+newRule.rightSide[0]
                        
                    unitPairs.add(newRule)#(X->Z)

        #odstraníme jednoduchá pravidla
        oldRules=self._rules.copy()
        self._rules -= unitPairs
        
        for unitPairRule in unitPairs:  #X->A
            for r in {oldR for oldR in oldRules if oldR.leftSide==unitPairRule.rightSide[0]}:   #A->w

                if len(r.rightSide)>1 or (isinstance(r.rightSide[0], Terminal) or r.rightSide[0]==self.EMPTY_STR):
                    #na pravé straně není pouze daný neterminál
                    
                    newRule=copy.copy(unitPairRule)
                    newRule.rightSide=r.rightSide

                    if newRule.leftSide[0]!=self.NON_GEN_MORPH_SIGN and r.leftSide[0]==self.NON_GEN_MORPH_SIGN:
                        #Nesmíme zapomenout přidat příznak, že se nemá ohýbat, ale tentokráto to musíme
                        #přesunout přímo to terminálu.
                        for s in newRule.rightSide:
                            if isinstance(s, Terminal):
                                
                                s.morph=False
                                
                    self._rules.add(newRule)    #X->w
                    
                    
    def _makeGroups(self):
        """
        Provede slučování pravidel na základě prefixů. Vhodné pro zjednodušení procesu analýzy.
        
        Příklad:
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"}
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} !T_GROUP
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} NOUN_GROUP_START
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} NOUN_GROUP_START !T_GROUP
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} NOUN_GROUP_START PREP_GROUP
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} NOUN_GROUP_START PREP_GROUP !T_GROUP
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} PREP_GROUP
            S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} PREP_GROUP !T_GROUP
            
            S -> NUM(n=S,g=M) ADJ_GROUP_MANDATORY(n=S,g=M) END
            S -> NUM(n=S,g=M) ADJ_GROUP_MANDATORY(n=S,g=M) LOC2(n=S,g=M) END
            
            Převede na:
                S->!NUMERIC 1{g=F, note=jS, n=S, c=1, t=S, r="^.*ová$"} S$1
                S$1-> ε
                S$1-> !T_GROUP
                S$1-> NOUN_GROUP_START S$2
                S$1-> PREP_GROUP S$3
                S$2-> ε
                S$2 -> !T_GROUP
                S$2 -> PREP_GROUP
                S$2 -> PREP_GROUP !T_GROUP
                S$3-> !T_GROUP 
                S$3-> ε         
                S -> NUM(n=S,g=M) ADJ_GROUP_MANDATORY(n=S,g=M) S$4
                S$4-> ε
                S$4-> LOC2(n=S,g=M) END
        
        """
        
        searchAccordingToLeftSide={}
        for r in self._rules:
            #najdeme pravidla se stejnou levou stranou
            try:
                searchAccordingToLeftSide[r.leftSide].add(r)
            except KeyError:
                searchAccordingToLeftSide[r.leftSide]=set([r])
                
        self._rules=set()   #budeme plnit novými pravidly

        for leftSide, rules in searchAccordingToLeftSide.items():
            #rekurzivní vytváření nových pravidel na základě společného prefixu
            #pravých stran
            self._rules|=self._makePrefixGroups(leftSide, RulePrefixTree(rules))
            
    def _makePrefixGroups(self, leftSide, prefTree):
        """
        Vytvoři nová pravidla na základě prefixového stromu.
        
        :param leftSide: Levá strana pravidel, které se mají vytvářet.
            Pokud dojde v rekurzi ke větvení, tak přidává pro rozlyšení hodnotu čítače k názvu.
        :type leftSide: str
        :param prefTree: Prefixový strom na jehož základě tvoří nová pravidla.
        :type prefTree: RulePrefixTree
        """
        
        #Budeme si zde pro lepší představu ukazovat průběh na modelovém prefixovém stromu.
        #1] (1,2) (3) (4)    {1}
        #2] (1,2) (3)        {1,2}
        #3] (1,2)            {1,2,3}
        #4] (3,4)            {4}
        # touply vždy označují nejdelší prefixy, než dojde k větvení. V množinových závorkách jsou čísla pravidel
        # se stejným prefixem.
        
        rules=set()

        newNontermsCnt=0
        for prefix, tree in prefTree.offsprings.items():
            if len(tree.rules)>1:
                #větvíme
                #budeme potřebovat nový neterminál pro
                #reprezentaci větve
                newNonTerm=leftSide+self.GEN_NONTERM_CNT_SEPPARATOR+str(newNontermsCnt)
                newNontermsCnt+=1
                
                #vytvoříme novou větev
                rules.add(Rule(fromString=None, 
                               terminals=self._terminals,
                               nonterminals=self._nonterminals,leftSide=leftSide,
                     rightSide=list(prefix)+[newNonTerm]))

                #rekurzivně se zanoříme do větve
                rules|=self._makePrefixGroups(newNonTerm,tree)
            else:
                #konec už dál nevětvíme
                if prefix is None:
                    #None jako prefix znamená, že aktuální neterminál na levé straně pravidla
                    #se může derivovat na prázdný řetězec.
                
                    #Například chci povolit derivaci jak pro případ znázorněný pravidlem:
                    #3] (1,2)            {1,2,3}
                    #tak i dalších sdílejících prefix.
                    #1] (1,2) (3) (4)    {1}
                    #2] (1,2) (3)        {1,2}
                    rules.add(Rule(fromString=None, 
                                   terminals=self._terminals,
                                   nonterminals=self._nonterminals,leftSide=leftSide,
                                   rightSide=[self.EMPTY_STR]))
                
                else:      
                    rules.add(Rule(fromString=None, 
                               terminals=self._terminals,
                               nonterminals=self._nonterminals,
                               leftSide=leftSide,rightSide=list(prefix)))
                
                    #v našem modelovém případu to odpovídá:
                    #    1] (1,2) (3) (4)    {1}
                    #    4] (3,4)            {4}    
                
                
            
        return rules
        
    def _makeTable(self):
        """
        Vytvoření parsovací tabulky.
        
        """
        self._makeEmptySets()
        #COULD BE DELETED print("empty", self._empty)
        self._makeFirstSets()
        #COULD BE DELETED print("first", self._first)
        self._makeFollowSets()
        #COULD BE DELETED print("follow", self._follow)
        self._makePredictSets()
        #COULD BE DELETED print("predict", ", ".join(str(r)+":"+str(t) for r,t in self._predict.items()))
        
        """
        COULD BE DELETED
        print("predict")
        
        for i, l in enumerate([ str(k)+":"+str(x) for k,x in self._predict.items()]):
            print(i,l)
            
        """

        #inicializace tabulky
        self._table={ n:self.ParsingTableSymbolRow({t:set() for t in self._terminals}) for n in self._nonterminals}
        
        #zjištění pravidla pro daný terminál na vstupu a neterminál na zásobníku
        for r in self._rules:
            for t in self._terminals:
                if t in self._predict[r]:
                    #t může být nejlevěji derivován
                    self._table[r.leftSide][t].add(r)

        #Jen pro testovani self.printParsingTable()
                  
    '''
    Jen pro testovani
    Potřebuje importovat pandas.
    
    def printParsingTable(self):
        """
        Vytiskne na stdout tabulku pro analýzu.
        """
        inputSymbols=[Token.Type.EOF.terminalRepr]+list(sorted(self._terminals))
        
        ordeNon=list(self._nonterminals)
        data=[]
        for n in ordeNon:
            data.append([str(self._table[n][iS]) for iS in inputSymbols])
            
        print(pandas.DataFrame(data, ordeNon, inputSymbols))
    '''
    
    def _makeEmptySets(self):
        """
        Získání "množin" empty (v aktuální gramatice) v podobě dict s příznaky True/False,
         zda daný symbol lze derivovat na prázdný řetězec.
         
        Jedná se o Dict s příznaky: True lze derivovat na prázdný řetězec, či False nelze. 

        """

            
        self._empty={t:False for t in self._terminals} #terminály nelze derivovat na prázdný řetězec
        self._empty[self.EMPTY_STR]=True    #prázdný řetězec mohu triviálně derivovat na prázdný řetězec
        
        for N in self._nonterminals:
            #nonterminály inicializujeme na false
            self._empty[N]=False
        
        
        #pravidla typu: N -> ε
        for r in self._rules:
            if r.rightSide == [self.EMPTY_STR]:
                self._empty[r.leftSide]=True
            else:
                self._empty[r.leftSide]=False
        
        #hledáme ty, které se mohou proderivovat na prázdný řetězec ve více krocích
        #procházíme pravidla dokud se mění nějaká množina empty
        change=True
        while change: 
            change=False
            
            for r in self._rules:
                if all(self._empty[rN] for rN in r.rightSide):
                    #všechny symboly na pravé straně pravidla lze derivovat na prázdný řetězec
                    if not self._empty[r.leftSide]:
                        #došlo ke změně
                        self._empty[r.leftSide]=True
                        change=True
   
    
    def _makeFirstSets(self):
        """
        Získání "množin" first (v aktuální gramatice) v podobě dict s množinami 
        prvních terminálů derivovatelných pro daný symbol.
        
        Před zavoláním této metody je nutné zavolat _makeEmptySets!
        """

        self._first={t:set([t]) for t in self._terminals} #terminály mají jako prvního samy sebe
        self._first[self.EMPTY_STR]=set()

        #inicializace pro neterminály
        for n in self._nonterminals:
            self._first[n]=set()
            
        #Hledáme first na základě pravidel
        change=True
        while change: 
            change=False
            for r in self._rules:
                #přidáme všechny symboly z first prvního symbolu, který se nederivuje na prázdný
                #také přidáváme first všech po cestě, kteří se derivují na prázdný
                for x in r.rightSide:
                    if self._empty[x]:
                        #derivuje se na prázdný budeme se muset podívat i na další
                        tmp=self._first[r.leftSide] | self._first[x]
                        if tmp!= self._first[r.leftSide]:
                            #došlo ke změně
                            self._first[r.leftSide] = tmp
                            change=True
                    else:
                        #nalezen první, který se nederivuje na prázdný
                        tmp=self._first[r.leftSide] | self._first[x]
                        if tmp!= self._first[r.leftSide]:
                            #došlo ke změně
                            self._first[r.leftSide] = tmp
                            change=True
                        break

    def _makeFollowSets(self):
        """
        Získání množiny všech terminálů, které se mohou vyskytovat vpravo od nějakého neterminálu A ve větné formě.
        
        Před zavoláním této metody je nutné zavolat _makeEmptySets, _makeFirstSets!

        """
        self._follow={ n:set() for n in self._nonterminals} #pouze pro neterminály
        #u startovacího neterminálu se ve větné formě na pravo od něj může vyskytovat pouze konec vstupu
        self._follow[self._startS]=set([Terminal(Terminal.Type.EOF)])
        
        #hledání follow na základě pravidel
        change=True
        while change: 
            change=False
            for r in self._rules:
                for i, x in enumerate(r.rightSide):
                    if x in self._nonterminals:
                        #máme neterminál
                        if i+1<len(r.rightSide):
                            #nejsme na konci
                            tmp=self._follow[x]|self._firstFromSeq(r.rightSide[i+1:])
                            if tmp!=self._follow[x]:
                                #zmena
                                self._follow[x]=tmp
                                change=True
                                
                        if i+1>=len(r.rightSide) or self._emptySeq(r.rightSide[i+1:]):
                            #v pravo je prázdno nebo se proderivujeme k prázdnu
                            
                            tmp=self._follow[x]|self._follow[r.leftSide]
                            if tmp!=self._follow[x]:
                                #zmena
                                self._follow[x]=tmp
                                change=True
                                    
       

        
    
    def _makePredictSets(self):
        """
        Vytvoření množiny Predict(A → x), která je množina všech terminálů, které mohou být aktuálně nejlevěji
        vygenerovány, pokud pro libovolnou větnou formu použijeme pravidlo A → x.
        
        Před zavoláním této metody je nutné zavolat _makeEmptySets, _makeFirstSets, _makeFollowSets!
        
        """
        
        self._predict={}
        
        for r in self._rules:
            if self._emptySeq(r.rightSide):
                self._predict[r]=self._firstFromSeq(r.rightSide)|self._follow[r.leftSide]
            else:
                self._predict[r]=self._firstFromSeq(r.rightSide)
    
    def _firstFromSeq(self,seq):
        """
        Získání množiny first z posloupnosti terminálů a neterminálů
        
        Před zavoláním této metody je nutné zavolat _makeEmptySets, _makeFirstSets!
        
        :param seq: Posloupnost terminálů a neterminálů.
        :type seq: list
        :return: Množina first.
        :rtype: set|None
        """
        
        first=set()
        
        for x in seq:
            if self._empty[x]:
                #derivuje se na prázdný budeme se muset podívat i na další
                first=first|self._first[x]
            else:
                #nalezen první, který se nederivuje na prázdný
                first=first|self._first[x]
                break
        
        return first
    
    def _emptySeq(self,seq):
        """
        Určení množiny empty pro posloupnost terminálů a neterminálů
        
        Před zavoláním této metody je nutné zavolat _makeEmptySets!
        
        :param seq: Posloupnost terminálů a neterminálů.
        :type seq: list
        :return: True proderivuje se k prázdnému řetězce. Jinak false.
        :rtype: bool
        """
        
        return all(self._empty[s] for s in seq)


                
                
