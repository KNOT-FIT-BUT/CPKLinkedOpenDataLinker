#!/usr/bin/env python3
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

# Author: Lubomir Otrusina, iotrusina@fit.vutbr.cz
# Author: Tomáš Volf, ivolf@fit.vutbr.cz
#
# Description: Creates namelist from KB.

import itertools
import argparse
import os
import regex
import sys
from importlib import reload
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
reload(sys)

from library.config import AutomataVariants
from library.utils import remove_accent
from library.entities.Persons import Persons
from natToKB import NatToKB
import metrics_knowledge_base


# defining commandline arguments
parser = argparse.ArgumentParser()
parser.add_argument("-l", "--lowercase", action="store_true", help="creates a lowercase list")
parser.add_argument("-a", "--autocomplete", action="store_true", help="creates a list for autocomplete")
parser.add_argument("-u", "--uri", action="store_true", help="creates an uri list")
parser.add_argument("--czechnames", help="czechnames file path (suitable for debug)")
args = parser.parse_args()


# a dictionary for storing results
dictionary = {}
# a set for storing subnames results
g_subnames = set()

# automata variants config
atm_config = AutomataVariants.DEFAULT
if args.lowercase:
	atm_config |= AutomataVariants.LOWERCASE
if args.autocomplete:
	atm_config |= AutomataVariants.NONACCENT

# loading KB struct
kb_struct = metrics_knowledge_base.KnowledgeBase()

# multiple values delimiter
KB_MULTIVALUE_DELIM = metrics_knowledge_base.KB_MULTIVALUE_DELIM

SURNAME_MATCH = regex.compile(r"(((?<=^)|(?<=[ ]))(?:(?:da|von)(?:#[^ ]+)? )?((?:\p{Lu}\p{Ll}*(?:#[^- ]+)?-)?(?:\p{Lu}\p{Ll}+(?:#[^- ]+)?))$)")
UNWANTED_MATCH = regex.compile(r"(Princ|Svatý|,|z|[0-9])")

re_flag_names = r"(?:#[A-Z0-9]E?)"
re_flag_only1st_firstname = r"(?:#[GI]E?)"
re_flag_firstname = r"(?:#[G]E?)"
re_flag_sure_surname = r"(?:#[^GI]E?)"

word_freq = dict()


''' For firstnames or surnames it creates subnames of each separate name and also all names together '''
def get_subnames_from_parts(subname_parts):
	subnames = set()
	subname_all = ''
	for subname_part in subname_parts:
		subname_part = regex.sub(r'#[A-Za-z0-9]E?( |$)', '\g<1>', subname_part)
		subnames.add(subname_part)
		if subname_all:
			subname_part = ' ' + subname_part
		subname_all += subname_part

	if (subname_all):
		subnames.add(subname_all)
	return subnames


def build_name_variant(ent_flag, strip_nameflags, inflection_parts, is_basic_form, i_inflection_part, stacked_name, name_inflections):
	subnames = set()
	separator = ''
	if i_inflection_part < len(inflection_parts):
		for inflected_part in inflection_parts[i_inflection_part]:
			if stacked_name and inflected_part:
				separator = ' '
			name_inflections, built_subnames = build_name_variant(ent_flag, strip_nameflags, inflection_parts, is_basic_form, i_inflection_part + 1, stacked_name + separator + inflected_part, name_inflections)
			subnames |= built_subnames
	else:
		new_name_inflections = set()
		new_name_inflections.add(stacked_name)

		if ent_flag in ['F', 'M']:
			match_one_firstname_surnames = regex.match("^([^#]+#[G]E? )(?:[^#]+#[G]E? )+((?:[^# ]+#SE?(?: \p{L}+#[L78]E?)*(?: |$))+)", stacked_name)
			if match_one_firstname_surnames:
				firstname_surnames = match_one_firstname_surnames.group(1) + match_one_firstname_surnames.group(2)
				if firstname_surnames not in name_inflections:
					new_name_inflections.add(firstname_surnames)

			if is_basic_form:
				firstnames_surnames = regex.match("^((?:[^#]+#[G]E? )+)((?:[^# ]+#SE?(?: |$))+)", stacked_name)
				if firstnames_surnames:
					firstnames_surnames = firstnames_surnames.group(1) + firstnames_surnames.group(2).upper()
					if firstnames_surnames != stacked_name:
						new_name_inflections.add(firstnames_surnames)

			for n in new_name_inflections:
				subnames |= get_subnames_from_parts(regex.findall(r'(\p{L}+#GE?)', n))
				subnames |= get_subnames_from_parts(regex.findall(r'(\p{L}+#SE?(?: \p{L}+#[L78])*)', n))
			subnames = Persons.get_normalized_subnames(subnames)
		for n in new_name_inflections:
			name_inflections.add(regex.sub(r'#[A-Za-z0-9]E?(?=-| |$)', '', n) if strip_nameflags else n)
	return [name_inflections, subnames]

