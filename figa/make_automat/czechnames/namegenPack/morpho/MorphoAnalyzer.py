"""
Created on 14. 7. 2018

Tento modul obsahuje třídy pro morfologickou analýzu.

:author:     Martin Dočekal
:contact:    xdocek09@stud.fit.vubtr.cz
"""

from abc import ABC, abstractmethod, abstractclassmethod, abstractproperty
from subprocess import Popen, PIPE
from ..Errors import ExceptionMessageCode, ErrorMessenger
from namegenPack.morpho.MorphCategories import *
import collections

from typing import Set, Dict, Tuple
import string
import math
import logging
import sys

class MARule(collections.Mapping):
    """
    Reprezentace pravidla tvaru z morfologické analýzy.
    Pravidlo reprezentuje mluvnické kategorie, které ma dané slovo.
    """
    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        if self._hash is None:
            self._hash = 0
            for pair in self._d.items():
                self._hash ^= hash(pair)
        return self._hash
    
    def __str__(self):
        return str(self._d)
    
    def __repr__(self):
        return repr(self._d)
    
    def sameExcept(self, other, exceptCat:Set[MorphCategories]=set()):
        """
        Porovnává aktuální pravidlo s nějakým jiným zdali je stejné až na dané morfologické kategorie.
        
        :param other: Pravidlo pro porovnání.
        :type other: MARule
        :param exceptCat: Kategorie, které nejsou zohledňovány při kontrole na shodu.
        :type exceptCat: Set[MorphCategories]
        """
        try:
            for morphCat, morphCatVal in self.items():
                if morphCat not in exceptCat and other[morphCat]!=morphCatVal:
                    #nemá stejnou hodnotu pro morphcat a nejedná se o pád
                    return False
        except KeyError:
            #asi nemá morphCat vůbec
            return False
        
        return True
        
    
    @property
    def lntrf(self):
        """
        Ve formátu lntrf. Včetně poznámky
        """
        res=self.lntrfWithoutNote
        try:
            return res+self[MorphCategories.NOTE].lntrf
        except KeyError:
            pass
        return res
        
    @property
    def lntrfWithoutNote(self):
        """
        Ve formátu lntrf. Bez poznámky
        """
        pos=self[MorphCategories.POS].lntrf
        try:
            #pořadí pro ify je voleno dle předpokládané četnosti
            if self[MorphCategories.POS]==POS.NOUN:
                #podstané jméno zjistím rod, číslo, pád
                return pos+self[MorphCategories.GENDER].lntrf \
                    +self[MorphCategories.NUMBER].lntrf \
                    +self[MorphCategories.CASE].lntrf
                    
            if self[MorphCategories.POS]==POS.ADJECTIVE:
                #přídavné jméno zjistím negaci,rod, číslo, pád, stupeň
                return pos+self[MorphCategories.NEGATION].lntrf \
                    +self[MorphCategories.GENDER].lntrf \
                    +self[MorphCategories.NUMBER].lntrf \
                    +self[MorphCategories.CASE].lntrf \
                    +self[MorphCategories.DEGREE_OF_COMPARISON].lntrf
                    
            if self[MorphCategories.POS]==POS.PREPOSITION:
                #předložka pád
                return pos
            
            if self[MorphCategories.POS]==POS.PREPOSITION_M:
                #předložka M pád
                return pos
                    
            if self[MorphCategories.POS]==POS.NUMERAL:
                #číslovka rod, číslo, pád
                return pos+self[MorphCategories.GENDER].lntrf \
                    +self[MorphCategories.NUMBER].lntrf \
                    +self[MorphCategories.CASE].lntrf
                    
            if self[MorphCategories.POS]==POS.PRONOUN:
                #zájméno zjistime rod, číslo, pád
                return pos+self[MorphCategories.GENDER].lntrf \
                    +self[MorphCategories.NUMBER].lntrf \
                    +self[MorphCategories.CASE].lntrf
                    
            if self[MorphCategories.POS]==POS.VERB:
                #sloveso negace, osoba, číslo
                return pos+self[MorphCategories.NEGATION].lntrf \
                    +self[MorphCategories.PERSON].lntrf \
                    +self[MorphCategories.NUMBER].lntrf
                    
            if self[MorphCategories.POS]==POS.ADVERB:
                #příslovce negace stupeň
                return pos+self[MorphCategories.NEGATION].lntrf \
                    +self[MorphCategories.DEGREE_OF_COMPARISON].lntrf
            
            if self[MorphCategories.POS]==POS.CONJUNCTION:
                #spojka, nic
                return pos
            
            if self[MorphCategories.POS]==POS.PARTICLE:
                #částice, nic
                return pos
            if self[MorphCategories.POS]==POS.INTERJECTION:
                #citoslovce, nic
                return pos
        except KeyError:
            #zdá se, že nevyhovuje tradičnímu rozvržení
            #zkusíme tedy co všechno má
            res=pos
            
            for x in [MorphCategories.NEGATION,MorphCategories.GENDER,MorphCategories.PERSON,\
                      MorphCategories.NUMBER,MorphCategories.CASE,MorphCategories.NEGATION,\
                      MorphCategories.DEGREE_OF_COMPARISON]:
                try:
                    res+=self[x].lntrf
                except KeyError:
                    #tohle ne zkusíme další
                    pass
            
            return res

