/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef mozilla_ipc_LibprotobufMapping_h
#define mozilla_ipc_LibprotobufMapping_h

#include "mozilla/ipc/MessageLink.h"
#include "IPCMessageStart.h"

#include "nsThreadUtils.h"

#include "chrome/common/ipc_message.h"
#include "chrome/common/ipc_message_utils.h"
#include "mojo/core/ports/name.h"

#include "mozilla/dom/PContent.h"

#include <string>

namespace mozilla {
namespace fuzzing {

struct TypedProtobuf {
    uint32_t type;
    std::string serialized_data;
};

class LibprotobufMapping {
 public:
  // Used for protobuf-based fuzzing
  // static UniquePtr<IPC::Message> ConvertProtobufToIPCMessage(UniquePtr<TypedProtobuf>& protobuf);
  // static UniquePtr<TypedProtobuf> ConvertIPCMessageToProtobuf(UniquePtr<IPC::Message>& msg);
  static std::string ReadPayloadFromMessage(const IPC::Message& msg);
  static mozilla::UniquePtr<IPC::Message> CreateMessageFromPayload(const std::string& payload);
  static nsCString nsCString_ToIPC(const std::string& str);
  static std::string nsCString_ToProtobuf(const nsCString& str);
  static nsString nsString_ToIPC(const std::string& str);
  static std::string nsString_ToProtobuf(const nsString& str);
  // template<typename T>
  // static IPC::ReadResult<std::string> ReadSerializedParam(IPC::MessageReader* reader);
  // template<typename T>
  // static mozilla::Maybe<T> DeserializeFromString(std::string& payload);
  // template<typename T>
  // static std::string SerializeToString(T* param);
  // template<typename T>
  // static UniquePtr<T> ParseTypedProtobuf(UniquePtr<TypedProtobuf> proto);
  // template<typename T>
  // static UniquePtr<TypedProtobuf> SerializeTypedProtobuf(UniquePtr<T> proto, IPC::IPCMessages type);

  template<typename T>
  static UniquePtr<T> ParseProtobufMessage(const IPC::Message& msg) {
    UniquePtr<TypedProtobuf> typedProto = mozilla::MakeUnique<TypedProtobuf>();
    typedProto->type = msg.type();
    typedProto->serialized_data = LibprotobufMapping::ReadPayloadFromMessage(msg);
    return LibprotobufMapping::ParseTypedProtobuf<T>(typedProto);
  }

  template<typename T>
  static UniquePtr<T> ParseTypedProtobuf(UniquePtr<TypedProtobuf>& proto) {
      auto input = mozilla::MakeUnique<T>();
      if (input->ParseFromString(proto->serialized_data)) {
        if (!!getenv("MOZ_FUZZ_DEBUG")) {
          MOZ_FUZZING_NYX_PRINTF("DEBUG: Parsed protobuf object:\n%s\n", input->DebugString().c_str());
        }
        return input;
      }
      if (!!getenv("MOZ_FUZZ_DEBUG")) {
        MOZ_FUZZING_NYX_PRINT("ERROR: Protobuf parsing failed - returning empty pointer\n");
      }
      return {};
  }

  template<typename T>
  static UniquePtr<TypedProtobuf> SerializeTypedProtobuf(UniquePtr<T>& proto, IPC::IPCMessages type) {
      if (!proto) {
        if (!!getenv("MOZ_FUZZ_DEBUG")) {
          MOZ_FUZZING_NYX_PRINT("ERROR: Cannot serialize nullptr protobuf object\n");
        }
        return {};
      }
      UniquePtr<TypedProtobuf> output = mozilla::MakeUnique<TypedProtobuf>();
      output->serialized_data = proto->SerializeAsString();
      output->type = type;
      return output;
  }

  template<typename T>
  static IPC::ReadResult<std::string> ReadSerializedParam(IPC::MessageReader* reader) {

    // save position before reading
    size_t offset_before = reader->iter_.iter_.AbsoluteOffset();

    // copy iter state
    Pickle::BufferList::IterImpl iter_before = reader->iter_.iter_;

    // read parameter
    auto readResult = IPC::ReadParam<T>(reader);
    if (!readResult) {
      if (!!getenv("MOZ_FUZZ_DEBUG")) {
        MOZ_FUZZING_NYX_PRINT("ERROR: Reading serialized parameter failed due to empty read result\n");
      }
      return {};
    }

    // calculate serialized size
    size_t offset_after = reader->iter_.iter_.AbsoluteOffset();
    size_t serialized_size = offset_after - offset_before;

    std::string result;
    result.resize(serialized_size);

    if (!reader->message_.Buffers().ReadBytes(
            iter_before,
            result.data(), // write into string buffer
            serialized_size)) {
        if (!!getenv("MOZ_FUZZ_DEBUG")) {
          MOZ_FUZZING_NYX_PRINT("ERROR: ReadBytes failed to copy serialized data\n");
        }
        return {};
    }

    return {std::move(result)};
  }

  template<typename T>
static std::string SerializeToStringMove(T& param) { //TT* param
    //if (!param) return "";

    // create dummy
    mozilla::UniquePtr<IPC::Message> dummy_msg = mozilla::dom::PContent::Msg_SetCharacterMap(0);
    IPC::MessageWriter writer__{(*(dummy_msg))};

    IPC::WriteParam(&writer__, std::move(param)); //*param

    return LibprotobufMapping::ReadPayloadFromMessage(*dummy_msg);
}

  template<typename T>
static std::string SerializeToString(T& param) { //T* param
    //if (!param) return "";

    // create dummy
    mozilla::UniquePtr<IPC::Message> dummy_msg = mozilla::dom::PContent::Msg_SetCharacterMap(0);
    IPC::MessageWriter writer__{(*(dummy_msg))};

    // check for some moveonly types
    // if constexpr (std::is_same_v<T, mozilla::ipc::BigBuffer> ||
    //               std::is_same_v<T, mozilla::ipc::Shmem>) {
    //IPC::WriteParam(&writer__, *param);
    IPC::WriteParam(&writer__, param);

    return LibprotobufMapping::ReadPayloadFromMessage(*dummy_msg);
}

template<typename T>
  static mozilla::Maybe<T> DeserializeFromString(const std::string& payload) {
    // create dummy msg
    mozilla::UniquePtr<IPC::Message> dummy_msg = LibprotobufMapping::CreateMessageFromPayload(payload);

    // let ParamTraits deserialize the parameter
    IPC::MessageReader reader__{
                          *(dummy_msg)};

    // T result;
    // if (!IPC::ReadParam<T>(&reader__, &result)) {
    //   MOZ_FUZZING_NYX_ABORT("Deserialization from string failed\n");
    //   return mozilla::Nothing();
    // }
    auto result = IPC::ReadParam<T>(&reader__);
    if (!result) {
      if (!!getenv("MOZ_FUZZ_DEBUG")) {
        MOZ_FUZZING_NYX_PRINT("Deserialization from string failed\n");
      }
      return mozilla::Nothing();
    }

    return mozilla::Some(std::move(*result));
  }
};
}  // namespace fuzzing
}  // namespace mozilla

#endif