# not used
def get_KB_names_for(_fields, preserve_flag = False):
	names = dict()
	str_name = kb_struct.get_data_for(_fields, 'NAME')
	str_aliases = kb_struct.get_data_for(_fields, 'ALIASES')
	if not preserve_flag:
		str_aliases = regex.sub(r"#(?:lang|ntype)=[^#|]*", "", str_aliases)

	names = [str_name]
	for alias in str_aliases.split(KB_MULTIVALUE_DELIM):
		alias = alias.strip()
		if alias and alias not in names:
			names.append(alias)
	return names

def get_KB_names_ntypes_for(_fields):
	names = dict()
	str_name = kb_struct.get_data_for(_fields, 'NAME')
	str_aliases = kb_struct.get_data_for(_fields, 'ALIASES')
	str_aliases = regex.sub(r"#lang=[^#|]*", "", str_aliases)

	names[str_name] = None
	for alias in str_aliases.split(KB_MULTIVALUE_DELIM):
		ntype = regex.search(r"#ntype=([^#|]*)", alias)
		if ntype:
			ntype = ntype.group(1)
		if not ntype: # unify also for previous
			ntype = None
		k_alias = regex.sub(r"#ntype=[^#|]*", "", alias).strip()
		if k_alias and k_alias not in names:
			names[k_alias] = ntype
	return names


def process_czechnames(cznames_file, strip_nameflags = True):
	global g_subnames
	name_inflections = {}

	with open(cznames_file) as f:
		for line in f:
			if line:
				line = line.strip('\n').split('\t')
				name = line[0]
				inflections = line[2].split('|') if line[2] != '' else []
				for idx, infl in enumerate(inflections):
					inflection_parts = {}
					for i_infl_part, infl_part in enumerate(infl.split(' ')):
						inflection_parts[i_infl_part] = set()
						for infl_part_variant in infl_part.split('/'):
							inflection_parts[i_infl_part].add(regex.sub(r'(\p{L}*)(\[[^\]]+\])?', '\g<1>', infl_part_variant))
					if name not in name_inflections:
						name_inflections[name] = set()
					built_name_inflections, built_subnames = build_name_variant(line[1], strip_nameflags, inflection_parts, idx == 0, 0, "", set())
					name_inflections[name] |= built_name_inflections
					g_subnames |= built_subnames
				if len(inflections) == 0 and line[1] in ['F', 'M']:
					g_subnames |= Persons.get_normalized_subnames([name], True)

	return name_inflections

