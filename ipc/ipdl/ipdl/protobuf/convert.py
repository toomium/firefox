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
    def convert(self, tu) -> dict[str, ast.File]:
        """returns |[ proto : File ]| representing the
        converted form of |tu|"""

        # Any modifications to the filename scheme here need corresponding
        # modifications in the ipdl.py driver script.
        files = _GenerateProtobufCode().lower(tu)
        #pprint(files)
        return files

    def genProto(self, file : ast.File, ipdlname) -> str:
        return ipdl.lower._DISCLAIMER.ws + f"// Generated from {ipdlname}\n\n" + generator.Generator().generate(file)

class _GenerateProtobufCode(ipdl.ast.Visitor):
    """Creates protobuf ast for given ipdl ast."""

    def __init__(self):
        #self.protofile : ast.File = ast.File() # internal protobuf ast
        self.messages : list[ast.Message] = []
        self.namespacedStructsAndUnions : dict[str, list[ast.Message]] = {}
        self.namespacedProtoHeaders : dict[str, ast.File] = {}
        self.mainProtofile : ast.File = ast.File()
        self.imports : list[ast.Import] = []
        #self.messages : list[ast.Message] = []
        #self.structsAndUnions : list[ast.Message] = []
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

    def lower(self, tu):
        self.name = tu.name
        tu.accept(self)
        file_list : dict[str, ast.File] = dict()
        #file_list["main"] = self.namespacedProtofiles["main"]
        file_list["main"] = self.mainProtofile
        for ns, file in self.namespacedProtoHeaders.items():
            file_list[ns] = file
        return file_list

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
        # map basetype recursively
        return self.mapType(arraytype.basetype)

    def mapBuiltinCType(self, builtinCType : ipdl.type.BuiltinCType):
        # map directly to scalar type
        return PBTypeMappings[builtinCType.name()]

    def mapActorType(self, actorType : ipdl.type.ActorType):
        return "bytes"

    def mapStructType(self, structType : ipdl.type.StructType):
        qual = "protobuf"
        for ns in structType.qname.quals:
            qual += f".{ns}"
        return qual + "." + structType.name()

    def mapUnionType(self, unionType : ipdl.type.UnionType):
        qual = "protobuf"
        for ns in unionType.qname.quals:
            qual += f".{ns}"
        return qual + "." + unionType.name()

    def mapMaybeType(self, maybeType : ipdl.type.MaybeType):
        # map basetype recursively
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


    def visitMessageDecl(self, md : ipdl.lower.MessageDecl):
        gen_msgs = []
        send_msg = ast.Message(md.prettyMsgName())
        field_num = 1
        # add normal msg including incoming params
        for parm in md.inParams:
            field = self.mapParam(parm.progname, parm.type)
            field.number = field_num
            send_msg.elements.append(field)
            field_num += 1
        gen_msgs.append(send_msg)

        # add another message if there's a reply with outgoing params
        if md.hasReply():
            field_num = 1
            reply_msg = ast.Message(md.prettyReplyName())
            for parm in md.outParams:
                field = self.mapParam(parm.progname, parm.type)
                field.number = field_num
                reply_msg.elements.append(field)
                field_num += 1
            gen_msgs.append(reply_msg)

        return gen_msgs


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

    def addElement(self, f : ast.File, e : ast.MessageElement):
        f.file_elements.append(e)


    def buildMainProtofile(self, mf : ast.File, tu : ipdl.ast.TranslationUnit):
        # import all namespaced proto files publicly
        mf.syntax = "proto2"
        option_runtime = ast.Comment("option optimize_for = LITE_RUNTIME;")
        self.addElement(mf, option_runtime)
        self.addNL(mf)

        if tu.protocol:
            package = ast.Package(self.getNamespace(tu.protocol.namespaces) + "." + self.name)
            self.addElement(mf, package)
            self.addNL(mf)

        self.addComment(mf, "// Importing all namespaced protobuf children headers")
        for ns in self.namespacedProtoHeaders.keys():
            mf.file_elements.append(ast.Import(name=f"{tu.name}_{ns}.proto", public=True))
        self.addNL(mf)

        # adding protocol messages if there are any
        if self.messages:
            # if there's a protocol here, we also need the imports inherited by ipdl
            if self.imports:
                self.addComment(mf, "// Imports inherited by ipdl")
                for imp in self.imports:
                    self.addElement(mf, imp)
                self.addNL(mf)
            #  add protocol messages
            self.addComment(mf, "// Message declarations")
            for msg in self.messages:
                self.addElement(mf, msg)
                self.addNL(mf)

        # add stats about parameters
        self.addComment(mf, "// Parameter mappings stats:")
        self.addComment(mf, f"// Total parameters in this file {self.param_count}")
        self.addComment(mf, f"// Parameter types:{self.counters}")
        self.addComment(mf, f"// Scalar mappings performed: {self.scalar_mappings}")
        #self.addComment(mf, f"// Message structs/unions generated from ipdl structs/unions: {len(self.structsAndUnions)}")

    def buildNamespacedProtofile(self, ns : str, file : ast.File, tu : ipdl.ast.TranslationUnit):
        option_runtime = ast.Comment("option optimize_for = LITE_RUNTIME;")
        file.syntax = "proto2"

        package = ast.Package(ns)

        self.addElement(file, option_runtime)
        self.addNL(file)
        self.addElement(file, package)

        # add regular imports inherited from ipdl file
        if self.imports:
            self.addNL(file)
            for imp in self.imports:
                self.addElement(file, imp)
        self.addNL(file)

        # add parent namespaces
        names = ns.split(".")
        to_import = []
        for i in range(0, len(names)):
            potential_namespace = ".".join(names[:i])
            if potential_namespace in self.namespacedStructsAndUnions.keys():
                to_import.append(potential_namespace)
        if to_import:
            self.addComment(file, "// Importing other parent namespaces")
            for i in to_import:
                self.addElement(file, ast.Import(self.name + f"_{i}.proto"))
            self.addNL(file)


        # add structs and unions
        if ns in self.namespacedStructsAndUnions.keys():
            self.addComment(file, "// Structs and unions declarations")
            for su in self.namespacedStructsAndUnions[ns]:
                self.addElement(file, su)
                self.addNL(file)


    def visitTranslationUnit(self, tu : ipdl.ast.TranslationUnit):
        #self.namespacedProtofiles["protobuf"] = ast.File("proto2")

        # converting includes
        for inc in tu.includes:
            self.imports.append(inc.accept(self))

        # converting structs and unions
        for su in tu.structsAndUnions:
            new_su = su.accept(self)
            ns = self.getNamespace(su.namespaces)
            #print(ns)
            if ns not in self.namespacedStructsAndUnions.keys():
                self.namespacedStructsAndUnions[ns] = []
            self.namespacedStructsAndUnions[ns].append(new_su)
            #self.structsAndUnions.append(su.accept(self))

        #pprint(self.namespacedStructsAndUnions)
        # converting messages
        if tu.protocol:
            self.messages.extend(tu.protocol.accept(self))

        # build namespaced header files based on found namespaces in structs and unions
        #print(self.all_namespaces)
        for ns in self.namespacedStructsAndUnions.keys():
            self.namespacedProtoHeaders[ns] = ast.File()

        # converting is done, now adding all elements together into the ast
        self.buildMainProtofile(self.mainProtofile, tu)

        for ns, file in self.namespacedProtoHeaders.items():
            self.buildNamespacedProtofile(ns, file, tu)


    def addComment(self, file : ast.File, cmt : str):
        self.addElement(file, ast.Comment(cmt))

    def getNamespace(self, namespaces : list[ipdl.ast.Namespace], addParent = True) -> str:
        ret = ""
        if addParent:
            ret += "protobuf"
        for ns in namespaces:
            ret += "." + ns.name
        return ret


    def addNL(self, f : ast.File):
        self.addElement(f, _NL)

    def visitBuiltinCxxInclude(self, inc):
        pass

    def visitCxxInclude(self, inc):
        pass

    def visitInclude(self, inc : ipdl.ast.Include):
        base_name, ext = os.path.splitext(inc.file)
        if ext.lower() != '.ipdlh':
            #print(f"Error: '{inc.file}' is not a .ipdlh file.")
            return

        return ast.Import(base_name + ".proto")

    def visitProtocol(self, p : ipdl.ast.Protocol):
        msgs : list[ast.Message] = []

        for msg in p.messageDecls:
            msgs.extend(msg.accept(self))

        return msgs



# --------------------------------------------------

