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
    def convert(self, tu) -> ast.File:
        """returns |[ proto : File ]| representing the
        converted form of |tu|"""

        # Any modifications to the filename scheme here need corresponding
        # modifications in the ipdl.py driver script.
        pproto = ast.File()
        _GenerateProtobufCode().lower(tu, pproto)
        return pproto

    def genProto(self, file : ast.File) -> str:
        return ipdl.lower._DISCLAIMER.ws + generator.Generator().generate(file)

class _GenerateProtobufCode(ipdl.ast.Visitor):
    """Creates protobuf ast for given ipdl ast."""

    def __init__(self):
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
        self.protofile.file_elements = []
        tu.accept(self)

    def countParamTypes(self, ipdltype : ipdl.type.Type):
        self.param_count += 1
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
            # map directly to corresponding scalar type
            return PBTypeMappings[importedCxxType.name()]
        return "bytes" # otherwise just use bytes

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

    def mapType(self, ipdltype : ipdl.type.Type) -> str:
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

    def mapParam(self, param_name, ipdltype : ipdl.type.Type) -> ast.Field:
        self.countParamTypes(ipdltype)
        mapped_type = self.mapType(ipdltype)

        if (isinstance(ipdltype, ipdl.type.BuiltinCType) or
            isinstance(ipdltype, ipdl.type.ImportedCxxType)) and mapped_type != "bytes":
            self.scalar_mappings += 1

        cardinality = ast.FieldCardinality.REQUIRED
        if isinstance(ipdltype, ipdl.type.MaybeType):
            cardinality = ast.FieldCardinality.OPTIONAL
        elif isinstance(ipdltype, ipdl.type.ArrayType):
            cardinality = ast.FieldCardinality.REPEATED

        return ast.Field(param_name, 0, mapped_type, cardinality)


    def visitMessageDecl(self, md : ipdl.ast.MessageDecl):
        new_msg = ast.Message(md.name)
        field_num = 1
        for parm in md.inParams:
            field = self.mapParam(parm.progname, parm.type)
            field.number = field_num
            new_msg.elements.append(field)
            field_num += 1
        return new_msg


    def visitStructDecl(self, struct : ipdl.lower.StructDecl):
        new_struct = ast.Message(struct.name)
        field_number = 1
        for f in struct.fields:
            field = self.mapParam(f.name, f.ipdltype)
            field.number = field_number
            field_number += 1
            new_struct.elements.append(field)
        return new_struct

    def visitUnionDecl(self, union : ipdl.lower.UnionDecl):
        new_union = ast.Message(union.name)
        one_of = ast.OneOf("content")
        field_number = 1
        for f in union.components:
            field = self.mapParam(f.name, f.ipdltype)
            field.number = field_number
            field.cardinality = None
            field_number += 1
            one_of.elements.append(field)
        new_union.elements.append(one_of)
        return new_union

    def addElement(self, e : ast.MessageElement):
        self.protofile.file_elements.append(e)

    def visitTranslationUnit(self, tu : ipdl.ast.TranslationUnit):
        pf = self.protofile
        pf.syntax = "proto2"
        #option_runtime = ast.Option("optimize_for", ast.Identifier("LITE_RUNTIME"))
        option_runtime = ast.Comment("option optimize_for = LITE_RUNTIME;")
        namespace = "protobuf"
        for ns in tu.namespaces:
            namespace += f".{ns.name}"

        package = ast.Package(namespace)

        # converting includes
        for inc in tu.includes:
            self.imports.append(inc.accept(self))

        # converting structs and unions
        for su in tu.structsAndUnions:
            self.structsAndUnions.append(su.accept(self))

        # converting messages
        if tu.protocol:
            self.messages.extend(tu.protocol.accept(self))

        # converting is done, now adding all elements together into the ast
        self.addElement(option_runtime)
        self.addNL()
        self.addElement(package)

        if self.imports:
            self.addNL()
            for imp in self.imports:
                self.addElement(imp)

        self.addNL()

        # add structs and unions
        if self.structsAndUnions:
            self.addComment("// Structs and unions declarations")
            for su in self.structsAndUnions:
                self.addElement(su)
                self.addNL()

        # add messages
        if self.messages:
            self.addComment("// Message declarations")
            for msg in self.messages:
                self.addElement(msg)
                self.addNL()

        # add stats about parameters
        self.addComment("// Parameter mappings stats:")
        self.addComment(f"// Total parameters in this file {self.param_count}")
        self.addComment(f"// Parameter types:{self.counters}")
        self.addComment(f"// Scalar mappings performed: {self.scalar_mappings}")
        self.addComment(f"// Message structs/unions generated from ipdl structs/unions: {len(self.structsAndUnions)}")

    def addComment(self, cmt : str):
        self.addElement(ast.Comment(cmt))

    def addNL(self):
        self.addElement(_NL)

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

