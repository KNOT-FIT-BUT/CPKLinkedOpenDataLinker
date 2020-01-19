#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Copyright 2015 Brno University of Technology

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# Author: Tomas Ondrus, xondru04@stud.fit.vutbr.cz
# Author: Jan Cerny, xcerny62@stud.fit.vutbr.cz
# Author: Lubomir Otrusina, iotrusina@fit.vutbr.cz
#
# Description: Merges two Knowledge Bases together.

import argparse
import sys
import time
import hashlib

class KB(object):
    '''
    Class representing Knowledge Base.
    '''

    def __init__(self, KB_file_name, KB_fields_file_name, separator):
        '''
        KB_file_name - file name of a KB
        KB_fields_file_name - file name of config for a KB
        separator - multiple values separator used in a KB
        '''

        self.name = KB_file_name
        if KB_fields_file_name == None: 
            self.fields_file_name = KB_file_name + ".fields"
        else:
            self.fields_file_name = KB_fields_file_name
        self.separator = separator

    def load_config(self):
        '''
        Loads a config file with fields description (*.fields) for a given KB.
        '''

        try:
            fields_fd = open(self.fields_file_name, 'r')
        except IOError:
            sys.stderr.write("Cannot open file " + self.fields_file_name + ".\n")
            sys.exit(1)
        self.fields = dict()
        line_number = 0
        POSTFIX_LEN = len(" (MULTIPLE VALUES)")
        for line in fields_fd: 
            line = line.strip()
            if (not line): # skips empty lines
                continue
            if (line.endswith(" (MULTIPLE VALUES)")):
                self.fields[self.name + "." + line[:-POSTFIX_LEN]] = Field(line_number, True)
            else:
                self.fields[self.name + "." + line] = Field(line_number, False)
            line_number += 1
        self.field_count = len(self.fields)
        fields_fd.close()

    def load_to_memory(self):
        '''
        Loads KB into memory.
        '''

        try:
            kb_fd = open(self.name, "r")
        except IOError:
            sys.stderr.write("Cannot open file " + self.name + ".\n")
            sys.exit(1)
        self.entities = list()
        for line in kb_fd:
            self.entities.append(Entity(line, self.separator, self.field_count))
        kb_fd.close()

    def get_field_order_num(self, field_name):
        '''
        Returns a position for a given field named field_name.
        '''

        return self.fields[field_name].order_num

class Field(object):
    '''
    Class for a value from *.fields config file.
    '''

    def __init__(self, order_num, multiple):
        self.order_num = order_num
        self.multiple  = multiple

class Entity(object):
    """
    Data line container.
    """

    def __init__(self, line, separator, field_count):
        self.data    = line.split("\t")
        self.weight  = 0
        self.used  = False
        self.matched = None
        for i in range(field_count):
            self.data[i] = self.data[i].split(separator)
            for j in range(len(self.data[i])):
                self.data[i][j] = self.data[i][j].strip()
            self.data[i] = set(self.data[i])
            if '' in self.data[i]:
                self.data[i].remove('')
            self.data[i] = tuple(self.data[i])
        self.data = tuple(self.data)

    def get_field(self, order_num):
        return self.data[order_num]

UNIQUE = 1
NAME = 2
OTHER = 3

class Relation(object):
    '''
    Class for a relation between 1st and 2nd KB.
    '''

    def __init__(self, n1, n2, rel_type):
        self.kb1_field = n1
        self.kb2_field = n2
        self.type = rel_type

def parse_relations(rel_conf_file_name, kb1, kb2):
    '''
    Loads relations between the KBs from config a file.

    rel_conf_file_name - name of the file with relation configuration
    kb1 - 1st KB
    kb2 - 2nd KB
    '''

    try:
        rel_fd = open(rel_conf_file_name, 'r')
    except IOError:
        sys.stderr.write("Cannot open file " + rel_conf_file_name + ".\n")
        sys.exit(1)
    relations = list()
    rel_type = 0
    for line in rel_fd:
        if not line:
            pass
        elif line.startswith("UNIQUE:"):
            rel_type = UNIQUE
        elif line.startswith("NAME:"):
            rel_type = NAME
        elif line.startswith("OTHER:"):
            rel_type = OTHER
        elif line.startswith("\t"):
            line = line.strip()
            first,second = line.split('=')
            if first.startswith(kb2.name):
                (first, second) = (second, first)
            fieldnum1 = kb1.get_field_order_num(first)
            fieldnum2 = kb2.get_field_order_num(second)
            relations.append(Relation(fieldnum1, fieldnum2, rel_type))
        else:
            sys.stderr.write("Invalid format of the config file " + rel_conf_file_name + ".\n")
            exit(1)
    rel_fd.close()
    return relations