def add_to_dictionary(_key, _nametype, _value, _type, _fields, alt_names):
	"""
	 Adds the name into the dictionary. For each name it adds also an alternative without accent.

	 _key : the name of a given entity
	 _value : the line number (from the KB) corresponding to a given entity
	 _type : the type of a given entity
	"""
	global g_subnames

	# removing white spaces
	_key = regex.sub('\s+', ' ', _key).strip()

	# there are no changes for the name from the allow list
	if _key not in allow_list:

		# we don't want names with any of these characters
		unsuitable = ";?!()[]{}<>/~@#$%^&*_=+|\"\\"
		_key = _key.strip()
		for x in unsuitable:
			if x in _key:
				return

		# inspecting names with numbers
		if len(regex.findall(r"[0-9]+", _key)) != 0:
			# we don't want entities containing only numbers
			if len(regex.findall(r"^[0-9 ]+$", _key)) != 0:
				return
			# exception for people or artist name (e.g. John Spencer, 1st Earl Spencer)
			if _type in ["person", "person:artist", "person:fictional"]:
				if len(regex.findall(r"[0-9]+(st|nd|rd|th)", _key)) == 0:
					return
			# we don't want locations with numbers at all
			if _type.startswith("geoplace:"):
				return

		# special filtering for people and artists
		if _type in ["person", "person:artist", "person:fictional"]:
			# we don't want names starting with "List of"
			if _key.startswith("Seznam "):
				return

		# generally, we don't want names starting with low characters (event is needed with low character, ie. "bitva u Waterloo")
		if _type in ["person", "person:artist", "person:fictional", "organisation"] or _type.startswith('geo'):
			if len(regex.findall(r"^\p{Ll}+", _key)) != 0:
				return

		# filtering out all names with length smaller than 2 and greater than 80 characters
		if len(_key) < 2 or len(_key) > 80:
			return

		# filtering out names ending by ., characters
		if _type not in ["person", "person:artist", "person:fictional"]:
			if len(regex.findall(r"[.,]$", _key)) != 0:
				return

	# Get all inflection variants of key
	key_inflections = None
