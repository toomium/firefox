
from ipdl.builtin import PBTypeMappings
from pprint import pprint
import ipdl.ast
from ipdl.lower import _DISCLAIMER
from ipdl.protobuf.parser.proto_schema_parser import ast, generator
import ipdl.type
#from parser.proto_schema_parser import *


_NL = ast.Comment("")

class ConvertToProto:
    def convert(self, tu):
        """returns |[ proto : File ]| representing the
        converted form of |tu|"""

        # Any modifications to the filename scheme here need corresponding
        # modifications in the ipdl.py driver script.
        name = tu.name
        pproto = ast.File()

        _GenerateProtobufCode().lower(tu, pproto)

        proto_gen = generator.Generator().generate(pproto)

        return _DISCLAIMER.ws + proto_gen


class _GenerateProtobufCode(ipdl.ast.Visitor):
    """Creates protobuf ast for given ipdl ast."""

    def __init__(self):
        self.protocol = None  # protocol we're generating a protobuf for
        self.protofile : ast.File = None # internal protobuf ast
        self.imports : list[ast.Import] = []
        self.messages : list[ast.Message] = []
        self.scalar_mappings = 0
        self.param_count = 0
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
        }

    def lower(self, tu, protoFile):
        self.protofile = protoFile
        #self.protofile.file_elements = []
        tu.accept(self)

    def visitDecl(self, d):
        return d.progname

    def checkType(ipdltype : ipdl.type.Type, counters):
        if isinstance(ipdltype, ipdl.type.ImportedCxxType):
            counters['ImportedCxxType'] += 1
        elif isinstance(ipdltype, ipdl.type.BuiltinCType):
            counters['BuiltinCType'] += 1
        elif isinstance(ipdltype, ipdl.type.ArrayType):
            counters['ArrayType'] += 1
        elif isinstance(ipdltype, ipdl.type.ActorType):
            counters['ActorType'] += 1
        elif isinstance(ipdltype, ipdl.type.StructType):
            counters['StructType'] += 1
        elif isinstance(ipdltype, ipdl.type.UnionType):
            counters['UnionType'] += 1
        elif isinstance(ipdltype, ipdl.type.MaybeType):
            counters['MaybeType'] += 1
        elif isinstance(ipdltype, ipdl.type.FDType):
            counters['FDType'] += 1
        else:
            counters['other'] += 1
        return counters

    def mapImportedCxxType(self, importedCxxType : ipdl.type.ImportedCxxType):
        if importedCxxType.name() in PBTypeMappings.keys():
            # Type 1: map directly to corresponding scalar type
            self.scalar_mappings += 1
            return PBTypeMappings[importedCxxType.name()]

        # otherwise bytes
        return "bytes"

    def mapArrayType(self, arraytype : ipdl.type.ArrayType):
        # create repeated param and map basetype recursively
        return "repeated " + self.mapType(arraytype.basetype)

    def mapBuiltinCType(self, builtinCType : ipdl.type.BuiltinCType):
        # map directly to scalar type
        self.scalar_mappings += 1
        return PBTypeMappings[builtinCType.name()]

    def mapActorType(self, actorType : ipdl.type.ActorType):
        return "bytes"

    def mapStructType(self, structType : ipdl.type.StructType):
        #pprint(vars(structType))
        #pprint(vars(structType.qname))
        # we have to define a seperate message
        return "StructType TODO"

    def mapUnionType(self, unionType : ipdl.type.UnionType):
        return "UnionType TODO"

    def mapMaybeType(self, maybeType : ipdl.type.MaybeType):
        return "MaybeType TODO"

    def mapFDType(self, fdType : ipdl.type.FDType):
        return "bytes"

    def mapType(self, ipdltype : ipdl.type.Type):
        if isinstance(ipdltype, ipdl.type.ImportedCxxType):
            return self.mapImportedCxxType(ipdltype)
        elif isinstance(ipdltype, ipdl.type.BuiltinCType):
            return self.mapBuiltinCType(ipdltype)
        elif isinstance(ipdltype, ipdl.type.ArrayType):
            return self.mapArrayType(ipdltype)
        elif isinstance(ipdltype, ipdl.type.ActorType):
            return self.mapActorType(ipdltype)
        elif isinstance(ipdltype, ipdl.type.StructType):
            return self.mapStructType(ipdltype)
        elif isinstance(ipdltype, ipdl.type.UnionType):
            return self.mapUnionType(ipdltype)
        elif isinstance(ipdltype, ipdl.type.MaybeType):
            return self.mapMaybeType(ipdltype)
        elif isinstance(ipdltype, ipdl.type.FDType):
            return self.mapFDType(ipdltype)
        else:
            return "bytes"

    def visitMessageDecl(self, md : ipdl.ast.MessageDecl):
        new_msg = ast.Message(md.name)
        msg_elements : list[ast.Field]= []
        field_num = 1

        pprint(vars(md))
        for parm in md.inParams:
            #pprint(vars(parm))
            pprint(vars(parm))
            new_msg.elements.append(ast.Field(parm.accept(self), field_num, self.mapType(parm.type)))
            field_num += 1
            self.param_count += 1

        return new_msg


    def visitTranslationUnit(self, tu : ipdl.ast.TranslationUnit):
        pf = self.protofile

        option_runtime = ast.Option("optimize_for", "LITE_RUNTIME")

        pf.syntax = "proto2"

        # converting includes
        for inc in tu.includes:
            self.imports.append(inc.accept(self))

        # converting messages
        if tu.protocol:
            self.messages.extend(tu.protocol.accept(self))

        # converting structs

        #pprint(self.messages)
        # build elements list of protobuf ast
        pf.file_elements = [option_runtime] + [_NL] + self.imports + [_NL]

        for msg in self.messages:
            pf.file_elements.extend([msg])
            pf.file_elements.extend([_NL])

        # add stats about parameters
        pf.file_elements.append(ast.Comment("\n\n// Parameter mappings stats:"))
        pf.file_elements.append(ast.Comment(f"Total parameters in this file {self.param_count}"))
        pf.file_elements.append(ast.Comment(f"//{self.counters}"))

        pprint(vars(pf))


    def visitBuiltinCxxInclude(self, inc):
        pass

    def visitCxxInclude(self, inc):
        pass

    def visitInclude(self, inc : ipdl.ast.Include):
        return ast.Import(inc.file)

    def visitProtocol(self, p : ipdl.ast.Protocol):
        msgs : list[ast.Message] = []

        for msg in p.messageDecls:
            msgs.append(msg.accept(self))

        return msgs



# --------------------------------------------------