class MorphoAnalyze(ABC):
    """
    Interface pro výsledky morfologické analýzy slova.
    """
    
    @abstractmethod
    def getAll(self, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set(), groupFlags:Set[Flag]=set()) -> Dict[MorphCategories,Set[MorphCategory]]:
        """
        Vrácení všech možných hodnot mluvnických kategorií.
        
        :param valFilter: (Volitelný) Filtr, který určuje pevně stanovené 
            hodnoty, které musí mít dané pravidlo, aby se bralo v úvahu.
            Tedy není-li v daném pravidle vůbec zmíněná kategorie obsažena, tak pravidlo neprojde přes filtr.
            Příklad: Chci získat všechny rody jakých může nabývat slovo pokud je podstatným jménem.
            Nastavím filtr na: set(POS.NOUN)
            Chci získat všechny hodnoty pro slovo ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
        :type valFilter: Set[MorphCategory]
        :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
        :type notValFilter:Set[MorphCategory]
        :param groupFlags: Flagy, které musí mít daná skupina vázající se na slovo.
        :type groupFlags: Set[Flag]
        :return: Hodnoty mluvnických kategorií.
        :rtype: Dict[MorphCategories, Set[MorphCategory]]
        """
        pass
    
    @abstractmethod
    def getAllForCategory(self, morphCategory: MorphCategories, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set(), groupFlags:Set[Flag]=set()) -> Set[MorphCategory]:
        """
        Vrácení všech možných hodnot dané mluvnické kategorie.
        
        :param morphCategory: Mluvnická kategorie.
        :type morphCategory: MorphCategories
        :param valFilter: (Volitelný) Filter, který určuje pevně stanovené 
            hodnoty, které musí mít dané pravidlo, aby se bralo v úvahu.
            Tedy není-li v daném pravidle/rozboru vůbec zminěná kategorie obsažena, tak pravidlo neprojde přes filtr.
            Příklad: Chci získat všechny rody jakých může nabývat slovo pokud je podstatným jménem.
            Nastavím filtr na: set(POS.NOUN)
            Chci získat všechny hodnoty pro slovo ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
        :type valFilter: Set[MorphCategory]
        :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
        :type notValFilter:Set[MorphCategory]
        :param groupFlags: Flagy, které musí mít daná skupina vázající se na slovo.
        :type groupFlags: Set[Flag]
        :return: Hodnoty dané mluvnické kategorie.
        :rtype: Set[MorphCategory]
        """
        pass
    
    @abstractmethod
    def getMorphs(self, valFilter: Set[MorphCategory]=set(), notValFilter: Set[MorphCategory] =set(), wordFilter: Set[MorphCategory] =set(), groupFlags:Set[Flag]=set())->Set[Tuple[MARule,str]]:
        """
        Získání tvarů.
        
        :param valFilter: (Volitelný) Filtr, který určuje pevně stanovené 
                hodnoty, které musí mít pravidlo tvaru, aby se bral v úvahu daný tvar.
                Tedy není-li v daném pravidle tvaru vůbec zminěná kategorie obsažena, tak tvar neprojde přes filtr.
                Příklad: Chci získat všechny tvary, které jsou podstatným jménem, tak
                nastavím filtr na: set(POS.NOUN)
                Chci získat všechny tvary ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
        :type valFilter: Set[MorphCategory]
        :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
        :type notValFilter:Set[MorphCategory]
        :param wordFilter: Podmínky na původní slovo. Jelikož analýza nám může říci několik variant, tak tímto filtrem můžeme
            spřesnit odhad.
            Chceme-li získat všechny tvary, které se váží na případy, kdy se předpokládá, že původní slovo mělo
            danou morfologickou kategorii, tak použijeme tento filtr.
                Příklad: Pokud je vložen 1. pád. Budou brány v úvahu jen tvary, které patří ke skupině tvarů vázajících se na případ
                že původní slovo je v 1. pádu.
        :type wordFilter: Set[MorphCategory]
        :param groupFlags: Flagy, které musí mít daná skupina vázající se na slovo.
        :type groupFlags: Set[Flag]
        :return: Množinu dvojic (pravidlo, tvar).
        :rtype: Set[Tuple[MARule,str]]
        """
        pass
    
