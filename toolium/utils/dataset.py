# -*- coding: utf-8 -*-
u"""
Copyright 2020 Telefónica Investigación y Desarrollo, S.A.U.
This file is part of Toolium.

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

from past.builtins import basestring, unicode, xrange
import json
import uuid
import re
import datetime


def prepare_param(param, language="es"):
    """
    Available replacements:
        [LENGTH] Generate a fixed length data for elements
        [MISSING_PARAM] Remove the param from the Dataset
        [EMPTY] Empty string
        [B] Add Blank space if  in the given param
        [RANDOM] Generate random value
        [DATETIME] Add a timestamp
        [NOW] Similar to DATETIME without milliseconds
        [NOW + 2 DAYS] Similar to NOW but two days later
        [NOW - 1 MINUTES] Similar to NOW but one minute earlier
        [TODAY] Similar to NOW without time
        [TODAY + 2 DAYS] Functionality similar to NOW, but only with date offsets (days, weeks)
    :param param: Test parameter
    :return data with the correct replacements
    """

    if not isinstance(param, basestring):
        return param

    date_format = '%d/%m/%Y %H:%M:%S' if language == 'es' else '%Y/%m/%d %H:%M:%S'
    date_day_format = '%d/%m/%Y' if language == 'es' else '%Y/%m/%d'
    date_matcher = re.match('\[(NOW|TODAY)\s*([\+|-]\s*\d+)\s*(\w+)\s*\]', param)

    type_mapping_regex = '\[(DICT|LIST|INT|FLOAT|STR|UNICODE):(.*)\]'
    type_mapping_match_group = re.match(type_mapping_regex, param)

    if "[MISSING_PARAM]" in param:
        new_param = None
    elif "[EMPTY]" in param:
        new_param = param.replace("[EMPTY]", "")
    elif "[B]" in param:
        new_param = param.replace("[B]", " ")
    elif "[RANDOM]" in param:
        return param.replace("[RANDOM]", uuid.uuid4().hex[0:8])
    elif "[DATETIME]" in param:
        return param.replace("[DATETIME]", str(datetime.datetime.utcnow()))
    elif "[NOW]" in param:
        return param.replace("[NOW]", str(datetime.datetime.utcnow().strftime(date_format)))
    elif "[TODAY]" in param:
        return param.replace("[TODAY]", str(datetime.datetime.utcnow().strftime(date_day_format)))
    elif "[TRUE]" in param:
        return True
    elif "[FALSE]" in param:
        return False
    elif "[NULL]" in param:
        return None
    elif type_mapping_match_group and type_mapping_match_group.group(1) \
            in ["LIST", "DICT", "INT", "FLOAT", "STR", "UNICODE"]:
        if type_mapping_match_group.group(1) == "STR":
            return type_mapping_match_group.group(2)
        elif type_mapping_match_group.group(1) == "UNICODE":
            return unicode(type_mapping_match_group.group(2))
        else:
            exec(u"exec_param = {type}({value})".format(type=type_mapping_match_group.group(1).lower(),
                                                        value=type_mapping_match_group.group(2)))
            return locals()['exec_param']
    elif date_matcher and len(date_matcher.groups()) == 3:
        configuration = dict([(date_matcher.group(3).lower(), int(date_matcher.group(2).replace(" ", "")))])
        now = (date_matcher.group(1) == 'NOW')
        reference_date = datetime.datetime.utcnow() if now else datetime.datetime.utcnow().date()
        replace_value = reference_date + datetime.timedelta(**configuration)
        return replace_value.strftime(date_format) if now else replace_value.strftime(date_day_format)
    else:
        new_param = generate_fixed_length_param(param)

    return new_param


def generate_fixed_length_param(param):
    """
    Generate a fixed length param if the elements matches the expression
    [<type>_WITH_LENGTH_<length>]. E.g.: [STRING_WITH_LENGTH_15]
    :param param: Lettuce param
    :return param with the desired length
    """
    try:
        if "_WITH_LENGTH_" in param:
            if "_ARRAY_WITH_LENGTH_" in param:
                seeds = {'STRING': 'a', 'INTEGER': 1}
                seed, length = param[1:-1].split("_ARRAY_WITH_LENGTH_")
                param = list(seeds[seed] for x in xrange(int(length)))
            elif "JSON_WITH_LENGTH_" in param:
                length = int(param[1:-1].split("JSON_WITH_LENGTH_")[1])
                param = dict((str(x), str(x)) for x in xrange(length))
            else:
                seeds = {'STRING': 'a', 'INTEGER': "1"}
                # The chain to be generated can be just a part of param
                start = param.find("[")
                end = param.find("]")
                seed, length = param[start + 1:end].split("_WITH_LENGTH_")
                generated_part = seeds[seed] * int(length)
                placeholder = "[" + seed + "_WITH_LENGTH_" + length + "]"
                param = param.replace(placeholder, generated_part)
                if seed == "INTEGER":
                    param = int(param)
    finally:
        return param