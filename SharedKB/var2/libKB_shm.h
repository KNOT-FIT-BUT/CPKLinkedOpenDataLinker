/* -*- coding: utf-8 -*- */
/*
Copyright 2014 Brno University of Technology

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
/*
 * Soubor:  libKB_shm.h
 * Datum:   2013/08/29
 * Autor:   Jan Doležal, xdolez52@stud.fit.vutbr.cz
 * Projekt: Decipher - Knowledge Base daemon
 * Popis:   Program ze souboru načte matici stringů,
 *          drží ji efektivně v paměti a efektivně v ní hledá
 *          a tuto paměť sdílí read-only pro další programy.
 */
/**
 * @file	libKB_shm.h
 * @date	2013/08/29
 * @author	Jan Doležal, xdolez52@stud.fit.vutbr.cz
 * @brief	Decipher - Knowledge Base daemon
 */

#ifndef KB_SHM_H
#define KB_SHM_H

// práce se vstupem/výstupem
#include <stdio.h>

// obecné funkce jazyka C
#include <stdlib.h>
#include <stdbool.h>

// kvůli funkci strtoul a dalších
#include <string.h>

// ošetření přetečení
#include <limits.h>

// proměnná errno
#include <errno.h>
#include <assert.h>

// často potřebný hlavičkový soubor
#include <unistd.h>

#define VERSION_SIZE 20

/*       _\|/_
         (o o)
 +----oOO-{_}-OOo----+
 | Makra             |
 +------------------*/
#define FREE(pointer) { free(pointer); pointer = NULL; }

#define ERROR(message) \
  fprintf(stderr,"%s (%s:%s:%d)\n",(message),__FILE__,__func__,__LINE__)

#define OFFSET_GIVE(origin, pointer) ( (void *)((size_t)(pointer) - (size_t)(origin)) )
#define OFFSET_2_P(pointer, offset) ( (void *)((size_t)(pointer) + (size_t)(offset)) )

/*       _\|/_
         (o o)
 +----oOO-{_}-OOo----+
 | Globální proměnné |
 +------------------*/
extern char *KB_shm_name;

/*       _\|/_
         (o o)
 +----oOO-{_}-OOo-----------+
 | Struktury a výčtové typy |
 +-------------------------*/
typedef unsigned short TStrLen;
typedef struct SKBStringVector KBStringVector;
typedef struct SKBString KBString;

struct SKBString {
	char *str;
	TStrLen length;
	TStrLen *offsets;
	TStrLen num_offsets;
	
	bool is_offset; /// určuje zda-li ukazatele uvnitř jsou offsety.
};

/**
 * Struktura držící vektor typu KBString
 */
struct SKBStringVector {
	KBString *array;
	
	bool is_offset; /// určuje zda-li ukazatele uvnitř jsou offsety.
	unsigned length;
	unsigned capacity;
};

/**
 * Sdílená paměť
 * Ve sdílené paměti mají všechny ukazatele funkci offsetu od začátku sdílené paměti.
 */
typedef struct {
	KBStringVector head;
	KBStringVector data;
	size_t capacity;
	char * version;
} KBSharedMem;

/*       _\|/_
         (o o)
 +----oOO-{_}-OOo---------------------------+
 | Následují funkce pro typ KBStringVector. |
 +-----------------------------------------*/
/**
 * Vrací ukazatel na \a n prvek v poli KBStringVector \a vector.
 */
KBString * KBStringVectorAt(KBStringVector *vector, unsigned n);

/**
 * Vrací ukazatel na sloupec \a col řetězce \a n -tého prvku v poli KBStringVector \a vector.
 */
char * KBStringVectorDataAt(KBStringVector *vector, unsigned n, TStrLen col);

/*       _\|/_
         (o o)
 +----oOO-{_}-OOo---------------------+
 | Následují funkce pro typ KBString. |
 +-----------------------------------*/
/**
 * Vrací ukazatel na offset řětězce v \a kb_str podle \a offset.
 */
