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

#include "mozilla/dom/PContent.h"

#include <fstream>
#include <sstream>

#include "protobuf/PContent.pb.h"

#include "gfxFontUtils.h"
#include "mozilla/GfxMessageUtils.h"

using namespace mojo::core::ports;
using namespace mozilla::ipc;

typedef ::gfxSparseBitSet gfxSparseBitSet;


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

template<typename T>
UniquePtr<T> LibprotobufMapping::ParseTypedProtobuf(UniquePtr<TypedProtobuf> proto) {
    auto input = mozilla::MakeUnique<T>();
    if (input.ParseFromString(proto->serialized_data)) {
        return input;
    }
    return nullptr;
}

template<typename T>
UniquePtr<TypedProtobuf> LibprotobufMapping::SerializeTypedProtobuf(UniquePtr<T> proto, IPC::IPCMessages type) {
    UniquePtr<TypedProtobuf> output = mozilla::MakeUnique<TypedProtobuf>();
    output->serialized_data = proto.SerializeAsString();
    output->type = type;
    return output;
}

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


template<typename T>
IPC::ReadResult<std::string> LibprotobufMapping::ReadSerializedParam(IPC::MessageReader* reader) {
  size_t offset_before = reader->iter_.iter_.AbsoluteOffset();
  MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter AbsoluteOffset: %lu\n",
                    offset_before);

  //copy iter state
  Pickle::BufferList::IterImpl iter_before = reader->iter_.iter_;
  auto readResult = IPC::ReadParam<T>(reader);

  size_t offset_after = reader->iter_.iter_.AbsoluteOffset();
  MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter AbsoluteOffset After: %lu\n",
                  offset_after);
  size_t serialized_size = offset_after - offset_before;

  Vector<char, 256, InfallibleAllocPolicy> dumpBuffer;
  if (!dumpBuffer.initLengthUninitialized(serialized_size)) {
    MOZ_FUZZING_NYX_ABORT("dumpBuffer.initLengthUninitialized failed\n");
    return {};
  }
  if (!reader->message_.Buffers().ReadBytes(
          iter_before,
          reinterpret_cast<char*>(dumpBuffer.begin()),
          serialized_size)) {
    MOZ_FUZZING_NYX_ABORT("ReadBytes failed\n");
    return {};
  }

  std::string result = std::string(dumpBuffer.begin(), dumpBuffer.length());

  return std::move(result);
}

template<typename T>
std::string LibprotobufMapping::SerializeToString(T* param) {
  // create dummy msg
  mozilla::UniquePtr<IPC::Message> dummy_msg = mozilla::MakeUnique<IPC::Message>();
  IPC::MessageWriter writer__{
                (*(dummy_msg))};
  // let ParamTraits serialize the parameter into the dummy msg
  IPC::WriteParam((&(writer__)), param);

  // read entire payload of dummy msg and return as string
  return ReadPayloadFromMessage(dummy_msg);
}

template<typename T>
mozilla::Maybe<T> LibprotobufMapping::DeserializeFromString(std::string& payload) {
  // create dummy msg
  mozilla::UniquePtr<IPC::Message> dummy_msg = CreateMessageFromPayload(payload);

  // let ParamTraits deserialize the parameter
  IPC::MessageReader reader__{
                        *(dummy_msg)};

  T result;
  if (!IPC::ReadParam<T>(&reader__, &result)) {
    MOZ_FUZZING_NYX_ABORT("Deserialization from string failed\n");
    return mozilla::Nothing();
  }

  return mozilla::Some(std::move(result));
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
