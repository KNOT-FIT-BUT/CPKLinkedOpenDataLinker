#!/usr/bin/env python
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

import sys
import metrics_knowledge_base
import argparse

parser = argparse.ArgumentParser(
	description = "Add empty columns for stats and matrics to the knowledge base reading from standard input."
)
parser.add_argument(
	'-H', '--head-kb',
	help='Header for the knowledge base, which specify its types and their atributes (default: %(default)s).',
	default=metrics_knowledge_base.PATH_HEAD_KB
)

arguments = parser.parse_args()

kb_struct = metrics_knowledge_base.KnowledgeBase(path_to_headkb=arguments.head_kb)

for line in sys.stdin:
	columns = line.rstrip("\n").split("\t")
	
	ent_head = kb_struct.get_ent_head(columns)
	stats_and_matrics = "\t".join(ent_head).find("WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE") >= 0
	if stats_and_matrics and len(columns)+6 == len(ent_head):
		index = kb_struct.get_col_for(columns, "WIKI BACKLINKS")
		columns.insert(index, "\t"*5)
		sys.stdout.write("\t".join(columns) + '\n')
	else:
		sys.stdout.write(line)

# EOF
