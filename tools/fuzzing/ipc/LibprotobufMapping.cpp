/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#include "LibprotobufMapping.h"

#include "nsThreadUtils.h"

#include "mozilla/ipc/MessageLink.h"
#include "chrome/common/ipc_message_utils.h"

#include "mozilla/dom/PContent.h"

#include <fstream>
#include <sstream>

#include "protobuf/test.pb.h"
#include "protobuf/SetCharacterMap.pb.h"

#include "gfxFontUtils.h"
#include "mozilla/GfxMessageUtils.h"

using namespace mojo::core::ports;
using namespace mozilla::ipc;

typedef ::gfxSparseBitSet gfxSparseBitSet;


namespace mozilla {
namespace fuzzing {

// static
LibprotobufMapping& LibprotobufMapping::instance() {
  static LibprotobufMapping lib;
  return lib;
}

UniquePtr<IPC::Message> LibprotobufMapping::ConvertProtobufToIPCMessage
(UniquePtr<TypedProtobuf> protobuf) {
    UniquePtr<IPC::Message> msg;

    switch(protobuf->type){
      case dom::PContent::Msg_ExtProtocolChannelConnectParent__ID: {
        // first deserialize protobuf
        ExtProtocolChannelConnectParent input;

        input.ParseFromString(protobuf->serialized_data);

        auto registrarId = input.registrarid();

        // then create new message
        msg = dom::PContent::Msg_ExtProtocolChannelConnectParent(MSG_ROUTING_CONTROL);
        IPC::MessageWriter writer__{
            (*(msg))};

        IPC::WriteParam((&(writer__)), registrarId);
        // Sentinel = 'registrarId'
        ((&(writer__)))->WriteSentinel(464585857);
        break;
      }
      case dom::PContent::Msg_SetCharacterMap__ID: {
        // first deserialize protobuf
        SetCharacterMap input;

        input.ParseFromString(protobuf->serialized_data);

        msg = dom::PContent::Msg_SetCharacterMap(MSG_ROUTING_CONTROL);
        IPC::MessageWriter writer__{
                (*(msg))};

        IPC::WriteParam((&(writer__)), input.ageneration());
        // Sentinel = 'aGeneration'
        ((&(writer__)))->WriteSentinel(430179438);
        IPC::WriteParam((&(writer__)), input.afamilyindex());
        // Sentinel = 'aFamilyIndex'
        ((&(writer__)))->WriteSentinel(501089468);
        IPC::WriteParam((&(writer__)), input.aalias());
        // Sentinel = 'aAlias'
        ((&(writer__)))->WriteSentinel(129040972);
        IPC::WriteParam((&(writer__)), input.afaceindex());
        // Sentinel = 'aFaceIndex'
        ((&(writer__)))->WriteSentinel(335021001);
        IPC::WriteParam((&(writer__)), *(new gfxSparseBitSet()));
        // Sentinel = 'aMap'
        ((&(writer__)))->WriteSentinel(60883328);
        break;
      }

      default: {
        break;
      }
    }


    return msg;
}

UniquePtr<TypedProtobuf> LibprotobufMapping::ConvertIPCMessageToProtobuf(UniquePtr<IPC::Message> msg){

  MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto]: %s Size: %u\n",
                           IPC::StringFromIPCMessageType(msg->type()),
                           msg->header()->payload_size);

  UniquePtr<TypedProtobuf> output = MakeUnique<TypedProtobuf>();;

  switch (msg->type()){
    case dom::PContent::Msg_SetCharacterMap__ID: {
      // read parameter
      IPC::MessageReader reader__{
                        *(msg)};
      auto maybe__aGeneration = IPC::ReadParam<uint32_t>((&(reader__)));

      auto& aGeneration = *maybe__aGeneration;
      MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter Generation: %u\n",
                      aGeneration);

      // Sentinel = 'aGeneration'
      if ((!(((&(reader__)))->ReadSentinel(430179438)))) {
          mozilla::ipc::SentinelReadError("Error deserializing 'uint32_t'");
      }
      auto maybe__aFamilyIndex = IPC::ReadParam<uint32_t>((&(reader__)));

      auto& aFamilyIndex = *maybe__aFamilyIndex;
      MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter FamilyIndex: %u\n",
                      aFamilyIndex);

