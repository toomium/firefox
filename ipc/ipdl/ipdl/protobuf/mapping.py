from ipdl.builtin import PBTypeMappings
import ipdl.type


def IPDLTypeIsSimple(type):
    return isinstance(type, ipdl.type.BuiltinCType) or (isinstance(type, ipdl.type.ImportedCxxType) and type.name() in PBTypeMappings.keys())

def IPDLTypeIsStructured(type):
    return isinstance(type, ipdl.type.StructType) or isinstance(type, ipdl.type.UnionType)

def IPDLTypeIsModifier(type):
    return isinstance(type, ipdl.type.MaybeType) or isinstance(type, ipdl.type.NotNullType) or isinstance(type, ipdl.type.ArrayType)

def IPDLTypeIsComplex(type):
    return not (IPDLTypeIsSimple(type) or IPDLTypeIsModifier(type) or IPDLTypeIsStructured(type))


class ProtobufTypeMapper(ipdl.type.TypeVisitor):

    def __init__(self):
        self.counters = {
            str(ipdl.type.ActorType) : 0,
            str(ipdl.type.ArrayType) : 0,
            str(ipdl.type.BuiltinCType) : 0,
            str(ipdl.type.ByteBufType) : 0,
            str(ipdl.type.EndpointType) : 0,
            str(ipdl.type.FDType): 0,
            str(ipdl.type.ImportedCxxType) : 0,
            str(ipdl.type.ManagedEndpointType) : 0,
            str(ipdl.type.MaybeType) : 0,
            str(ipdl.type.NotNullType) : 0,
            str(ipdl.type.ProtocolType) : 0,
            str(ipdl.type.ShmemType): 0,
            str(ipdl.type.StructType) : 0,
            str(ipdl.type.UnionType) : 0,
            str(ipdl.type.UniquePtrType) : 0,
        }
        self.scalarMappings = 0
        self.structuredMappings = 0

        self.paramCount = 0
        super().__init__()

    def countParamTypes(self, ipdltype : ipdl.type.Type):
        self.counters[str(type(ipdltype))] += 1

    def mapType(self, type : ipdl.type.Type, countParam=True):
        if countParam:
            self.countParamTypes(type)

        mapped_type = type.accept(self)

        if IPDLTypeIsSimple(type):
            self.scalarMappings += 1
        elif IPDLTypeIsStructured(type):
            self.structuredMappings += 1

        return mapped_type

    def visitActorType(self, a : ipdl.type.ActorType, *args):
        return "bytes"

    def visitBuiltinCType(self, b : ipdl.type.BuiltinCType, *args):
        return PBTypeMappings[b.name()]

    def visitByteBufType(self, s : ipdl.type.ByteBufType, *args):
        return "bytes"

    def visitEndpointType(self, s : ipdl.type.EndpointType, *args):
        return "bytes"

    def visitArrayType(self, a : ipdl.type.ArrayType, *args):
        return self.mapType(a.basetype, countParam=False)

    def visitFDType(self, s : ipdl.type.ArrayType, *args):
        return "bytes"

    def visitImportedCxxType(self, t : ipdl.type.ImportedCxxType, *args):
        if t.name() in PBTypeMappings.keys():
            # map directly to corresponding scalar type
            return PBTypeMappings[t.name()]
        return "bytes" # otherwise just use bytes

    def visitManagedEndpointType(self, s : ipdl.type.ManagedEndpointType, *args):
        return "bytes"

    def visitMaybeType(self, m : ipdl.type.MaybeType, *args):
        return self.mapType(m.basetype, countParam=False)

    def visitMessageType(self, m, *args):
        return super().visitMessageType(m, *args)

    def visitNotNullType(self, m : ipdl.type.NotNullType, *args):
        return self.mapType(m.basetype, countParam=False)

    def visitProtocolType(self, p : ipdl.type.ProtocolType, *args):
        return "bytes"

    def visitShmemType(self, s : ipdl.type.ShmemType, *args):
        return "bytes"

    def visitStructType(self, s : ipdl.type.StructType, *args):
        qual = "protobuf"
        for ns in s.qname.quals:
            qual += f".{ns}"
        return qual + "." + s.name()

    def visitUnionType(self, u : ipdl.type.UnionType, *args):
        qual = "protobuf"
        for ns in u.qname.quals:
            qual += f".{ns}"
        return qual + "." + u.name()

    def visitUniquePtrType(self, m : ipdl.type.UniquePtrType, *args):
        return "bytes"

    def visitVoidType(self, v : ipdl.type.VoidType, *args):
        return "bytes"

    def defaultVisit(self, node, *args):
        return super().defaultVisit(node, *args)

    def getCounters(self):
        return self.counters

    def getScalarMappings(self):
        return self.scalarMappings

    def getStructuredMappings(self):
        return self.structuredMappings

    def getParamCount(self):
        return sum(self.counters.values())
