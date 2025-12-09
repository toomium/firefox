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
from ipdl.lower import TranslationUnit, _DISCLAIMER
from ipdl.type import ImportedCxxType, BuiltinCType, ArrayType, ActorType, StructType, UnionType, MaybeType, FDType, IPDLType
from ipdl import writeifmodified

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

_PROTO_HEAD = """syntax = "proto2";

option optimize_for = LITE_RUNTIME;\n\n"""

class ProtobufExporter:

    def genheader(self, ast : TranslationUnit):
        pprint(vars(ast))
        out = _DISCLAIMER.ws + "\n"
        out += _PROTO_HEAD

        if ast.namespaces:
            out += "package "
        for ns in ast.namespaces:
            out +=  + ns.name + ";\n"

        # print imports
        for inc in ast.includes:
            pprint(vars(inc))

        return out


    def genproto(self, ast : TranslationUnit, protoheadersdir : str, protosrcdir : str):
        # generate header and includes
        out = self.genheader(ast)

        # generate structs
        out += self.genStructs(ast)

        # generate protocol if it exists
        if ast.protocol:
            protocolname, out = self.protocolToProtobuf(ast.protocol)

        if ast.filetype == 'header':
            writeifmodified(out, os.path.join(protoheadersdir, f"{ast.name}.proto"))
        else:
            writeifmodified(out, os.path.join(protosrcdir, f"{protocolname}.proto"))

        print("todo")

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

    def mapImportedCxxType(self, importedCxxType : ImportedCxxType):
        # Type 1: map directly to corresponding scalar type
        out = ""
        if importedCxxType.name() in PBTypeMappings.keys():
            out += PBTypeMappings[importedCxxType.name()]
            self.counters['scalar_mappings'] += 1
        else:
            out += importedCxxType.name()
        return out


    def mapArrayType(self, arraytype : ArrayType):
        # create repeated param and map basetype recursively
        return "repeated " + self.mapType(arraytype.basetype)

    def mapBuiltinCType(self, builtinCType : BuiltinCType):
        # map directly to scalar type
        self.counters['scalar_mappings'] += 1
        return PBTypeMappings[builtinCType.name()]

    def mapActorType(self, actorType : ActorType):
        return "ActorType TODO"

    def mapStructType(self, structType : StructType):
        #pprint(vars(structType))
        #pprint(vars(structType.qname))
        # we have to define a seperate message
        return "StructType TODO"

    def mapUnionType(self, unionType : UnionType):
        return "UnionType TODO"

    def mapMaybeType(self, maybeType : MaybeType):
        return "MaybeType TODO"

    def mapFDType(self, fdType : FDType):
        return "FDTYPE TODO"

    def mapType(self, ipdltype : IPDLType):
        if isinstance(ipdltype, ImportedCxxType):
            return self.mapImportedCxxType(ipdltype)
        elif isinstance(ipdltype, BuiltinCType):
            return self.mapBuiltinCType(ipdltype)
        elif isinstance(ipdltype, ArrayType):
            return self.mapArrayType(ipdltype)
        elif isinstance(ipdltype, ActorType):
            return self.mapActorType(ipdltype)
        elif isinstance(ipdltype, StructType):
            return self.mapStructType(ipdltype)
        elif isinstance(ipdltype, UnionType):
            return self.mapUnionType(ipdltype)
        elif isinstance(ipdltype, MaybeType):
            return self.mapMaybeType(ipdltype)
        elif isinstance(ipdltype, FDType):
            return self.mapFDType(ipdltype)
        else:
            return "bytes"

    def protocolToProtobuf(self, protocol):
        out = _DISCLAIMER.ws + "\n"
        out += _PROTO_HEAD
        #pprint(vars(protocol))

        # used for stats
        param_count = 0
        self.counters = {
            'ImportedCxxType': 0,
            'BuiltinCType': 0,
            'ArrayType': 0,
            'ActorType': 0,
            'StructType': 0,
            'UnionType': 0,
            'MaybeType': 0,
            'FDType': 0,
            'other': 0,
            'scalar_mappings': 0
        }

        # for every message in this protocol...
        for msg in protocol.messageDecls:
            # add one proto message
            out += f"message {msg.name} " + "{\n"

            # initialize field numbers for this message
            field_number = 0

            for param in msg.params:
                #pprint(vars(param))
                #pprint(vars((param.ipdltype)))
                #if isinstance(param.ipdltype, ImportedCxxType):
                #    pprint(vars((param.ipdltype.qname)))

                # increment stats counter
                self.counters = ProtobufExporter.checkType(param.ipdltype, self.counters)
                param_count += 1

                # map type
                out += "   "
                out += self.mapType(param.ipdltype)
                out += " "

                # add name and field number
                out += param.name
                out += f" = {field_number}"

                # special case for arraytype
                if isinstance(param.ipdltype, ArrayType):
                    out += " [packed = true]"

                # close
                out += ";\n"

                # increase field_number
                field_number += 1
            out += "}\n\n"

        # print stats for this protocol
        out += "\n\n"
        out += "// Parameter mapping stats\n"
        out += f"// Total parameter count: {param_count}\n"
        out += f"//{self.counters}"
        return (protocol.name, out)
