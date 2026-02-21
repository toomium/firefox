import os
from ipdl.builtin import PBTypeMappings
from pprint import pprint
import ipdl.ast
import ipdl.lower
from ipdl.protobuf.parser.proto_schema_parser import ast, generator
import ipdl.type
from ipdl.protobuf import mapping

USE_PROTO3 = False
USE_LITE_RUNTIME = (os.getenv('FUZZING_SNAPSHOT_LPM_DEBUG') == None)


_NL = ast.Comment("")

class ConvertToProto:
    def convert(self, tu) -> dict[str, ast.File]:
        """returns |[ proto : File ]| representing the
        converted form of |tu|"""

        files = _GenerateProtobufCode(tu).lower(tu)
        return files

    def genProto(self, file : ast.File, ipdlname) -> str:
        return ipdl.lower._DISCLAIMER.ws + f"// Generated from {ipdlname}\n\n" + generator.Generator().generate(file)


def getNamespace(sep : str, namespaces: list[ipdl.ast.Namespace], addParent=True) -> str:
    parts = []
    if addParent:
        parts.append("protobuf")

    for ns in namespaces:
        parts.append(ns.name)

    return sep.join(parts)



def getProtobufVarName(name: str):
    # append "a_" as prefix to avoid reserved names like "descriptor"
    return "a_" + name

def getUnionArrayMemberType(name: str):
    # returns the type of the dummy message constructed for array types inside unions
    return getProtobufVarName("type_" + name)

def getUnionEnumName(name: str):
    # name is protobuf variable name
    # analogue to protoc behaviours, see: https://github.com/protocolbuffers/protobuf/blob/main/src/google/protobuf/compiler/cpp/helpers.cc
    result = ""
    cap_next = True
    for char in name:
        if 'a' <= char <= 'z':
            if cap_next:
                result += char.upper()
            else:
                result += char
            cap_next = False
        elif 'A' <= char <= 'Z':
            result += char
            cap_next = False
        elif '0' <= char <= '9':
            result += char
            cap_next = True
        else:
            cap_next = True
    return "k" + result
    # parts = name.split('_')
    # ret = "k"
    # for part in parts:
    #     ret += part[0].upper() + part[1:]
    # return ret


