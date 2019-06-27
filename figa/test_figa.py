#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4 softtabstop=4 expandtab shiftwidth=4

# ***********************************************
# * Soubor:  test_figa.py                       *
# * Datum:   2019-06-26                         *
# * Autor:   Jan Doležal, idolezal@fit.vutbr.cz *
# ***********************************************

# ====== IMPORTY ======

import argparse
import collections

import linecache, inspect

import sources.marker as figa

# ====== GLOBÁLNÍ KONSTANTY ======

# ====== GLOBÁLNÍ PROMĚNNÉ ======

# ====== FUNKCE A TŘÍDY ======

NamelistLine = collections.namedtuple("NamelistLine", "fragment kb_rows")

def parseNamelistLine(raw_namelist_line):
    """
    Parsuje řádky souboru "namelist".

    Syntax řádku souboru "namelist" v Backusově-Naurově formě (BNF):
        <řádek> ::= <fragment> "\t" <odpovídající čísla řádků v KB> "\n"
        <odpovídající čísla řádků v KB> ::= <int> | <int> ";" <odpovídající čísla řádků v KB> | "N"
    kde:
        <čísla řádků do KB> odkazují na řádky ve znalostní bázi s entitami, jenž mají mezi atributy <fragment> (řádek N značí část jména)
    """
    
    fragment, raw_kb_rows = raw_namelist_line.rstrip("\n").split("\t")
    kb_rows = []
    for i in raw_kb_rows.split(";"):
        if i == "N":
            kb_rows.append(0)
        else:
            kb_rows.append(int(i))
    parsed_namelist_line = NamelistLine(fragment, set(kb_rows))
    return parsed_namelist_line

FigaOutput = collections.namedtuple("FigaOutput", "kb_rows start_offset end_offset fragment flag")

def parseFigaOutput(raw_figa_output):
    """
    Parsuje výstup z figy.

    Syntax výstupního formátu v Backusově-Naurově formě (BNF):
        <výstup Figa> :== <řádek výstupu>
            | <řádek výstupu> <výstup Figa>
        <řádek výstupu> :== <čísla řádků do KB> "\t" <počáteční offset>
                "\t" <koncový offset> "\t" <fragment> "\t" <příznak> "\n"
        <čísla řádků do KB> :== <číslo>
            | <číslo> ";" <čísla řádků do KB>
    kde:
        <čísla řádků do KB> odkazují na řádky ve znalostní bázi s entitami, jenž mají mezi atributy <fragment> (řádek 0 značí zájmeno – coreference)
        <počáteční offset> a <koncový offset> jsou pozice prvního a posledního znaku řetězce <fragment> (na pozici 1 leží první znak vstupního textu) – to je třeba upravit, aby šlo využít přímo input[start_offset:end_offset]
        <příznak> může nabývat dvou hodnot: F – fragment plně odpovídá atributu odkazovaných entit; S – byl tolerován překlep ve fragmentu
    """

    # Formát "číslo_řádku[;číslo_řádku]\tpočáteční_offset\tkoncový_offset\tnázev_entity\tF"
    for line in raw_figa_output.split("\n"):
        if line != "":
            kb_rows, start_offset, end_offset, fragment, flag = line.split("\t")
            yield FigaOutput(set(map(int, kb_rows.split(";"))), int(start_offset)-1, int(end_offset), fragment, flag) # Figa má start_offset+1 (end_offset má dobře).

# ====== MAIN ======

def argParse():
    """
    Zpracování parametrů příkazového řádku
    """
    
    parser = argparse.ArgumentParser(
        description = "Reflexivní test nástroje Figa pomocí souboru \"namelist\" a dle něj vygenerovaného slovníku \"automata.dct\""
    )
    
    parser.add_argument("namelist",
        type = str,
        help = ("Cesta k souboru \"namelist\".")
    )
    
    parser.add_argument("figa_dict",
        type = str,
        help = ("Cesta ke slovníku vygenerovaného ze souboru \"namelist\".")
    )
    
    arguments = parser.parse_args()
    
    return arguments

def main():
    """
    Hlavní funkce volána při spuštění
    """
    
    # == Zpracování parametrů příkazového řádku ==
    arguments = argParse()
    
    # == Načtení slovníku do nástroje Figa ==
    figa_handler = figa.marker()
    figa_handler.load_dict(arguments.figa_dict)
    
    # == Testovnání nástroje Figa pomocí souboru "namelist" ==
    with open(arguments.namelist) as fp:
        error_cnt = 0
        error_str = ""
        for raw_namelist_line in fp:
            # Parsování řádků ze souboru "namelist"
            if raw_namelist_line.rstrip("\n") != "":
                parsed_namelist_line = parseNamelistLine(raw_namelist_line)
            else:
                continue
            
            # Parsování výstupu z nástroje Figa
            input_string = parsed_namelist_line.fragment
            raw_figa_output = figa_handler.lookup_string(input_string)
            parsed_figa_output = list(parseFigaOutput(raw_figa_output))
            
            # Porovnání řádku ze souboru "namelist" a výstupu z nástroje Figa
            ok = True
            if not (len(parsed_figa_output) == 1):
                # * Pokud nemáme povolený overlap, měl by být výstup právě jeden
                ok = False
                error_str = linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-3).strip()
            elif not (parsed_figa_output[0].start_offset == 0 and len(input_string.decode("utf-8")) == parsed_figa_output[0].end_offset):
                # * Vstupní fragment by měl odpovídat fragmentu z výstupu nástroje Figa (alespoň délkou)
                ok = False
                error_str = linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-3).strip()
            elif not (parsed_figa_output[0].kb_rows == parsed_namelist_line.kb_rows):
                # * Řádky KB by měli odpovídat
                ok = False
                error_str = linecache.getline(__file__, inspect.getlineno(inspect.currentframe())-3).strip()
            
            if not ok:
                error_cnt += 1
                print("=== err. %s ===" % error_cnt)
                print(error_str)
                print("<<<<<<<<<")
                print("NamelistLine(fragment='%s', kb_rows=%s)" % parsed_namelist_line)
                print("---------")
                for line in parsed_figa_output:
                    print("FigaOutput(kb_rows=%s, start_offset=%s, end_offset=%s, fragment='%s', flag='%s')" % line)
                print(">>>>>>>>>")

if __name__ == "__main__":
    main()

# konec souboru test_figa.py