def make_index(kb2_entities, kb2_field_count, relations):
    '''
    Creates an index over the 2nd KB.
    The index is used to speed up searching over the KB.
    '''

    # determines which fields will be indexed
    fields_to_index = list()
    for relation in relations:
        if relation.type != OTHER:
            fields_to_index.append(relation.kb2_field)
    fields_to_index = set(fields_to_index)

    index = [x for x in range(kb2_field_count + 1)]

    # fulfills dicts with default empty dict
    for field in fields_to_index:
        index[field] = dict()

    # iterates over KB lines and add terms to index
    for entity in kb2_entities:
        for field in fields_to_index:
            value = entity.get_field(field)
            if (not value): # skips empty value
                continue
            for one_value in value:
                if (index[field].get(one_value) is None):
                    index[field][one_value] = [entity] # saves reference
                else:
                    index[field][one_value].append(entity)
    return index

def get_args():
    """
    Parses arguments of the program. Returns an object of class argparse.Namespace.
    """ 

    parser = argparse.ArgumentParser(
        description="Compare two different Knowledge Bases.")
    parser.add_argument("--first",
        help="filename of the first KB (also used as a prefix for config files)",
        required=True)
    parser.add_argument("--second",
        help="filename of the second KB (also used as a prefix for config files)",
        required=True)
    parser.add_argument("--first_fields",
        help="filename of the first KB fields list (default '(--first option).fields')")
    parser.add_argument("--second_fields",
        help="filename of the second KB fields list (default '(--second option).fields')")
    parser.add_argument("--rel_conf",
        help="filename of a relationships config",
        required=True)
    parser.add_argument("--output_conf",
        help="filename of an output format")
    parser.add_argument("--other_output_conf",
        help="filename of an output format")
    parser.add_argument("--first_sep",
        help="first multiple value separator (default '|')",
        default="|")
    parser.add_argument("--second_sep",
        help="second multiple value separator (default '|')",
        default="|")
    parser.add_argument("--id_prefix",
        help="prefix for ids")
    parser.add_argument("--output",
        help="filename of an output")  
    parser.add_argument("--second_output",
        help="filename of output of rest not matched from second KB")
    parser.add_argument("--treshold",
        help="matching treshold")
    return parser.parse_args()

def match(kb1, index, relations, treshold):
    '''
    Matches items from the 2nd KB with the corresponding items from the 1st KB.
    '''

    # dividing relations into three list according the type
    unique_relations = list()
    name_relations = list()
    other_relations = list()
    for x in relations:
        if x.type == UNIQUE:
            unique_relations.append(x)
        elif x.type == NAME:
            name_relations.append(x)
        else:
            other_relations.append(x)

    # going through entities from the 1st KB
    for entity in kb1.entities:

        # first, searching for a corresponding entry from the 2nd KB based on unique ids
        match = match_by_unique(entity, index, unique_relations)
        if match is not None:
            entity.matched = match
            match.used = True # marked as used (can be used only once)
            entity.used = True
            continue  # process another entry from KB

        # second, searching for a corresponding entry from the 2nd KB based on names (aliases, ...)
        candidates = match_by_name(entity, index, name_relations)
        if not candidates:
            continue

        # getting score for each candidate
        for candidate in candidates:
            for relation in unique_relations:
                first = entity.get_field(relation.kb1_field)
                second = candidate.get_field(relation.kb2_field)
                if first and second and first[0] != second[0]:
                    candidate.weight = -1000
                    break

            # evaluating in name_relations was performed during the match_by_name function call
            if (candidate.weight < treshold): 
                continue
            for relation in other_relations:
                first = entity.get_field(relation.kb1_field)
                second = candidate.get_field(relation.kb2_field)
                for i in first:
                    for j in second:
                        try: # if string contains a number, the number will be rounded 
                            i = round(float(i), 1)
                        except:
                            pass
                        try:
                            j = round(float(j), 1)
                        except:
                            pass
                        if i == j:
                            candidate.weight += 1

        # choosing the best candidate (the one with the highest score)
        if candidates:
            best = candidates[0]
            for candidate in candidates:
                if candidate.weight > best.weight:
                    best = candidate

            # links the best one with the particular entity
            if best.weight >= treshold:
                entity.matched = best
                entity.used = True
                best.used = True # mark as used (can be used only once)

        # set the score to zero
        for candidate in candidates:
            candidate.weight = 0

