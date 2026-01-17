/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#include "LibprotobufMapping.h"
#include "IPCMessageStart.h"

#include "nsThreadUtils.h"

#include "mozilla/ipc/MessageLink.h"
#include "chrome/common/ipc_message_utils.h"

#include <fstream>
#include <sstream>


using namespace mojo::core::ports;
using namespace mozilla::ipc;

namespace mozilla {
namespace fuzzing {

// mozilla::UniquePtr<IPC::Message> CreateMessageFromPayload(const std::string& payload) {
//     uint32_t payload_size = payload.size();
//     std::vector<char> buffer(sizeof(IPC::Message::Header) + payload_size);

//     // write dummy header
//     IPC::Message::Header* header = reinterpret_cast<IPC::Message::Header*>(buffer.data());
//     header->payload_size = payload_size;

//     // copy payload to buffer
//     memcpy(buffer.data() + sizeof(IPC::Message::Header), payload.data(), payload_size);

//     // create msg from buffer
//     auto msg = std::make_unique<IPC::Message>(buffer.data(), buffer.size());
//     return msg;
// }

// const std::string ReadPayloadFromMessage(mozilla::UniquePtr<IPC::Message>& msg) {
//     Pickle::BufferList::IterImpl iter(msg->Buffers());

//     Vector<char, 256, InfallibleAllocPolicy> dumpBuffer;
//     if (!dumpBuffer.initLengthUninitialized(msg->Buffers().Size())) {
//         MOZ_FUZZING_NYX_ABORT("dumpBuffer.initLengthUninitialized failed\n");
//     }

//     // copy from buffer but skip header
//     if (!msg->Buffers().ReadBytes(
//                                     iter,
//                                     reinterpret_cast<char*>(dumpBuffer.begin() + sizeof(IPC::Message::Header)),
//                                     dumpBuffer.length() - sizeof(IPC::Message::Header))) {
//         MOZ_FUZZING_NYX_ABORT("ReadBytes failed\n");
//     }

//     return std::string(reinterpret_cast<char*>(dumpBuffer.begin()),
//                dumpBuffer.length());
// }

// // static
// LibprotobufMapping& LibprotobufMapping::instance() {
//   static LibprotobufMapping lib;
//   return lib;
// }

mozilla::UniquePtr<IPC::Message> LibprotobufMapping::CreateMessageFromPayload(const std::string& payload) {
    uint32_t payload_size = payload.size();
    std::vector<char> buffer(sizeof(IPC::Message::Header) + payload_size);

    // write dummy header
    IPC::Message::Header* header = reinterpret_cast<IPC::Message::Header*>(buffer.data());
    header->payload_size = payload_size;

    // copy payload to buffer
    memcpy(buffer.data() + sizeof(IPC::Message::Header), payload.data(), payload_size);

    // create msg from buffer
    mozilla::UniquePtr<IPC::Message> msg = mozilla::MakeUnique<IPC::Message>(buffer.data(), buffer.size());
    return msg;
}

nsCString nsCString_ToIPC(std::string& str) {
    nsCString res;
    res.Assign(str.data(), str.length());
    return res;
}

std::string nsCString_ToProtobuf(nsCString& str) {
    return std::string(str.get(), str.Length());
}

nsString nsString_ToIPC(std::string& str) {
    NS_ConvertUTF8toUTF16 converter(str.data(), str.length());
    return nsString(converter);
}

std::string nsString_ToProtobuf(nsString& str) {
    NS_ConvertUTF16toUTF8 converter(str);
    return std::string(converter.get(), converter.Length());
}

std::string LibprotobufMapping::ReadPayloadFromMessage(mozilla::UniquePtr<IPC::Message>& msg) {
    Pickle::BufferList::IterImpl iter(msg->Buffers());

    Vector<char, 256, InfallibleAllocPolicy> dumpBuffer;
    if (!dumpBuffer.initLengthUninitialized(msg->Buffers().Size())) {
        MOZ_FUZZING_NYX_ABORT("dumpBuffer.initLengthUninitialized failed\n");
    }

    // copy from buffer but skip header
    if (!msg->Buffers().ReadBytes(
                                    iter,
                                    reinterpret_cast<char*>(dumpBuffer.begin() + sizeof(IPC::Message::Header)),
                                    dumpBuffer.length() - sizeof(IPC::Message::Header))) {
        MOZ_FUZZING_NYX_ABORT("ReadBytes failed\n");
    }

    return std::string(reinterpret_cast<char*>(dumpBuffer.begin()),
               dumpBuffer.length());
}


// UniquePtr<IPC::Message> LibprotobufMapping::ConvertProtobufToIPCMessage
// (UniquePtr<TypedProtobuf>& protobuf) {
//     UniquePtr<IPC::Message> msg;

//     switch(protobuf->type){
//       case dom::PContent::Msg_SetCharacterMap__ID: {
//         // first deserialize protobuf
//         protobuf::mozilla::dom::PContent::Msg_SetCharacterMap input;

//         input.ParseFromString(protobuf->serialized_data);

//         msg = dom::PContent::Msg_SetCharacterMap(MSG_ROUTING_CONTROL);
//         IPC::MessageWriter writer__{
//                 (*(msg))};

//         IPC::WriteParam((&(writer__)), input.ageneration());
//         // Sentinel = 'aGeneration'
//         ((&(writer__)))->WriteSentinel(430179438);
//         IPC::WriteParam((&(writer__)), input.afamilyindex());
//         // Sentinel = 'aFamilyIndex'
//         ((&(writer__)))->WriteSentinel(501089468);
//         IPC::WriteParam((&(writer__)), input.aalias());
//         // Sentinel = 'aAlias'
//         ((&(writer__)))->WriteSentinel(129040972);
//         IPC::WriteParam((&(writer__)), input.afaceindex());
//         // Sentinel = 'aFaceIndex'
//         ((&(writer__)))->WriteSentinel(335021001);
//         //IPC::WriteParam((&(writer__)), MakeUnique<gfxSparseBitSet>());
//         ((&(writer__)))->WriteBytes(input.amap().c_str(), input.amap().length());
//         // Sentinel = 'aMap'

//         ((&(writer__)))->WriteSentinel(60883328);
//         break;
//       }

//       default: {
//         break;
//       }
//     }

//     return msg;
// }

// UniquePtr<TypedProtobuf> LibprotobufMapping::ConvertIPCMessageToProtobuf(UniquePtr<IPC::Message>& msg){

//   MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto]: %s Size: %u\n",
//                            IPC::StringFromIPCMessageType(msg->type()),
//                            msg->header()->payload_size);

//   UniquePtr<TypedProtobuf> output = MakeUnique<TypedProtobuf>();

//   switch (msg->type()){
//     case dom::PContent::Msg_SetCharacterMap__ID: {
//       // create protobuf
//       protobuf::mozilla::dom::PContent::Msg_SetCharacterMap proto;

//       // read parameter
//       IPC::MessageReader reader__{
//                         *(msg)};
//       auto maybe__aGeneration = IPC::ReadParam<uint32_t>((&(reader__)));

//       auto& aGeneration = *maybe__aGeneration;
//       MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter Generation: %u\n",
//                       aGeneration);
//       proto.set_ageneration(aGeneration);


//       // Sentinel = 'aGeneration'
//       if ((!(((&(reader__)))->ReadSentinel(430179438)))) {
//           mozilla::ipc::SentinelReadError("Error deserializing 'uint32_t'");
//       }
//       auto maybe__aFamilyIndex = IPC::ReadParam<uint32_t>((&(reader__)));

//       auto& aFamilyIndex = *maybe__aFamilyIndex;
//       MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter FamilyIndex: %u\n",
//                       aFamilyIndex);
//       proto.set_afamilyindex(aFamilyIndex);

//       // Sentinel = 'aFamilyIndex'
//       if ((!(((&(reader__)))->ReadSentinel(501089468)))) {
//           mozilla::ipc::SentinelReadError("Error deserializing 'uint32_t'");
//       }
//       auto maybe__aAlias = IPC::ReadParam<bool>((&(reader__)));

//       auto& aAlias = *maybe__aAlias;
//       MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter Alias: %u\n",
//                       aAlias);
//       proto.set_aalias(aAlias);

//       // Sentinel = 'aAlias'
//       if ((!(((&(reader__)))->ReadSentinel(129040972)))) {
//           mozilla::ipc::SentinelReadError("Error deserializing 'bool'");
//       }
//       auto maybe__aFaceIndex = IPC::ReadParam<uint32_t>((&(reader__)));

//       auto& aFaceIndex = *maybe__aFaceIndex;
//       MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter FaceIndex: %u\n",
//                       aFaceIndex);
//       proto.set_afaceindex(aFaceIndex);

//       // Sentinel = 'aFaceIndex'
//       if ((!(((&(reader__)))->ReadSentinel(335021001)))) {
//           mozilla::ipc::SentinelReadError("Error deserializing 'uint32_t'");
//       }

//       // Read as serialized
//       std::string aMap = ReadSerializedParam<gfxSparseBitSet>(&(reader__), msg);
//       proto.set_amap(aMap);

//       // Sentinel = 'aMap'
//       if ((!(((&(reader__)))->ReadSentinel(60883328)))) {
//           mozilla::ipc::SentinelReadError("Error deserializing 'gfxSparseBitSet'");
//       }
//       reader__.EndRead();

//       MOZ_FUZZING_NYX_PRINT("INFO: [ConvertToProto] Proto created\n");

//       output->type = dom::PContent::Msg_SetCharacterMap__ID;
//       output->serialized_data = proto.SerializeAsString();

//       break;
//     }
//     default:
//     {
//       //
//       break;
//     }
//   }

//   return output;
// }

}  // namespace fuzzing
}  // namespace mozilla
