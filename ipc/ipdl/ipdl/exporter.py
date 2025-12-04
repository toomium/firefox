# vim: set ts=4 sw=4 tw=99 et:
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import sys

from ipdl.builtin import PBTypeMappings
from ipdl.ast import ASYNC, SYNC
from ipdl.ast import IN, OUT, INOUT
from ipdl.ast import StringLiteral
from ipdl.type import ImportedCxxType, BuiltinCType, ArrayType, ActorType, StructType, UnionType, MaybeType, FDType

from pprint import pprint

# We export some protocol data to JSON so it can be consumed and processed
# further by external tooling, such as Fuzzing/Security to automatically
# determine security boundaries and generate code coverage filters for
# certain protocols.


class JSONExporter:
    @staticmethod
    def protocolToObject(protocol):
        def implToString(impl):
            if impl is None:
                return None

            if type(impl) is StringLiteral:
                return str(impl.value)

            return str(impl)

        p = {
            "name": protocol.name,
            "namespaces": [x.name for x in protocol.namespaces],
            "managers": [x.name for x in protocol.managers],
            "parent_methods": [],
            "child_methods": [],
            "attributes": {
                x.name: implToString(x.value) for x in protocol.attributes.values()
            },
        }

        for md in protocol.messageDecls:

            def serialize_md(md):
                return {
                    "name": md.decl.progname,
                    "attributes": {x.name: x.value for x in md.attributes.values()},
                    "sync": md.sendSemantics == SYNC,
                    "params": [
                        {"type": x.ipdltype.name(), "name": x.name} for x in md.params
                    ],
                }

            if md.direction == IN or md.direction == INOUT:
                p["parent_methods"].append(serialize_md(md))

            if md.direction == OUT or md.direction == INOUT:
                p["child_methods"].append(serialize_md(md))

        return p

class ProtobufExporter:

    def checkType(ipdltype, counters):
        if isinstance(ipdltype, ImportedCxxType):
            counters['ImportedCxxType'] += 1
        elif isinstance(ipdltype, BuiltinCType):
            counters['BuiltinCType'] += 1
        elif isinstance(ipdltype, ArrayType):
            counters['ArrayType'] += 1
        elif isinstance(ipdltype, ActorType):
            counters['ActorType'] += 1
        elif isinstance(ipdltype, StructType):
            counters['StructType'] += 1
        elif isinstance(ipdltype, UnionType):
            counters['UnionType'] += 1
        elif isinstance(ipdltype, MaybeType):
            counters['MaybeType'] += 1
        elif isinstance(ipdltype, FDType):
            counters['FDType'] += 1
        else:
            counters['other'] += 1
        return counters

    @staticmethod
    def protocolToProtobuf(protocol):
        out = """syntax = "proto2";

option optimize_for = LITE_RUNTIME;\n\n"""
        pprint(vars(protocol))

        # used for stats
        param_count = 0
        scalar_mappings = 0
        counters = {
            'ImportedCxxType': 0,
            'BuiltinCType': 0,
            'ArrayType': 0,
            'ActorType': 0,
            'StructType': 0,
            'UnionType': 0,
            'MaybeType': 0,
            'FDType': 0,
            'other': 0
        }

        for msg in protocol.messageDecls:
            out += f"message {msg.name} " + "{\n"
            for param in msg.params:
                pprint(vars(param))
                counters = ProtobufExporter.checkType(counters, param.ipdltype)
                param_count += 1
                out += "   "
                # Type 1: map directly to corresponding scalar type
                if param.ipdltype.name() in PBTypeMappings.keys():
                    scalar_mappings += 1
                    out += "MAPPED "
                    out += PBTypeMappings[param.ipdltype.name()]
                #elif param.ipdltype.
                    # Type 2:
                else:
                    # Type 3: just pretend it's a byte string
                    out += param.ipdltype.name()
                out += " "
                out += f"{param.ipdltype.isCxx()} {param.name}\n"
            out += "}\n\n"

        # print stats
        out += "\n\n"
        out += "// Parameter mapping stats\n"
        out += f"// Total parameter count: {param_count}\n"
        out += f"// Parameters mapped to scalar type: {scalar_mappings}\n"
        print(counters)
        return (protocol.name, out)