class MorphoAnalyzer(ABC):
    """
    Interface morfologického analyzátoru.
    """
    
    @abstractmethod
    def analyze(self, word:str) -> MorphoAnalyze:
        """
        Získání morfologické analýzy slova.
        
        :param word: slovo pro analýzu
        :type word: str
        :return: Analýza slova. None při neúspěchu.
        :rtype: MorphoAnalyze 
        """
        pass

    

class MorphoAnalyzerException(ExceptionMessageCode):
    """
    Vyjímka pro problémy s morfologickým analyzátorem
    """
    pass
    
class MorphoAnalyzerLibma(object):
    """
    Obálka pro Morfologický analyzátor postavený na knihovně libma
    .. _ma: http://knot.fit.vutbr.cz/wiki/index.php/Morfologický_slovník_a_morfologický_analyzátor_pro_češtinu
    
    """
    class MAWordGroup():
        """
        Třída reprezentující skupinu slov k nějakému slovu.
        Obsahuje lemma a vzor daného slova. Také značko-pravidla pro dané slovo
        a různé tvary společně s jejich značko pravidly.
        
        Libma dělí analýzu slova na více skupin. Tato třída reprezentuje jednu ze skupin.
        Zkrácený příklad pro slovo Velké (skupina začíná <s>):
        ma><s> Velké (Sedláčková_nF)
          <l>Velká
          <c>k1gFnPc1
          <c>k1gFnPc4
          ...
          <f>[k1gFnSc7] Velkou 
          <f>[k1gFnSc4] Velkou 
          <f>[k1gFnSc5] Velká 
          <f>[k1gFnSc1] Velká 
          <f>[k1gFnSc6] Velké 
          <f>[k1gFnSc3] Velké 
          ...
        <s> Velké (Široký_nM)
          <l>Velký
          <c>k1gMnPc4
          <f>[k1gMnPc5] Velcí 
          <f>[k1gMnPc1] Velcí 
          <f>[k1gMnPc4] Velké 
          ...
        <s> Velké (velký)
          <l>velký
          <c>k2eAgFnPc1d1
          <c>k2eAgFnPc4d1
          <c>k2eAgFnPc5d1
          ...
          <f>[k2eNgNnPc4d3wH] nejnevětši 
          ...

        """
        
        def __init__(self, word):
            """
            Vytvoření skupiny pro slovo. 
            
            :param word: Slovo pro nějž je tato skupina vytvořena.
            :type word: str
            """
            self._word=word
            self._flags={Flag.NOT_GENERAL_WORD} #implicitně se nejedná o obecné slovo
            self._tagRules=[]   #značko pravidla pro slovo
            self._morphs=[] #tvary k danému slovu ve formátu dvojic (tagRule, tvar)
            
        @property
        def flags(self):
            """
            Flagy skupiny.
            """
            return self._flags

        def addFlag(self, flag:Flag):
            """
            Přidání flagu ke skupině.
            Stará se o odstraňování flagů, které jsou opakem práve přidaného flagu.
            Příklad:
                Přidávám: Flag.GENERAL_WORD
                Pokud má flag Flag.NOT_GENERAL_WORD, tak bude Flag.NOT_GENERAL_WORD odstraněn.

            :param flag: Nový flag.
            :type flag: Flag
            """
            if flag==Flag.GENERAL_WORD and Flag.NOT_GENERAL_WORD in self._flags:
                self._flags.remove(Flag.NOT_GENERAL_WORD)
            elif flag==Flag.NOT_GENERAL_WORD and Flag.GENERAL_WORD in self._flags:
                self._flags.remove(Flag.GENERAL_WORD)
                
            self._flags.add(flag)
            
        def removeFlag(self, flag:Flag):
            """
            Odstranění flagu ze skupině.

            :param flag: Flag pro odstranění.
            :type flag: Flag
            """
            self._flags.remove(flag)   
        
        @property
        def word(self):
            """
            Slovo pro nějž je tato skupina vytvořena.
            """
            return self._word

        @word.setter
        def word(self, value):
            """
            Nastavení slova pro nějž je tato skupina vytvořena.
            
            :param value: Slovo pro nějž je tato skupina vytvořena.
            :type value: str
            """
            self._word = value    
            
        def addMorph(self, tagRule, morph, relevant=False):
            """
            Přidání tvaru.
            !!!NA ZÁKLADĚ POKYNŮ JSOU NEJSOU PŘÍJMÁNY VŠECHNY HOVOROVÉ TVARY
            
            :param tagRule: Značko pravidlo pro tvar (příklad k1gFnSc7)
            :type tagRule: str
            :param morph: Tvar slova.
            :type morph: str
            :param relevant: Pokud je true, tak nepřídá daný tvar, který nevyhovuje přidaným pravidlům.
                Tvar nevyhovuje přidaným pravidlům ve skupině, máli jiné hodnoty morfologických kategorií až na
                CASE (pád). Chceme získávat všechny relevantní tvary.
               
            :type relevant: bool
            """
            rule=self.convTagRule(tagRule)
            if MorphCategories.STYLISTIC_FLAG in rule and rule[MorphCategories.STYLISTIC_FLAG]==StylisticFlag.COLLOQUIALLY:
                #nechceme hovorové
                return
            
            if relevant:
                #uživatel chce přidat jen relevantní
                for r in self._tagRules:
                    if r.sameExcept(rule, set([MorphCategories.CASE, MorphCategories.STYLISTIC_FLAG])):
                        #je stejné jako alespoň jedno pravidlo
                        self._morphs.append((rule, morph))
                        return
            else:
                self._morphs.append((rule, morph))

        def getMorphs(self, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set())->Set[Tuple[MARule,str]]:
            """
            Získání tvarů.
            
            :param valFilter: (Volitelný) Filtr, který určuje pevně stanovené 
                hodnoty, které musí mít pravidlo tvaru, aby se bral v úvahu daný tvar.
                Tedy není-li v daném pravidle tvaru vůbec zminěná kategorie obsažena, tak tvar neprojde přes filtr.
                Příklad: Chci získat všechny tvary, které jsou podstatným jménem, tak
                nastavím filtr na: dict(MorphCategories.POS: set(POS.NOUN))
                Chci získat všechny tvary ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
            :type valFilter: Set[MorphCategory]
            :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
            :type notValFilter:Set[MorphCategory]
            :return: Množinu dvojic (pravidlo, tvar).
            :rtype: Set[Tuple[MARule,str]]
            """
            
            morphs=set()
            valFilterCategories=set(f.category() for f in valFilter)
            for r, m in self._morphs:
                try:
                    if all(r[c] in valFilter for c in valFilterCategories) \
                        and all( f.category() not in r or r[f.category()]!=f for f in notValFilter):

                        #úprava velikosti počátečního písmene tvaru na základě původního slova
                        if self._word[0].isupper():
                            newM=m[0].upper()+m[1:]
                        else:
                            newM=m[0].lower()+m[1:]
                        
                        morphs.add((r,newM))
                except KeyError:
                    #neobsahuje danou mluvnickou kategorii
                    pass

            return morphs  
            
            
        @staticmethod
        def convTagRule(tagRule):
            """
            Převod značko pravidla ze str do MARule
            
            :param tagRule: Značko pravidlo (příklad k1gFnPc1)
            :type tagRule: str
            :return: Převedené pravidlo z morfologické analýzy.
            :rtype: MARule
            """
            #Příklad převodu: k1gFnPc1;jL
            #    
            #    {"k":"1","g":"F","n":"P","c":"1","note":"jL"}
            
            
            res=dict()
            note=None
            rule=tagRule.split(";")
            
            if len(rule)==2:
                note=rule[1]
                
            rule=rule[0]
                
            for i in range(0, len(rule)-1, 2):
                try:
                    mCategory=MorphCategories.fromLntrf(rule[i])
                    res[mCategory]=mCategory.createCategoryFromLntrf(rule[i+1])
                except (MorphCategoryInvalidException, MorphCategoryInvalidValueException):
                    #neznámá kategorie, či hodnota kategorie
                    #pravděpodobně se jedná o kategorii, která nás nezajíma
                    #tak to vynecháme
                    pass
                
            if note is not None:
                try:
                    mCategory=MorphCategories.NOTE
                    res[mCategory]=mCategory.createCategoryFromLntrf(note)
                except MorphCategoryInvalidValueException:
                    #neznámá hodnota kategorie/hodnoty
                    #pravděpodobně se jedná o kategorii/hodnoty, která nás nezajíma
                    #tak to vynecháme
                    pass

            return MARule(res)
        
        def addTagRuleConv(self, tagRule:MARule):
            """
            Přidání značko pravidla, které již bylo zkonvertováno pomocí convTagRule.
            
            NEPŘÍJMÁ StylisticFlag.COLLOQUIALLY
            
            :param tagRule: Značko pravidlo 
            :type tagRule: MARule
            """
            if MorphCategories.NOTE in tagRule:
                #Zkontrolujeme, zda-li aktuálně vkládané pravidlo nemá poznámku
                
                if Flag.GENERAL_WORD in self._flags:
                    #pokud ano, tak musíme tento flag odstranit.
                    self._flags.remove(Flag.GENERAL_WORD)
                    #a vrátíme implicitní
                    self._flags.add(Flag.NOT_GENERAL_WORD)
                
            
            self._tagRules.append(tagRule)
            
        def addTagRule(self, tagRule):
            """
            Přidání značko pravidla.
            
            NEPŘÍJMÁ StylisticFlag.COLLOQUIALLY
            
            :param tagRule: Značko pravidlo (příklad k1gFnPc1)
            :type tagRule: str
            """
            r=self.convTagRule(tagRule)
            if r:
                self.addTagRuleConv(r)
            
        def getAll(self, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set()) -> Dict[MorphCategories,Set[MorphCategory]]:
            """
            Vrácení všech možných hodnot mluvnických kategorií.
            
            :param valFilter: (Volitelný) Filtr, který určuje pevně stanovené 
                hodnoty, které musí mít dané pravidlo, aby se bralo v úvahu.
                Tedy není-li v daném pravidle vůbec zmíněná kategorie obsažena, tak pravidlo neprojde přes filtr.
                Příklad: Chci získat všechny rody jakých může nabývat slovo pokud je podstatným jménem.
                Nastavím filtr na: set(POS.NOUN)
                Chci získat všechny hodnoty pro slovo ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
            :type valFilter: Set[MorphCategory]
            :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
            :type notValFilter:Set[MorphCategory]
            :return: Hodnoty mluvnických kategorií.
            :rtype: Dict[MorphCategories, Set[MorphCategory]]
            """
            values={}
            
            valFilterCategories=set(f.category() for f in valFilter)
            for r in self._tagRules:
                try:
                    if all( r[c] in valFilter for c in valFilterCategories) \
                        and all( f.category() not in r or r[f.category()]!=f for f in notValFilter):
                        for morphCat, morphCatVal in r.items():
                            try:
                                values[morphCat].add(morphCatVal)
                            except KeyError:
                                #první vložení hodnoty dané kategorie
                                values[morphCat]={morphCatVal}
                                
                except KeyError:
                    #neobsahuje danou mluvnickou kategorii
                    pass

            return values  
        
        def getAllForCategory(self, morphCategory: MorphCategories, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set()) -> Set[MorphCategory]:
            """
            Vrácení všech možných hodnot mluvnické kategorie.
            
            :param morphCategory: Mluvnická kategorie.
            :type morphCategory: MorphCategories
            :param valFilter: (Volitelný) Filtr, který určuje pevně stanovené 
                hodnoty, které musí mít dané pravidlo, aby se bralo v úvahu.
                Tedy není-li v daném pravidle vůbec zminěná kategorie obsažena, tak pravidlo neprojde přes filtr.
                Příklad: Chci získat všechny rody jakých může nabývat slovo pokud je podstatným jménem.
                Nastavím filtr na: set(POS.NOUN)
                Chci získat všechny hodnoty pro slovo ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
            :type valFilter: Set[MorphCategory]
            :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
            :type notValFilter:Set[MorphCategory]
            :return: Hodnoty dané mluvnické kategorie.
            :rtype: Set[MorphCategory]
            """
            
            values=set()
            valFilterCategories=set(f.category() for f in valFilter)
            
            for r in self._tagRules:
                try:
                    if all( r[c] in valFilter for c in valFilterCategories) \
                        and all( f.category() not in r or r[f.category()]!=f for f in notValFilter):
                        values.add(r[morphCategory])
                except KeyError:
                    #neobsahuje danou mluvnickou kategorii
                    pass

            return values  
            
         
        @property
        def rules(self):
            """
            Přiřazená pravidla
            """
            return self._tagRules
            
        def __str__(self):
            s="Tag rules:\n"
            for tr in self._tagRules:
                s+="\t"+str(tr)+"\n"
            s+="Flags:\n"
            for f in self._flags:
                s+="\t"+str(f)+"\n"
            s+="Morphs:\n"
            for m in self._morphs:
                s+="\t"+str(m)+"\n"
                
            return s
                
                
    class MAWord(MorphoAnalyze):
        """
        Obsahuje data z morfologické analýzy slova.
        """
        
        def __init__(self):
            """
            Vytvoření instance morfologické analýzy slova.

            """
            self._groups=[]
            
        
        def addGroup(self, group):
            """
            Přidání skupiny z morfoligické analýzy.
            
            :param group: Skupina z analýzy obsahující vzor, lemma, tvary, značko-pravidla
            :type group: MorphoAnalyzerLibma.MAWordGroup
            """
            self._groups.append(group)
            
        def delGroup(self, group):
            """
            Smaže danou skupinu.
            
            :param group: Skupina, které bude smazána.
            :type group:MorphoAnalyzerLibma.MAWordGroup
            """
            
            self._groups.remove(group)
            
        def getAll(self, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set(), groupFlags:Set[Flag]=set()) -> Dict[MorphCategories,Set[MorphCategory]]:
            """
            Vrácení všech možných hodnot mluvnických kategorií. Ve všech skupinách
            získaných při analýze slova.
            
            :param valFilter: (Volitelný) Filtr, který určuje pevně stanovené 
                hodnoty, které musí mít dané pravidlo, aby se bralo v úvahu.
                Tedy není-li v daném pravidle vůbec zmíněná kategorie obsažena, tak pravidlo neprojde přes filtr.
                Příklad: Chci získat všechny rody jakých může nabývat slovo pokud je podstatným jménem.
                Nastavím filtr na: set(POS.NOUN)
                Chci získat všechny hodnoty pro slovo ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
            :type valFilter: Set[MorphCategory]
            :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
            :type notValFilter:Set[MorphCategory]
            :param groupFlags: Flagy, které musí mít daná skupina vázající se na slovo.
            :type groupFlags: Set[Flag]
            :return: Hodnoty mluvnických kategorií.
            :rtype: Dict[MorphCategories, Set[MorphCategory]]
            """
            values={}
            
            
            
            for g in self._groups:
                if len(g.flags & groupFlags)==len(groupFlags):
                    #má všechny flagy
                
                    for morphCat, morphCatValues in g.getAll(valFilter, notValFilter).items():
                        try:
                            values[morphCat]=values[morphCat] | morphCatValues
                        except KeyError:
                            #první vložení hodnoty dané kategorie
                            values[morphCat]=morphCatValues

            return values

        
        def getAllForCategory(self, morphCategory: MorphCategories, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set(), groupFlags:Set[Flag]=set()) -> Set[MorphCategory]:
            """
            Vrácení všech možných hodnot dané mluvnické kategorie. Ve všech skupinách
            získaných při analýze slova.
            
            :param morphCategory: Mluvnická kategorie.
            :type morphCategory: MorphCategories
            :param valFilter: (Volitelný) Filter, který určuje pevně stanovené 
                hodnoty, které musí mít dané pravidlo, aby se bralo v úvahu.
                Tedy není-li v daném pravidle vůbec zminěná kategorie obsažena, tak pravidlo neprojde přes filtr.
                Příklad: Chci získat všechny rody jakých může nabývat slovo pokud je podstatným jménem.
                Nastavím filtr na: set(POS.NOUN)
                Chci získat všechny hodnoty pro slovo ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
            :type valFilter: Set[MorphCategory]
            :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
            :type notValFilter:Set[MorphCategory]
            :param groupFlags: Flagy, které musí mít daná skupina vázající se na slovo.
            :type groupFlags: Set[Flag]
            :return: Hodnoty dané mluvnické kategorie.
            :rtype: Set[MorphCategory]
            """
            
            values=set()
            
            for g in self._groups:
                if len(g.flags & groupFlags)==len(groupFlags):
                    #má všechny flagy
                    values |= g.getAllForCategory(morphCategory, valFilter, notValFilter)

            return values
        
        def getMorphs(self, valFilter: Set[MorphCategory] =set(), notValFilter: Set[MorphCategory] =set(), wordFilter: Set[MorphCategory] =set(), groupFlags:Set[Flag]=set())->Set[Tuple[MARule,str]]:
            """
            Získání tvarů.
            
            :param valFilter: (Volitelný) Filtr, který určuje pevně stanovené 
                hodnoty, které musí mít pravidlo tvaru, aby se bral v úvahu daný tvar.
                Tedy není-li v daném pravidle tvaru vůbec zminěná kategorie obsažena, tak tvar neprojde přes filtr.
                Příklad: Chci získat všechny tvary, které jsou podstatným jménem, tak
                nastavím filtr na: dict(MorphCategories.POS: set(POS.NOUN))
                Chci získat všechny tvary ve středním a ženském rodě: set(Gender.NEUTER, Gender.FEMINE)
            :type valFilter: Set[MorphCategory]
            :param notValFilter: Stejné jako valFilter s tím rozdílem, že dané hodnoty nesmí pravidlo tvaru obsahovat.
            :type notValFilter:Set[MorphCategory]
            :param wordFilter: Podmínky na původní slovo. Jelikož analýza nám může říci několik variant, tak tímto filtrem můžeme
                spřesnit odhad.
                Chceme-li získat všechny tvary, které se váží na případy, kdy se předpokládá, že původní slovo mělo
                danou morfologickou kategorii, tak použijeme tento filtr.
                    Příklad: Pokud je vložen 1. pád. Budou brány v úvahu jen tvary, které patří ke skupině tvarů vázajících se na případ
                    že původní slovo je v 1. pádu.
            :type wordFilter: Set[MorphCategory]
            :param groupFlags: Flagy, které musí mít daná skupina vázající se na slovo.
            :type groupFlags: Set[Flag]
            :return: Množinu dvojic (pravidlo, tvar).
            :rtype: Set[Tuple[MARule,str]]
            """
            morphs=set()
            
            for g in self._groups:
                
                if len(g.flags & groupFlags)==len(groupFlags):
                    #má všechny flagy
                    if len(g.getAll(wordFilter)):
                        morphs |= g.getMorphs(valFilter, notValFilter)
                
            return morphs  
            
        
        @property
        def groups(self):
            """
            Skupiny z morfologické analýzy.
            
            :rtype: List(MAWordGroup)
            """
            
            return self._groups
        
        def __str__(self):
            s=""
            for g in self._groups:
                s+=str(g)
            s+="----------"
            return s
            
    
    def __init__(self, pathToMa, words, hint=None):
        """
        Provede vytvoření objektu Morfologického analyzátoru.
        Spustí nad všemy slovy z words morfologický analyzátor s parametry:
            -F vrací všechny možné tvary.
            -m Na výstup se vypíše flektivní analýza zadaného slova.
        Výsledek si poté načte a bude sloužit jako databáze, která bude použita pro získávání informací
        o slovech.
        
        :param pathToMa: Cesta/ příkaz pro spuštění morfologického analyzátoru.
        :type pathToMa: str
        :param resultsFilePath: Cesta k souboru, kde bude uložen výsledek z morfologického analyzátoru
        :type resultsFilePath: str
        :param words: Slova, která budou předložena analyzátoru a vysledek budou sloužit jako databáze
            pro tuto obálku. Objekt bude tedy znát nanejvýše tato slova.
        :type words: set(str)
        :param hint: Volitelný parametr, který dává nápovědu k hodnotě morfologické kategorie slova.
            Například pokud víme, že slovo je v prním pádu, tak použijeme tento parametr k odfiltrování dalších možností.
            Pokud je předán set, platí nápověda pro všechny slova stejná. Pokud je předán Dict, tak pro každé slovo je jiná (klíč udává slovo pro nějž nápověda platí).
            Pozor pokud se daná morfologická kategorie vůbec v analýze slova nevyskytuj, pak je nápověda ignorována.
        :type hint: :Set[MorphCategory] | Dict[MorphCategory]
        :raise MorphoAnalyzerException: Chyba analyzátoru.
        """
        self._hint=hint
        #vytvoříme novou prázdnou databázi slov
        self._wordDatabase={}
        
        self._pathToMa=pathToMa
        
        #získání informací o slovech
        words=list(words)
        self.__commWithMA(words)
        
        #určíme všechna slova obsahující pouze velká písmena, která jsou dlouhá alespoň dva znaky
        for w in words:
            if len(w)>=2 and w.isupper():
                g=self.MAWordGroup(w)
                g.lemma=w
                
                g.addTagRule(POS.ABBREVIATION.lntrf) 
                g.addMorph(POS.ABBREVIATION.lntrf, w)
                try:
                    self._wordDatabase[w].addGroup(g)
                except KeyError:
                    #slovo zatím není v databázi
                    self._wordDatabase[w]=self.MAWord()
                    self._wordDatabase[w].addGroup(g)
            
        #přidáme ke slovům von, da a de
        #analýzu, že se jedná o předložky za nimiž se slova ohýbají
        for w in ["von", "da", "de"]:
            g=self.MAWordGroup(w)
            g.lemma=w

            g.addTagRule(POS.PREPOSITION_M.lntrf) 
            g.addMorph(POS.PREPOSITION_M.lntrf, w)
            try:
                self._wordDatabase[w].addGroup(g)
            except KeyError:
                #slovo zatím není v databázi
                self._wordDatabase[w]=self.MAWord()
                self._wordDatabase[w].addGroup(g)
               
        #pro nás je a pouze spojka
        try:
            ma=self._wordDatabase["a"]

            delGroups=[group for group in ma.groups if group.rules[0][MorphCategories.POS]!=POS.CONJUNCTION]

            for g in delGroups:
                ma.delGroup(g)
  
        except KeyError:
            pass
        
        #vynecháváme, protože v našem případě nemůžou být písmena podstatným jménem
        for c in string.ascii_lowercase:
            try:
                ma=self._wordDatabase[c]

                for group in ma.groups:
                    if group.rules[0][MorphCategories.NOTE]==Note.CHARACTER_AS_NOUN:
                        ma.delGroup(group)
                        break   #předpokládáme pouze jednu skupinu
                        
            except KeyError:
                pass

    def __commWithMA(self, words):
        """
        Pošle ma slova, která mají být analyzována.
        
        :param words: Slova pro analýzu
        :type words:List[str]
        :raise MorphoAnalyzerException: Chyba analyzátoru.
        """
        
        
        p = Popen([self._pathToMa, "-F", "-m", "-n"], stdin=PIPE, stdout=PIPE, stderr=None)
                
        output, _ = p.communicate(str.encode(("\n".join(words))+"\n")) #vrací stdout a stderr
        
        #zkontrolujeme návratový kód
        if p.returncode!=0:
            #selhání analyzátoru
            raise MorphoAnalyzerException(ErrorMessenger.CODE_MA_FAILURE)
        

        retWords=self._parseMaOutput(output.decode())

        if retWords!=len(words):

            #nemáme všechna slova
            #zřejmě byl pro komunikaci výstup příliš velký pokusíme se poslat méně slov
            if len(words)==1:
                #Níž nelze. Vynecháme toto slovo. Není pravděpodobné, že by jedno slovo mělo tak příliš velký výstup
                #zřejmě se spíše jedná o nevhodné slovo pro ma. Jako je například slovo . (tečka).
                return
            
            origCnt=len(words)
            words=words[retWords:]#zbavíme se již zpracovaných
            
            partSize=math.ceil(len(words)/2)
            logging.info("\tPři komunikaci s ma došlo ke ztrátě slov (odesláno: "+str(origCnt)+", přijato: "+str(retWords)+"). Pokusím se o komunikaci znovu s menším počtem slov: "+\
                         str(origCnt)+" -> "+str(partSize)+".")
            for offset in range(0, len(words), partSize):
                self.__commWithMA(words[offset:offset+partSize])
            
        
        
    def _parseMaOutput(self, output):
        """
        Provede analýzu výstupu z ma a uloží získané informace do databáze.
        
        :param output: Výstup z analyzátoru.
        :type output: str
        :return: Počet získaných slov. (i nezpracovaných ma>--not found)
        :rtype: int
        """

        actWordGroup=None   #obsahuje data k aktuálně parsované skupině
        cntUnWords=0
        wordsInDBAtStart=len(self._wordDatabase)
        for line in output.splitlines():
            if line=="ma>--not found":
                #máme další slovo, ale nezpracované
                cntUnWords+=1
                continue
            
            #rozdělení řádku
            parts=line.strip().split()
                
            if parts[0][-3:]=="<s>":
                #začínáme číst novou skupinu slova
                #<s> vstupní slovo (vzor 1)
                    
                #byla předešlá skupina k něčemu dobrá?
                if actWordGroup is not None and len(actWordGroup.rules)==0:
                    #ne nebyla, tak ji odstraníme
                    self._wordDatabase[actWordGroup.word].delGroup(actWordGroup)
                
                #vytvoříme skupinu
                actWordGroup=self.MAWordGroup(parts[1])
                    
                try:
                    #vložíme skupinu do analýzy slova
                    self._wordDatabase[parts[1]].addGroup(actWordGroup)
                except KeyError:
                    #nové slovo
                    #vytvoříme objekt pro uložení morfologické analýzy slova
                    self._wordDatabase[parts[1]]=self.MAWord()
                    #a znovu vložíme
                    self._wordDatabase[parts[1]].addGroup(actWordGroup)
                
            elif parts[0][:3]=="<c>":
                #značko pravidlo, které sedí pro dané slovo
                
                if isinstance(self._hint, dict) or isinstance(self._hint, set):
                    #aplikujeme nápovědu
                    convRule=self.MAWordGroup.convTagRule(parts[0][3:])
                    
                    hint=self._hint[actWordGroup.word] if isinstance(self._hint, dict) else self._hint
                    if all( f.category() not in convRule or convRule[f.category()]==f for f in hint):
                        actWordGroup.addTagRuleConv(convRule)
                else:
                    actWordGroup.addTagRule(parts[0][3:])
            elif parts[0][:3]=="<l>":
                #lemma slova
                if parts[0][3:][0].islower():
                    #malé první písmeno u lematu
                    #nastavujeme jako obecné slovo
                    #pokud se dále ukáže, že má tato skupina poznámku, pak bude
                    #tento flag odstraněn samotným objektem třídy MAWordGroup.
                    actWordGroup.addFlag(Flag.GENERAL_WORD)
                
                
            elif parts[0][:3]=="<f>":
                #Přidání tvaru slova
                #pouze pokud je relevantní k znočko pravidlům, které sedí na dané slovo.
                #Tento požadavek si můžeme dovolit, jelikoř v tuto dobu by měly být zpracovány
                #všechny <c> řádky.
                actWordGroup.addMorph((parts[0][3:])[1:-1], parts[1], True)
                
        
        #byla předešlá skupina k něčemu dobrá?
        if actWordGroup is not None and len(actWordGroup.rules)==0:
            #nebyla
            self._wordDatabase[actWordGroup.word].delGroup(actWordGroup)
            
        return cntUnWords+len(self._wordDatabase)-wordsInDBAtStart
    
    def analyze(self, word):
        """
        Získání kompletních znalostí o slově. Slovo by mělo být 
        jedním ze slov předaných v konstruktoru.
        
        :param word: slovo pro analýzu
        :type word: str
        :return: Analýza slova. None pokud není slovo v databázi.
        :rtype: MAWord 
        """
        
        
        try:
            return self._wordDatabase[word]
        except KeyError:
            return None

    