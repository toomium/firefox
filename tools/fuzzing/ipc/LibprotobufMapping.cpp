/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#include "LibprotobufMapping.h"

#include "nsThreadUtils.h"

#include "mozilla/ipc/MessageLink.h"

#include "mozilla/dom/PContent.h"

#include <fstream>
#include <sstream>

#include "protobuf/test.pb.h"

using namespace mojo::core::ports;
using namespace mozilla::ipc;

namespace mozilla {
namespace fuzzing {

// static
LibprotobufMapping& LibprotobufMapping::instance() {
  static LibprotobufMapping lib;
  return lib;
}

UniquePtr<IPC::Message> LibprotobufMapping::ConvertProtobufToIPCMessage(const TypedProtobuf* protobuf) {

    // first deserialize protobuf
    ExtProtocolChannelConnectParent input;

    input.ParseFromString(protobuf->serialized_data);

    auto registrarId = input.registrarid();

    // then create new message
    UniquePtr<IPC::Message> msg = dom::PContent::Msg_ExtProtocolChannelConnectParent(MSG_ROUTING_CONTROL);
    IPC::MessageWriter writer__{
            (*(msg))};

    IPC::WriteParam((&(writer__)), registrarId);
    // Sentinel = 'registrarId'
    ((&(writer__)))->WriteSentinel(464585857);

    return msg;
}

TypedProtobuf LibprotobufMapping::ConvertIPCMessageToProtobuf(UniquePtr<IPC::Message> msg){

  TypedProtobuf output;

  switch (msg->type()){
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

      output.type = dom::PContent::Msg_ExtProtocolChannelConnectParent__ID;
      output.serialized_data = proto.SerializeAsString();
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