      // Sentinel = 'aFamilyIndex'
      if ((!(((&(reader__)))->ReadSentinel(501089468)))) {
          mozilla::ipc::SentinelReadError("Error deserializing 'uint32_t'");
      }
      auto maybe__aAlias = IPC::ReadParam<bool>((&(reader__)));

      auto& aAlias = *maybe__aAlias;
      MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter Alias: %u\n",
                      aAlias);
      // Sentinel = 'aAlias'
      if ((!(((&(reader__)))->ReadSentinel(129040972)))) {
          mozilla::ipc::SentinelReadError("Error deserializing 'bool'");
      }
      auto maybe__aFaceIndex = IPC::ReadParam<uint32_t>((&(reader__)));

      auto& aFaceIndex = *maybe__aFaceIndex;
      MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter FaceIndex: %u\n",
                      aFaceIndex);
      // Sentinel = 'aFaceIndex'
      if ((!(((&(reader__)))->ReadSentinel(335021001)))) {
          mozilla::ipc::SentinelReadError("Error deserializing 'uint32_t'");
      }



      size_t offset_before = reader__.iter_.iter_.AbsoluteOffset();
      MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter AbsoluteOffset: %lu\n",
                      offset_before);
      // copy iter state
      // Pickle::BufferList::IterImpl iter_before = reader__.iter_.iter_;
      // auto maybe__aMap = IPC::ReadParam<gfxSparseBitSet>((&(reader__)));
      // auto& aMap = *maybe__aMap;
      // size_t offset_after = reader__.iter_.iter_.AbsoluteOffset();
      // MOZ_FUZZING_NYX_PRINTF("INFO: [ConvertToProto] Read Parameter AbsoluteOffset After: %lu\n",
      //                 offset_after);
      // size_t serialized_size = offset_after - offset_before;

      // Vector<char, 256, InfallibleAllocPolicy> dumpBuffer;
      // if (!dumpBuffer.initLengthUninitialized(serialized_size)) {
      //   MOZ_FUZZING_NYX_ABORT("dumpBuffer.initLengthUninitialized failed\n");
      // }
      // if (!msg->Buffers().ReadBytes(
      //         iter_before,
      //         reinterpret_cast<char*>(dumpBuffer.begin()),
      //         serialized_size)) {
      //   MOZ_FUZZING_NYX_ABORT("ReadBytes failed\n");
      // }


      // Sentinel = 'aMap'
      if ((!(((&(reader__)))->ReadSentinel(60883328)))) {
          mozilla::ipc::SentinelReadError("Error deserializing 'gfxSparseBitSet'");
      }
      reader__.EndRead();



      // create protobuf
      SetCharacterMap proto;
      proto.set_ageneration(aGeneration);
      proto.set_afamilyindex(aFamilyIndex);
      proto.set_aalias(aAlias);
      proto.set_afaceindex(aFaceIndex);
      proto.set_gfxsparsebitset("test");

      MOZ_FUZZING_NYX_PRINT("INFO: [ConvertToProto] Proto created\n");

      output->type = dom::PContent::Msg_SetCharacterMap__ID;
      MOZ_FUZZING_NYX_PRINT("INFO: [ConvertToProto] Type set\n");
      output->serialized_data = proto.SerializeAsString();
      MOZ_FUZZING_NYX_PRINT("INFO: [ConvertToProto] Proto serialized\n");

      break;
    }
    case dom::PContent::Msg_ExtProtocolChannelConnectParent__ID:
    {
      // read parameter
      IPC::MessageReader reader__{
                        *(msg)};

      auto maybe__registrarId = IPC::ReadParam<uint64_t>((&(reader__)));
      if (!maybe__registrarId) {
          //FatalError("Error deserializing 'uint64_t'");
          //return MsgValueError;

      }
      auto& registrarId = *maybe__registrarId;
      // Sentinel = 'registrarId'
      if ((!(((&(reader__)))->ReadSentinel(464585857)))) {
          //mozilla::ipc::SentinelReadError("Error deserializing 'uint64_t'");
          //return MsgValueError;
      }
      reader__.EndRead();

      // create protobuf
      ExtProtocolChannelConnectParent proto;
      proto.set_registrarid(registrarId);

      output->type = dom::PContent::Msg_ExtProtocolChannelConnectParent__ID;
      output->serialized_data = proto.SerializeAsString();
      break;
    }
    default:
    {
      //
      break;
    }
  }

  return output;
}

}  // namespace fuzzing
}  // namespace mozilla
