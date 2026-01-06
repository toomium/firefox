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
  static std::string ReadPayloadFromMessage(mozilla::UniquePtr<IPC::Message>& msg);
  static mozilla::UniquePtr<IPC::Message> CreateMessageFromPayload(const std::string& payload);
  template<typename T>
  static IPC::ReadResult<std::string> ReadSerializedParam(IPC::MessageReader* reader);
  template<typename T>
  static mozilla::Maybe<T> DeserializeFromString(std::string& payload);
  template<typename T>
  static std::string SerializeToString(T* param);
  template<typename T>
  static UniquePtr<T> ParseTypedProtobuf(UniquePtr<TypedProtobuf> proto);
  template<typename T>
  static UniquePtr<TypedProtobuf> SerializeTypedProtobuf(UniquePtr<T> proto, IPC::IPCMessages type);
};

}  // namespace fuzzing
}  // namespace mozilla

#endif