def match_by_unique(entity, index, unique_relations):
    '''
    Searches over the index for the corresponding entities based on the unique id.
    '''

    for relation in unique_relations:
        first = entity.get_field(relation.kb1_field)
        if first: # the value in the 1st KB contains an unique id
            first_value = first[0]
            match = index[relation.kb2_field].get(first_value) 
            if match and not match[0].used:
                return match[0]
    return None               

def match_by_name(entity, index, name_relations):
    '''
    Searches over the index for the corresponding entities based on the name comparison.
    '''

    candidates = list()
    for relation in name_relations:
        first = entity.get_field(relation.kb1_field)
        if not first: # if empty, we have to take another relation
            continue
        for value in first:
            match = index[relation.kb2_field].get(value)
            if value and match:
                for x in match:
                    if not x.used:
                       x.weight += 1
                       candidates.append(x)
    return list(set(candidates)) # removes duplicates
 
class Output(object):
    '''
    Class for creating the output.
    '''

    def __init__(self, output_conf_file_name, other_output_conf_file_name, output_file_name, second_output_file_name):
        try:
            output_conf_fd = open(output_conf_file_name, 'r')
        except IOError:
            sys.stderr.write("Cannot open file " + output_conf_file_name + ".\n")
            sys.exit(1)
        output_fields = list()
        for line in output_conf_fd:
            line = line.strip() # trim whitespaces
            if (not line): # skip empty lines
                continue
            if (line == "None"):
                output_fields += [None]
            else:
                output_fields += [line]
        output_conf_fd.close()

        try:
            other_output_conf_fd = open(other_output_conf_file_name, 'r')
        except IOError:
            sys.stderr.write("Cannot open file " + other_output_conf_file_name + ".\n")
            sys.exit(1)
        other_output_fields = list()
        for line in other_output_conf_fd:
            line = line.strip() # trim whitespaces
            if (not line): # skip empty lines
                continue
            if (line == "None"):
                other_output_fields += [None]
            else:
                other_output_fields += [line]
        other_output_conf_fd.close()

        try:
            self.output_fd = open(output_file_name, 'w')
        except IOError:
            sys.stderr.write("Cannot open file " + output_file_name + ".\n")
            sys.exit(1)

        if second_output_file_name is not None :
            try:
                self.second_output_fd = open(second_output_file_name, 'w')
            except IOError:
                sys.stderr.write("Cannot open file " + second_output_file_name + ".\n")
                sys.exit(1)
            self.second_output = True
        else:
            self.second_output = False

        self.output_fields = output_fields
        self.other_output_fields = other_output_fields

    def make_output(self, kb1, kb2, relations, prefix):
        '''
        Creates the output.
        '''

        self.counter = 1 # global ID counter
        self.prefix = prefix  
        kb1_matched = 0
        kb1_not_matched = 0
        for line in kb1.entities:
            generated_line = list()
            if line.used:
                kb1_matched += 1
                for fieldname in self.output_fields:
                    if (fieldname == "ID"):
                        generated_line.append( [self.prefix + ":" + (hashlib.sha224((str(self.counter).encode('utf-8'))).hexdigest())[:10]])
                        self.counter += 1
                    elif (fieldname == None):
                        generated_line.append([""])
                    elif (fieldname.startswith('"')):
                        generated_line.append([fieldname.strip('"')])
                    else:
                        possible = list()
                        if fieldname.startswith(kb1.name):
                            ff = kb1.fields[fieldname]
                            possible.extend(line.get_field(ff.order_num))
                            if ff.multiple or len(possible) == 0 : # using values from the 2nd KB
                                for relation in relations:
                                    if relation.kb1_field == ff.order_num:
                                        possible.extend(line.matched.get_field(relation.kb2_field)) 
                        else:
                            ff = kb2.fields[fieldname]
                            possible.extend(line.matched.get_field(ff.order_num))
                            if ff.multiple or len(possible) == 0 : # using values from the 1st KB
                                for relation in relations:
                                    if relation.kb2_field == ff.order_num:
                                        possible.extend(line.get_field(relation.kb1_field)) 
                        possible = list(set(possible))
                        if not ff.multiple and len(possible) > 1:
                            possible = possible[0:1]
                        generated_line.append(possible)
            else:
                kb1_not_matched += 1
                for fieldname in self.other_output_fields:
                    if (fieldname == "ID"):
                        generated_line.append( [self.prefix + ":" + (hashlib.sha224((str(self.counter).encode('utf-8'))).hexdigest())[:10]])
                        self.counter += 1
                    elif (fieldname == None):
                        generated_line.append([""])
                    elif (fieldname.startswith('"')):
                        generated_line.append([fieldname.strip('"')])
                    else:
                        possible = list()
                        for fn in fieldname.split("|"):
                            field = kb1.get_field_order_num(fn)
                            possible.extend(line.get_field(field))
                        possible = list(set(possible))
                        generated_line.append(possible)
            self.write_line_to_output(generated_line)
        sys.stdout.write("Matched entities : " + str(kb1_matched) + ".\n")
        sys.stdout.write("Unmatched entities from the 1st KB : " + str(kb1_not_matched) + ".\n")
        if self.second_output:
            self.generate_rest(kb2.entities)
        else:
            self.generate_second(kb2.entities, self.output_fields, kb2.name, kb2.fields)
        self.output_fd.close()

    def write_line_to_output(self,line):
        for field in line:
            line[line.index(field)] = "|".join(field)
        result = ("\t".join(line)).replace("\n", "") + "\n"
        self.output_fd.write(result)

    def generate_second(self, data, output, kb, fields_in_kb2):
        kb2_not_matched = 0
        for line in data:
            if line.used:
                continue
            kb2_not_matched += 1
            result = ""
            for fieldname in output:
                if (fieldname == "ID"):
                    result += self.prefix + ":" + (hashlib.sha224((str(self.counter).encode('utf-8'))).hexdigest())[:10] + "\t"
                    self.counter += 1
                elif (fieldname == None):
                    result += "\t"
                elif (fieldname.startswith('"')):
                    result += fieldname.strip('"') + "\t"
                elif (not fieldname.startswith(kb)):
                    result += "\t"
                else:
                    result += ("|".join(line.get_field(fields_in_kb2[fieldname].order_num))).replace("\n", "") + "\t"
         
            result = result[:-1] + "\n"
            self.output_fd.write(result)
        sys.stdout.write("Unmatched entities from the 2nd KB : " + str(kb2_not_matched) + ".\n")

    def generate_rest(self, entities):
        sys.stdout.write("Unmatched entities from the 2nd KB were written into the separate file.\n")
        kb2_not_matched = 0
        for e in entities:
            if e.used:
                continue
            kb2_not_matched += 1
            result = ""
            for f in e.data:
                result += "|".join(f) + "\t"
            result = result[:-1] + "\n"
            self.second_output_fd.write(result)
        sys.stdout.write("Unmatched from the 2nd KB " + str(kb2_not_matched) + ".\n")