class _GenerateProtobufCode(ipdl.ast.Visitor):
    """Creates protobuf ast for given ipdl ast."""

    def __init__(self, tu : ipdl.ast.TranslationUnit):
        self.typeVisitor = mapping.ProtobufTypeMapper()
        self.name = tu.name
        self.messages : list[ast.Message] = []
        self.namespacedStructsAndUnions : dict[str, list[ast.Message]] = {}
        self.namespacedHeaders : dict[str, ast.File] = {}
        self.mainProtofile : ast.File = ast.File()
        self.imports : list[ast.Import] = []

    def lower(self, tu):
        tu.accept(self)
        file_list : dict[str, ast.File] = dict()
        file_list["main"] = self.mainProtofile
        for ns, file in self.namespacedHeaders.items():
            file_list[ns] = file
        return file_list

    def mapParam(self, param_name, ipdltype : ipdl.type.Type) -> ast.Field:
        mapped_type = self.typeVisitor.mapType(ipdltype)

        if USE_PROTO3:
            cardinality = None
        else:
            cardinality = ast.FieldCardinality.REQUIRED

        if isinstance(ipdltype, ipdl.type.MaybeType) or ipdltype.isRefcounted() or mapping.IPDLTypeIsSimple(ipdltype):
            cardinality = ast.FieldCardinality.OPTIONAL
        elif isinstance(ipdltype, ipdl.type.ArrayType):
            cardinality = ast.FieldCardinality.REPEATED

        return ast.Field(getProtobufVarName(param_name), 0, mapped_type, cardinality)

    def visitMessageDecl(self, md : 'ipdl.lower.MessageDecl'):
        gen_msgs = []
        send_msg = ast.Message(md.prettyMsgName())
        field_num = 1

        # check if msg is constructor
        if str(md.prettyMsgName()).endswith("Constructor"):
            # if so, then add a "long" parameter at the start
            # since all ctor's carry an actorid at the front
            field = self.mapParam("actorid", ipdl.type.BuiltinCType("long"))
            field.number = field_num
            send_msg.elements.append(field)
            field_num += 1

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


    def visitStructDecl(self, struct : 'ipdl.lower.StructDecl'):
        new_struct = ast.Message(struct.name)
        field_number = 1
        for f in struct.fields:
            field = self.mapParam(f.name, f.ipdltype)
            field.number = field_number
            field_number += 1
            new_struct.elements.append(field)
        return new_struct

    def visitUnionDecl(self, union : 'ipdl.lower.UnionDecl'):
        new_union = ast.Message(union.name)
        one_of = ast.OneOf("content")
        field_number = 1
        oneof_elements = []
        for f in union.components:
            field = self.mapParam(f.name, f.ipdltype)
            if field.cardinality == ast.FieldCardinality.REPEATED:
                # add param to nested message instead
                msg = ast.Message(getUnionArrayMemberType(f.name))
                field.number = 1
                msg.elements.append(field)
                new_union.elements.append(msg)
                # add dummy to one-of pointing to this nested message
                dummy_field = ast.Field(getProtobufVarName(f.name), field_number, getUnionArrayMemberType(f.name))
                field_number += 1
                oneof_elements.append(dummy_field)
            else:
                field.number = field_number
                field.cardinality = None
                field_number += 1
                oneof_elements.append(field)

        one_of.elements.extend(oneof_elements)    
        new_union.elements.append(one_of)
        return new_union

    def addElement(self, f : ast.File, e : ast.MessageElement):
        f.file_elements.append(e)


    def buildMainProtofile(self, mf : ast.File, tu : ipdl.ast.TranslationUnit):
        # import all namespaced proto files publicly
        if USE_PROTO3:
            mf.syntax = "proto3"
        else:
            mf.syntax = "proto2"

        if USE_LITE_RUNTIME:
            option_runtime = ast.Comment("option optimize_for = LITE_RUNTIME;")
            self.addElement(mf, option_runtime)

        self.addNL(mf)

        if tu.protocol:
            package = ast.Package(getNamespace(".", tu.protocol.namespaces) + "." + self.name)
            self.addElement(mf, package)
            self.addNL(mf)

        self.addComment(mf, "// Importing all namespaced protobuf children headers")
        for ns in self.namespacedHeaders.keys():
            mf.file_elements.append(ast.Import(name=f"{self.name}_{ns}.h.proto", public=True))
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
        self.addComment(mf, f"// Total parameters in this file {self.typeVisitor.getParamCount()}")
        self.addComment(mf, f"// Parameter types:{self.typeVisitor.getCounters()}")
        self.addComment(mf, f"// Simple mappings performed: {self.typeVisitor.getScalarMappings()}")
        self.addComment(mf, f"// Structured mappings performed: {self.typeVisitor.getStructuredMappings()}")
        self.addComment(mf, f"// Message structs/unions generated from ipdl structs/unions: {sum([len(x) for x in self.namespacedStructsAndUnions.values()])}")

    def buildHeader(self, ns : str, file : ast.File, tu : ipdl.ast.TranslationUnit):
        if USE_PROTO3:
            file.syntax = "proto3"
        else:
            file.syntax = "proto2"

        if USE_LITE_RUNTIME:
            option_runtime = ast.Comment("option optimize_for = LITE_RUNTIME;")
            self.addElement(file, option_runtime)

        self.addNL(file)
        package = ast.Package(ns)
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
                self.addElement(file, ast.Import(self.name + f"_{i}.h.proto"))
            self.addNL(file)


        # add structs and unions
        if ns in self.namespacedStructsAndUnions.keys():
            self.addComment(file, "// Structs and unions declarations")
            for su in self.namespacedStructsAndUnions[ns]:
                self.addElement(file, su)
                self.addNL(file)


    def visitTranslationUnit(self, tu : ipdl.ast.TranslationUnit):
        # converting includes
        for inc in tu.includes:
            self.imports.append(inc.accept(self))

        # converting structs and unions to protobuf message format
        for su in tu.structsAndUnions:
            conv_su = su.accept(self)
            ns = getNamespace(".", su.namespaces)
            if ns not in self.namespacedStructsAndUnions.keys():
                self.namespacedStructsAndUnions[ns] = []
            self.namespacedStructsAndUnions[ns].append(conv_su)

        # converting messages
        if tu.protocol:
            self.messages.extend(tu.protocol.accept(self))

        # build namespaced header files based on found namespaces in structs and unions
        for ns in self.namespacedStructsAndUnions.keys():
            self.namespacedHeaders[ns] = ast.File()

        # converting is done. Now build all files
        self.buildMainProtofile(self.mainProtofile, tu)

        for ns, file in self.namespacedHeaders.items():
            self.buildHeader(ns, file, tu)


    def addComment(self, file : ast.File, cmt : str):
        self.addElement(file, ast.Comment(cmt))

    def addNL(self, f : ast.File):
        self.addElement(f, _NL)

    def visitBuiltinCxxInclude(self, inc):
        pass

    def visitCxxInclude(self, inc):
        pass

    def visitInclude(self, inc : ipdl.ast.Include):
        base_name, ext = os.path.splitext(inc.file)
        # ignore non header includes
        if ext.lower() != '.ipdlh':
            return

        return ast.Import(base_name + ".proto")

    def visitProtocol(self, p : ipdl.ast.Protocol):
        msgs : list[ast.Message] = []

        for msg in p.messageDecls:
            msgs.extend(msg.accept(self))

        return msgs

