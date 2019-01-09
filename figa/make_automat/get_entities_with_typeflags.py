#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Typeflags format for person entities => <Type: P=Person>:<Subtype: F/G=Fictional/Group>:<Future purposes: determine regular name and alias>:<Gender: F/M=Female/Male>

import argparse
import sys
import os
import re
from importlib import reload
from natToKB import NatToKB
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
reload(sys)

import metrics_knowledge_base


# loading KB struct
kb_struct = metrics_knowledge_base.KnowledgeBase()

# multiple values delimiter
KB_MULTIVALUE_DELIM = metrics_knowledge_base.KB_MULTIVALUE_DELIM

name_typeflag = []

ntokb = NatToKB()
nationalities = ntokb.get_nationalities()

def extract_names_from_line(line):
    names = kb_struct.get_data_for(line, 'ALIASES').split(KB_MULTIVALUE_DELIM)
    names.append(kb_struct.get_data_for(line, 'NAME'))
    names = (a for a in names if a.strip() != "")

    return names


def append_names_to_list(names, type_flags, url_origin):
    for n in names:
        n = re.sub('\s+', ' ', n).strip()
        if re.search(r"#lang=(?!cs).*$", n):
            continue
        else:
            n = re.sub(r"#lang=cs$", "", n)
        unsuitable = ";?!()[]{}<>/~@#$%^&*_=+|\"\\"
        for x in unsuitable:
            if x in n:
                break
        else:
            #if type_flags[0] == 'P':
                #name_without_location = re.sub(r"\s+(?:ze?|of|von)\s+.*", "", n, flags=re.I)
                #a_and_neighbours = re.search(r"((?:[^ ])+)\s+a(?:nd)?\s+((?:[^ ])+)", name_without_location)
                #if a_and_neighbours:
                    #if a_and_neighbours.group(1) not in nationalities or a_and_neighbours.group(2) not in nationalities:
                        #type_flags = re.sub(r"(?<=P:)[^:]*(?=:)", 'G', type_flags)
                    ## else Kateřina Řecká a Dánská" is regular person
            name_typeflag.append(n + '\t' + type_flags + '\t' + url_origin)



def generate_name_alternatives(kb_path):
    if kb_path:
        with open(kb_path) as kb:
            for line in kb:
                if line:
                    line = line.strip('\n').split('\t')

                    ent_type = kb_struct.get_ent_type(line)
                    names = extract_names_from_line(line)
                    url_origin = kb_struct.get_data_for(line, 'WIKIPEDIA LINK')

                    if ent_type in ['person', 'person:artist', 'person:fictional', 'person:group']:
                        gender = kb_struct.get_data_for(line, 'GENDER')
                        subtype = ''

                        if ent_type == 'person:fictional':
                            subtype = 'F'
                        elif ent_type == 'person:group':
                            subtype = 'G'
                        append_names_to_list(names, "P:" + subtype + "::" + gender, url_origin)
                    elif ent_type in ['country', 'country:former', 'settlement', 'watercourse', 'waterarea', 'geo:relief', 'geo:waterfall', 'geo:island', 'geo:peninsula', 'geo:continent']:
                        append_names_to_list(names, 'L', url_origin)
                    else:
                        continue;

        for n in name_typeflag:
            print(n)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--kb_path')
    args = parser.parse_args()

    generate_name_alternatives(args.kb_path)