def main():
    args = get_args()
    output_maker = Output(args.output_conf, args.other_output_conf, args.output, args.second_output)

    begin = time.time()
    kb1 = KB(args.first, args.first_fields, args.first_sep)
    kb1.load_config()
    kb1.load_to_memory()
    sys.stdout.write("KB " + kb1.name + " was loaded into memory (" + str(round(time.time() - begin, 2)) + " s).\n")

    begin = time.time()
    kb2 = KB(args.second, args.second_fields, args.second_sep)
    kb2.load_config()
    kb2.load_to_memory()
    sys.stdout.write("KB " + kb2.name + " was loaded into memory (" + str(round(time.time() - begin, 2)) + " s).\n")
    relations = parse_relations(args.rel_conf, kb1, kb2)

    begin = time.time()
    index = make_index(kb2.entities, kb2.field_count, relations)
    sys.stdout.write("The index for the 2nd KB was created (" + str(round(time.time() - begin, 2)) + " s).\n")

    begin = time.time()
    match(kb1, index, relations, int(args.treshold))
    sys.stdout.write("KBs " + kb1.name + " and " + kb2.name + " were successfully compared (" + str(round(time.time() - begin, 2)) + " s).\n")

    begin = time.time()
    output_maker.make_output(kb1, kb2, relations, args.id_prefix)
    sys.stdout.write("A new KB " + args.output + " was created (" + str(round(time.time() - begin, 2)) + " s).\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