#	if _type in ["person", "person:artist", "person:fictional"]:
	if _key in alt_names:
		key_inflections = alt_names[_key]
	if not key_inflections:
		key_inflections = set([_key]) # TODO alternative names are not in subnames
		if _type in ["person", "person:artist", "person:fictional"] and _nametype != "nick":
			g_subnames |= Persons.get_normalized_subnames(set([_key]), True)
	for tmp in key_inflections.copy():
		if regex.search(r"\-\p{Lu}", tmp):
			key_inflections.add(regex.sub(r"\-(\p{Lu})", " \g<1>", tmp)) # Payne-John Christo -> Payne John Christo

	# All following transformatios will be performed for each of inflection variant of key_inflection
	for key_inflection in key_inflections:
		# adding name into the dictionary
		add(key_inflection, _value, _type)

		# generating permutations for person and artist names
		if _type in ["person", "person:artist", "person:fictional"]:
			length = key_inflection.count(" ") + 1
			if length <= 4 and length > 1:
				parts = key_inflection.split(" ")
				# if a name contains any of these words, we will not create permutations
				if not (set(parts) & set(["van", "von"])):
					names = list(itertools.permutations(parts))
					for x in names:
						r = " ".join(x)
						add(key_inflection, _value, _type)

		# adding various alternatives for given types
		if _type in ["person", "person:artist", "person:fictional", 'organisation'] or _type.startswith('geo'):
			re_saint = r'Svat(á|é|ého|ém|ému|í|ou|ý|ých|ým|ými) '
			if regex.search(r'(' + re_saint + r'|Sv |Sv\. ?)', key_inflection) is not None:
				add(regex.sub(r'(' + re_saint + r'|Sv |Sv\.)', 'Sv. ', key_inflection), _value, _type) # Svatý Jan / Sv.Jan / Sv Jan -> Sv. Jan
				add(regex.sub(r'(' + re_saint + r'|Sv |Sv\. )', 'Sv.', key_inflection), _value, _type) # Svatý Jan / Sv. Jan / Sv Jan -> Sv.Jan
				add(regex.sub(r'(' + re_saint + r'|Sv\. ?)', 'Sv ', key_inflection), _value, _type) # Svatý Jan / Sv. Jan / Sv.Jan -> Sv Jan
				# TODO: base form for female and middle-class
				add(regex.sub(r'(Sv\. ?|Sv )', 'Svatý ', key_inflection), _value, _type) # Sv. Jan / Sv.Jan / Sv Jan -> Svatý Jan

		if _type in ["person", "person:artist", "person:fictional"]:
			if _nametype != "nick":
				if regex.search(r"#", key_inflection):
					# TODO: what about abbreviation of Mao ce-Tung?
					#                             ( <firstname>             ) ( <other firstnames>                                 )( <unknowns>               )( <surnames>                   )
					name_parts = regex.search(r"^((?:\p{Lu}')?\p{Lu}\p{L}+%s) ((?:(?:(?:\p{Lu}')?\p{L}+#I )*(?:\p{Lu}')?\p{L}+%s )*)((?:(?:\p{Lu}')?\p{L}+#I )*)((?:\p{Lu}')?\p{Lu}\p{L}+(%s).*)$" % (re_flag_only1st_firstname, re_flag_firstname, re_flag_sure_surname), key_inflection)
					if name_parts:
						fn_1st = name_parts.group(1)
						tmp_fn_others = name_parts.group(2).strip().split()
						n_unknowns = name_parts.group(3).strip().split()
						tmp_sn_all = name_parts.group(4)
						if name_parts.group(5) not in ['#S', '#SE', '#R'] and len(n_unknowns):
							tmp_sn = n_unknowns.pop()
							if tmp_sn:
								tmp_sn_all = tmp_sn + ' ' + tmp_sn_all

						for i in range(len(n_unknowns) + 1):
							sep_special = ""
							fn_others_full = ""
							fn_others_abbr = ""

							fn_others = tmp_fn_others + n_unknowns[:i]
							if len(fn_others):
								sep_special = " "
								fn_others_full += " ".join(fn_others)
								for fn_other in fn_others:
									fn_others_abbr += fn_other[:1] + ". "
								fn_others_abbr = fn_others_abbr.strip()

							sn_all = ' '.join(n_unknowns[i:])
							if sn_all:
								sn_all += ' ' + tmp_sn_all
							else:
								sn_all = tmp_sn_all

							# For all of following format exaplaining comments of additions let us assume, that Johann Gottfried Bernhard is firstnames and a surname is Bach only.
							add("{} {}{}{}".format(fn_1st, fn_others_abbr, sep_special, sn_all), _value, _type)       # Johann G. B. Bach
							add("{}. {}{}{}".format(fn_1st[:1], fn_others_abbr, sep_special, sn_all), _value, _type)  # J. G. B. Bach
							add("{} {}".format(fn_1st, sn_all), _value, _type)                                        # Johann Bach
							add("{}. {}".format(fn_1st[:1], sn_all), _value, _type)                                   # J. Bach
							add("{}, {}{}{}".format(sn_all, fn_1st, sep_special, fn_others_full), _value, _type)      # Bach, Johann Gottfried Bernhard
							add("{}, {}{}{}".format(sn_all, fn_1st, sep_special, fn_others_abbr), _value, _type) # Bach, Johann G. B.
							add("{}, {}.{}{}".format(sn_all, fn_1st[:1], sep_special, fn_others_abbr), _value, _type) # Bach, J. G. B.
							add("{}, {}".format(sn_all, fn_1st), _value, _type)                                       # Bach, Johann
							add("{}, {}.".format(sn_all, fn_1st[:1]), _value, _type)                                  # Bach, J.

				else:
					add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>", key_inflection), _value, _type) # Adolf Born -> A. Born
					add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3>", key_inflection), _value, _type) # Peter Paul Rubens -> P. P. Rubens
					add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3>", key_inflection), _value, _type) # Peter Paul Rubens -> Peter P. Rubens
					add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3>. \g<4>", key_inflection), _value, _type) # Johann Gottfried Bernhard Bach -> J. G. B. Bach
					add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<1>. \g<2>. \g<3> \g<4>", key_inflection), _value, _type) # Johann Gottfried Bernhard Bach -> J. G. Bernhard Bach
					add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3>. \g<4>", key_inflection), _value, _type) # Johann Gottfried Bernhard Bach -> Johann G. B. Bach
					add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<1> \g<2>. \g<3> \g<4>", key_inflection), _value, _type) # Johann Gottfried Bernhard Bach -> Johann G. Bernhard Bach
					add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<1> \g<2> \g<3>. \g<4>", key_inflection), _value, _type) # Johann Gottfried Bernhard Bach -> Johann Gottfried B. Bach
					if not regex.search("[IVX]\.", key_inflection): # do not consider "Karel IV." or "Albert II. Monacký", ...
						add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2>, \g<1>", key_inflection), _value, _type) # Adolf Born -> Born, Adolf
						add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<2>, \g<1>.", key_inflection), _value, _type) # Adolf Born -> Born, A.
						add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<3>, \g<1> \g<2>", key_inflection), _value, _type) # Johann Joachim Quantz -> Quantz, Johann Joachim
						add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu})\p{L}+ (\p{Lu}\p{L}+)$", "\g<3>, \g<1>. \g<2>.", key_inflection), _value, _type) # Johann Joachim Quantz -> Quantz, J. J.
						add(regex.sub(r"^(\p{Lu}\p{L}+) (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2> \g<3>, \g<1>", key_inflection), _value, _type) # Tomáš Garrigue Masaryk -> Garrigue Masaryk, Tomáš
						add(regex.sub(r"^(\p{Lu})\p{L}+ (\p{Lu}\p{L}+) (\p{Lu}\p{L}+)$", "\g<2> \g<3>, \g<1>.", key_inflection), _value, _type) # Tomáš Garrigue Masaryk -> Garrigue Masaryk, T.
			if "Mc" in key_inflection:
				add(regex.sub(r"Mc(\p{Lu})", "Mc \g<1>", key_inflection), _value, _type) # McCollum -> Mc Collum
				add(regex.sub(r"Mc (\p{Lu})", "Mc\g<1>", key_inflection), _value, _type) # Mc Collum -> McCollum
			if "." in key_inflection:
				new_key_inflection = regex.sub(r"(\p{Lu}\.%s?) (?=\p{Lu})" %re_flag_names, "\g<1>", key_inflection) # J. M. W. Turner -> J.M.W.Turner
				add(new_key_inflection, _value, _type)
				new_key_inflection = regex.sub(r"(\p{Lu}\.%s?)(?=\p{Lu}\p{L}+)" %re_flag_names, "\g<1> ", new_key_inflection) # J.M.W.Turner -> J.M.W. Turner
				add(new_key_inflection, _value, _type)
				add(regex.sub(r"\.", "", new_key_inflection), _value, _type) # J.M.W. Turner -> JMW Turner
			if "-" in key_inflection:
				add('-'.join(word[0].upper() + word[1:] if len(word) > 1 else word for word in key_inflection.split("-")), _value, _type) # Mao Ce-tung -> Mao Ce-Tung
			if "ì" in key_inflection:
				add(regex.sub("ì", "í", key_inflection), _value, _type) # Melozzo da Forlì -> Melozzo da Forlí

			parts = key_inflection.split(" ")
			# if a name contains any of these words, we will not create permutations
			if not (set(parts) & set(["von", "van"])):
				for x in f_name:
					if x in key_inflection:
						new_key_inflection = regex.sub(' ?,? ' + x + '$', '', key_inflection) # John Brown, Jr. -> John Brown
						new_key_inflection = regex.sub('^' + x + ' ', '', new_key_inflection) # Sir Patrick Stewart -> Patrick Stewart
						if new_key_inflection.count(' ') >= 1:
							add(new_key_inflection, _value, _type)

		if _type in ["settlement", "watercourse"]:
			description = kb_struct.get_data_for(_fields, 'DESCRIPTION')
			if key_inflection in description:
				if _type == 'settlement':
					country = kb_struct.get_data_for(_fields, 'COUNTRY')
				elif _type == 'watercourse':
					country = kb_struct.get_data_for(_fields, 'SOURCE_LOC')
				if country and country not in key_inflection:
					add(key_inflection + ", " + country, _value, _type) # Peking -> Peking, China
					add(regex.sub("United States", "US", key_inflection + ", " + country), _value, _type)

		#if _type in ["event"]:
		#	if len(regex.findall(r"^[0-9]{4} (Summer|Winter) Olympics$", key_inflection)) != 0:
		#		location = kb_struct.get_data_for(_fields, 'LOCATION')
		#		year = kb_struct.get_data_for(_fields, 'START DATE')[:4]
		#		if year and location and "|" not in location:
		#			add("Olympics in " + location + " in " + year, _value, _type) # 1928 Summer Olympics -> Olympics in Amsterdam in 1928
		#			add("Olympics in " + year + " in " + location, _value, _type) # 1928 Summer Olympics -> Olympics in 1928 in Amsterdam
		#			add("Olympic Games in " + location + " in " + year, _value, _type) # 1928 Summer Olympics -> Olympic Games in Amsterdam in 1928
		#			add("Olympic Games in " + year + " in " + location, _value, _type) # 1928 Summer Olympics -> Olympic Games in 1928 in Amsterdam


