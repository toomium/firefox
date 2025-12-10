import os
from ipdl.builtin import PBTypeMappings
from pprint import pprint
import ipdl.ast
import ipdl.lower
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

        return ipdl.lower._DISCLAIMER.ws + proto_gen


class _GenerateProtobufCode(ipdl.ast.Visitor):
    """Creates protobuf ast for given ipdl ast."""

    def __init__(self):
        self.protocol = None  # protocol we're generating a protobuf for
        self.protofile : ast.File = None # internal protobuf ast
        self.imports : list[ast.Import] = []
        self.messages : list[ast.Message] = []
        self.structsAndUnions : list[ast.Message] = []
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

    def checkType(self, ipdltype : ipdl.type.Type):
        if isinstance(ipdltype, ipdl.type.ImportedCxxType):
            self.counters['ImportedCxxType'] += 1
        elif isinstance(ipdltype, ipdl.type.BuiltinCType):
            self.counters['BuiltinCType'] += 1
        elif isinstance(ipdltype, ipdl.type.ArrayType):
            self.counters['ArrayType'] += 1
        elif isinstance(ipdltype, ipdl.type.ActorType):
            self.counters['ActorType'] += 1
        elif isinstance(ipdltype, ipdl.type.StructType):
            self.counters['StructType'] += 1
        elif isinstance(ipdltype, ipdl.type.UnionType):
            self.counters['UnionType'] += 1
        elif isinstance(ipdltype, ipdl.type.MaybeType):
            self.counters['MaybeType'] += 1
        elif isinstance(ipdltype, ipdl.type.FDType):
            self.counters['FDType'] += 1
        else:
            self.counters['other'] += 1

    def mapImportedCxxType(self, importedCxxType : ipdl.type.ImportedCxxType):
        if importedCxxType.name() in PBTypeMappings.keys():
            # Type 1: map directly to corresponding scalar type
            return PBTypeMappings[importedCxxType.name()]

        # otherwise bytes
        return "bytes"

    def mapArrayType(self, arraytype : ipdl.type.ArrayType):
        # create repeated param and map basetype recursively
        return self.mapType(arraytype.basetype)

    def mapBuiltinCType(self, builtinCType : ipdl.type.BuiltinCType):
        # map directly to scalar type
        return PBTypeMappings[builtinCType.name()]

    def mapActorType(self, actorType : ipdl.type.ActorType):
        return "bytes"

    def mapStructType(self, structType : ipdl.type.StructType):
        return structType.name()

    def mapUnionType(self, unionType : ipdl.type.UnionType):
        return unionType.name()

    def mapMaybeType(self, maybeType : ipdl.type.MaybeType):
        return self.mapType(maybeType.basetype)

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

    def mapParam(self, param_name, ipdltype):
        #pprint(vars(param))
        self.checkType(ipdltype)

        if isinstance(ipdltype, ipdl.type.ImportedCxxType):
            if ipdltype.name() in PBTypeMappings.keys():
                self.scalar_mappings += 1
            return ast.Field(param_name, 0, self.mapImportedCxxType(ipdltype), ast.FieldCardinality.REQUIRED)
        elif isinstance(ipdltype, ipdl.type.BuiltinCType):
            self.scalar_mappings += 1
            return ast.Field(param_name, 0, self.mapBuiltinCType(ipdltype), ast.FieldCardinality.REQUIRED)
        elif isinstance(ipdltype, ipdl.type.ArrayType):
            return ast.Field(param_name, 0, self.mapArrayType(ipdltype), ast.FieldCardinality.REPEATED)
        elif isinstance(ipdltype, ipdl.type.ActorType):
            return ast.Field(param_name, 0, self.mapActorType(ipdltype), ast.FieldCardinality.REQUIRED)
        elif isinstance(ipdltype, ipdl.type.StructType):
            return ast.Field(param_name, 0, self.mapStructType(ipdltype), ast.FieldCardinality.REQUIRED)
        elif isinstance(ipdltype, ipdl.type.UnionType):
            return ast.Field(param_name, 0, self.mapUnionType(ipdltype), ast.FieldCardinality.REQUIRED)
        elif isinstance(ipdltype, ipdl.type.MaybeType):
            return ast.Field(param_name, 0, self.mapMaybeType(ipdltype), ast.FieldCardinality.OPTIONAL)
        elif isinstance(ipdltype, ipdl.type.FDType):
            return ast.Field(param_name, 0, self.mapFDType(ipdltype), ast.FieldCardinality.REQUIRED)
        else:
            return ast.Field(param_name, 0, "bytes", ast.FieldCardinality.REQUIRED)


    def visitMessageDecl(self, md : ipdl.ast.MessageDecl):
        new_msg = ast.Message(md.name)
        field_num = 1

        #pprint(vars(md))
        for parm in md.inParams:
            field = self.mapParam(parm.progname, parm.type)
            field.number = field_num
            new_msg.elements.append(field)
            field_num += 1
            self.param_count += 1

        return new_msg


    def visitStructDecl(self, struct : ipdl.lower.StructDecl):
        # convert struct decl to message
        new_struct = ast.Message(struct.name)
        field_number = 1
        for f in struct.fields:
            field = self.mapParam(f.name, f.ipdltype)
            field.number = field_number
            field_number += 1
            new_struct.elements.append(field)

        self.structsAndUnions.append(new_struct)

    def visitUnionDecl(self, union : ipdl.lower.UnionDecl):
        # convert union struct to message
        new_union = ast.Message(union.name)
        one_of = ast.OneOf("content")
        field_number = 1
        for f in union.components:
            field = self.mapParam(f.name, f.ipdltype)
            field.number = field_number
            field_number += 1
            one_of.elements.append(field)

        new_union.elements.append(one_of)
        self.structsAndUnions.append(new_union)

    def visitTranslationUnit(self, tu : ipdl.ast.TranslationUnit):
        pf = self.protofile

        option_runtime = ast.Option("optimize_for", "LITE_RUNTIME")

        pf.syntax = "proto2"

        # converting includes
        for inc in tu.includes:
            self.imports.append(inc.accept(self))

        # converting structs and unions
        for su in tu.structsAndUnions:
            su.accept(self)

        # converting messages
        if tu.protocol:
            self.messages.extend(tu.protocol.accept(self))

        # converting structs


        # converting is done, now adding all elements together

        # build elements list of protobuf ast
        pf.file_elements = [option_runtime] + [_NL] + self.imports + [_NL]

        # print structs and unions
        pf.file_elements.append(ast.Comment("// Structs and unions declarations"))
        for su in self.structsAndUnions:
            pf.file_elements.append(su)
            pf.file_elements.append(_NL)

        # print messages
        pf.file_elements.append(ast.Comment("// Message declarations"))
        for msg in self.messages:
            pf.file_elements.append(msg)
            pf.file_elements.append(_NL)

        # print stats about parameters
        pf.file_elements.append(ast.Comment("\n\n// Parameter mappings stats:"))
        pf.file_elements.append(ast.Comment(f"//Total parameters in this file {self.param_count}"))
        pf.file_elements.append(ast.Comment(f"//Parameter types:\n{self.counters}"))
        pf.file_elements.append(ast.Comment(f"//Scalar mappings performed: {self.scalar_mappings}"))
        pf.file_elements.append(ast.Comment(f"//Message structs/unions generated from ipdl structs/unions: {len(self.structsAndUnions)}"))
        #pprint(vars(pf))


    def visitBuiltinCxxInclude(self, inc):
        pass

    def visitCxxInclude(self, inc):
        pass

    def visitInclude(self, inc : ipdl.ast.Include):
        base_name, ext = os.path.splitext(inc.file)
        if ext.lower() not in ('.ipdl', '.ipdlh'):
            print(f"Error: '{inc.file}' is not a .ipdl or .ipdlh file.")
            return

        return ast.Import(base_name + ".proto")

    def visitProtocol(self, p : ipdl.ast.Protocol):
        msgs : list[ast.Message] = []

        for msg in p.messageDecls:
            msgs.append(msg.accept(self))

        return msgs



# --------------------------------------------------

