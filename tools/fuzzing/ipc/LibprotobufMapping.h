/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef mozilla_ipc_LibprotobufMapping_h
#define mozilla_ipc_LibprotobufMapping_h

#include "mozilla/ipc/MessageLink.h"

#include "nsThreadUtils.h"

#include "chrome/common/ipc_message.h"
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
  static LibprotobufMapping& instance();
  // Used for protobuf-based fuzzing
  UniquePtr<IPC::Message> ConvertProtobufToIPCMessage(UniquePtr<TypedProtobuf> protobuf);
  UniquePtr<TypedProtobuf> ConvertIPCMessageToProtobuf(UniquePtr<IPC::Message> msg);
};

}  // namespace fuzzing
}  // namespace mozilla

#endif