def add(_key, _value, _type):
	"""
	 Adds the name into the dictionary. For each name it adds also an alternative without accent.

	 _key : the name
	 _value : the line number (from the KB) corresponding to a given entity
	 _type : the type prefix for a given entity
	"""

	_key = regex.sub(r"#[A-Za-z0-9]E?(?= |,|\.|-|$)", "", _key)

	_key = _key.strip()

	if args.autocomplete:
		_key = remove_accent(_key.lower())

	if args.lowercase:
		_key = _key.lower()

	# removing entities that begin with '-. or space
	if len(regex.findall(r"^[ '-\.]", _key)) != 0:
		return

	# adding the type-specific prefix to begining of the name
	if args.autocomplete:
		_key = _type+":\t"+_key

	# adding the name into the dictionary
	if _key not in dictionary:
		dictionary[_key] = set()
	dictionary[_key].add(_value)


""" Processes a line with entity of argument determined type. """
def add_line_of_type_to_dictionary(_fields, _line_num, alt_names, _type):
	aliases = get_KB_names_ntypes_for(_fields)
	for alias, ntype in aliases.items():
		transformed_alias = [alias]
		if _type == "event":
			if len(alias) > 1:
				transformed_alias = [alias[0].upper() + alias[1:], alias[0].lower() + alias[1:]] # capitalize destroys other uppercase letters to lowercase
		elif _type == "organisation":
			transformed_alias = [alias, ' '.join(word[0].upper() + word[1:] if len(word) > 1 else word for word in alias.split())] # title also destroys other uppercase letters in word to lowercase

		for ta in transformed_alias:
			add_to_dictionary(ta, ntype, _line_num, _type, _fields, alt_names)