char * KBStringAt(KBString *kb_str, TStrLen offset);

/*       _\|/_
         (o o)
 +----oOO-{_}-OOo------------------------+
 | Následují funkce pro typ KBSharedMem. |
 +--------------------------------------*/
/**
 * Číslování řádků a sloupců od 1.
 * Vrací sloupec \a col hlavičky na řádku \a line.
 */
char * KBSharedMemHeadAt(KBSharedMem *kb, unsigned line, TStrLen col);

/**
 * Číslování sloupců od 1.
 * Vrací sloupec \a col hlavičky podle prefixu \a prefix.
 */
char * KBSharedMemHeadFor(KBSharedMem *kb, char prefix, TStrLen col);

/**
 * Číslování sloupců od 1.
 * Pokud je parametr \a line != NULL, zapíše se do něj řádek, na kterém se nachází onen prefix.
 * Vrací sloupec \a col hlavičky podle prefixu \a prefix.
 */
char * KBSharedMemHeadFor_Boost(KBSharedMem *kb, char prefix, TStrLen col, unsigned *line);

/**
 * Číslování řádků a sloupců od 1.
 * Vrací sloupec \a col dat na řádku \a line.
 */
char * KBSharedMemDataAt(KBSharedMem *kb, unsigned line, TStrLen col);

/**
 * Vrací verzi \a kb.
 */
char * KBSharedMemVersion(KBSharedMem *kb);

/*       _\|/_
         (o o)
 +----oOO-{_}-OOo------------+
 | Následují ostatní funkce. |
 +--------------------------*/

// Pro jazyky C/C++
/**
 * Připojí sdílenou paměť READ_ONLY do \a dest a do \a KB_shm_fd uloží file descriptor.
 * @return Pokud vše proběhlo v pořádku vrací 0, jinak číslo != 0.
 */
int connectKBSharedMem(KBSharedMem **dest, int *KB_shm_fd, char *kb_shm_name);

/**
 * Odpojí (odmapuje) sdílenou paměť na \a dest, zavře file descriptor \a KB_shm_fd.
 * Po odpojení \a dest = NULL a \a KB_shm_fd = -1.
 * @return Pokud vše proběhlo v pořádku vrací 0, jinak číslo != 0.
 */
int disconnectKBSharedMem(KBSharedMem **dest, int *KB_shm_fd);

// Pro jazyky Java, Python, ...
/**
 * Zkontroluje zda je sdílená paměť k dispozici.
 * @return Pokud ano vrací 0, jinak číslo != 0.
 */
int checkKB_shm(char *kb_shm_name);

/**
 * Připojí sdílenou paměť READ_ONLY.
 * @return Pokud vše proběhlo v pořádku vrací nezáporný file descriptor, při chybě vrací -1.
 */
int connectKB_shm(char *kb_shm_name);

/**
 * Namapuje sdílenou paměť READ_ONLY.
 * @return Pokud vše proběhlo v pořádku vrací ukazatel do namapované paměti, při chybě vrací NULL.
 */
KBSharedMem *mmapKB_shm(int KB_shm_fd);

/**
 * Odpojí (odmapuje) sdílenou paměť na \a dest a zavře file descriptor \a KB_shm_fd.
 * Parametr \a dest může být NULL.
 * @return Pokud vše proběhlo v pořádku vrací 0, jinak číslo != 0.
 */
int disconnectKB_shm(KBSharedMem *dest, int KB_shm_fd);

/**
 * Otevře textový soubor \a KB_path s KB a pokusí se přečíst jeho verzi.
 * @return Pokud vše proběhlo v pořádku vrací číslo verze, jinak prázdný řetězec.
 */
char * getVersionFromSrc(char *KB_path);

/**
 * Otevře binární soubor \a KB_bin_path s KB a pokusí se přečíst jeho verzi.
 * @return Pokud vše proběhlo v pořádku vrací číslo verze, jinak prázdný řetězec.
 */
char * getVersionFromBin(char *KB_bin_path);

#endif
/* konec souboru libKB_shm.h */