def process_person_common(person_type, _fields, _line_num, alt_names, confidence_threshold):
	""" Processes a line with entity of any subtype of person type. """

	aliases = get_KB_names_ntypes_for(_fields)
	name = kb_struct.get_data_for(_fields, 'NAME')
	confidence = float(kb_struct.get_data_for(_fields, 'CONFIDENCE'))

	for n, t in aliases.items():
		length = n.count(" ") + 1
		if length >= 2 or (n in word_freq and word_freq[n] > 0.5) or ((n[:1].lower() + n[1:]) not in word_freq):
			add_to_dictionary(n, t, _line_num, person_type, _fields, alt_names)

		if confidence >= confidence_threshold:
			surname_match = SURNAME_MATCH.search(name)
			unwanted_match = UNWANTED_MATCH.search(name)
			if surname_match and not unwanted_match:
				surname = surname_match.group(0)
				add_to_dictionary(surname, t, _line_num, person_type, _fields, alt_names)


def process_other(_fields, _line_num, alt_names):
	""" Processes a line with entity of other type. """

	add_line_of_type_to_dictionary(_fields, _line_num, alt_names, _fields[1])


def process_uri(_fields, _line_num):
	""" Processes all URIs for a given entry. """

	entity_head = kb_struct.get_ent_head(_fields)

	uris = []
	for uri_column_name in ['WIKIPEDIA LINK', 'WIKIPEDIA URL', 'DBPEDIA URL', 'FREEBASE URL']:
		if uri_column_name in entity_head:
			uris.append(kb_struct.get_data_for(_fields, uri_column_name))
	if 'OTHER URL' in entity_head:
		uris.extend(kb_struct.get_data_for(_fields, 'OTHER URL').split(KB_MULTIVALUE_DELIM))
	uris = [u for u in uris if u.strip() != ""]

	for u in uris:
		if u not in dictionary:
			dictionary[u] = set()
		dictionary[u].add(_line_num)


if __name__ == "__main__":

	if args.uri:
		# processing the KB
		line_num = 1
		for l in sys.stdin:
			fields = l[:-1].split("\t")
			process_uri(fields, str(line_num))
			line_num += 1

	else:
		# loading the list of titles, degrees etc. (earl, sir, king, baron, ...)
		with open("freq_terms_filtred.all") as f_file:
			f_name = f_file.read().splitlines()

		# loading the allow list (these names will be definitely in the namelist)
		with open("allow_list") as allow_file:
			allow_list = allow_file.read().splitlines()

		# loading the list of first names
		with open("yob2012.txt") as firstname_file:
			firstname_list = firstname_file.read().splitlines()

		# loading the list of all nationalities
		with open("nationalities.txt") as nationality_file:
			nationality_list = nationality_file.read().splitlines()

		# load version number (string) of KB
		with open("../../VERSION") as kb_version_file:
			kb_version = kb_version_file.read().strip()

		# load frequency for words
		with open("../../cs_media.wc") as frequency_file:
			dbg_f = open("freq.log", "w")
			word_freq_total = dict()
			for l in frequency_file:
				word, freq = l.rstrip().split("\t") # must be rstrip() only due to space as a key in input file
				word_freq[word] = int(freq)
				k_freq_total = word.lower()
				if k_freq_total not in word_freq_total:
					word_freq_total[k_freq_total] = 0
				word_freq_total[k_freq_total] += int(freq)
			for k in word_freq:
				word_freq[k] = word_freq[k] / word_freq_total[k.lower()]
				dbg_f.write(k + "\t" + str(word_freq[k]) + "\n")
			dbg_f.close()

		if args.czechnames:
			czechnames_file = args.czechnames
		else:
			czechnames_file = 'czechnames_' + kb_version + '.out'
		alternatives = process_czechnames(czechnames_file, False)

		# processing the KB
		line_num = 1
		for l in sys.stdin:
			fields = l[:-1].split("\t")
			ent_type = kb_struct.get_ent_type(fields)

			if ent_type == "person:fictional":
				process_person_common(ent_type, fields, str(line_num), alternatives, 15)
			elif ent_type == "person:artist":
				process_person_common(ent_type, fields, str(line_num), alternatives, 15)
			elif ent_type == "person":
				process_person_common(ent_type, fields, str(line_num), alternatives, 20)
			else:
				process_other(fields, str(line_num), alternatives)
			line_num += 1

		# Subnames in all inflections with 'N'
		for subname in g_subnames:
			if subname not in dictionary:
				dictionary[subname] = set()
			if 'N' not in dictionary[subname]:
				dictionary[subname].add('N')

		# Pronouns with first lower and first upper with 'N'
		pronouns = ["on", "ho", "mu", "něm", "jím", "ona", "jí", "ní"]
		if (not args.lowercase):
			pronouns += [pronoun.capitalize() for pronoun in pronouns]
		if (args.autocomplete):
			pronouns += [remove_accent(pronoun) for pronoun in pronouns]
		dictionary.update(dict.fromkeys(pronouns, 'N'))

		# geting nationalities
		ntokb = NatToKB()
		nationalities = ntokb.get_nationalities()
		for nat in nationalities:
			if nat not in dictionary:
				dictionary[nat] = set()
			dictionary[nat].add('N')

	# printing the output
	for item in dictionary.items():
		print(item[0] + "\t" + ";".join(item[1]))
