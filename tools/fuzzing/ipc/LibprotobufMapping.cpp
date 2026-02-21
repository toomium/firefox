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

nsCString LibprotobufMapping::nsCString_ToIPC(const std::string& str) {
    //nsCString res;
    //res.Assign(str.data(), str.length());
    //return res;
    return nsCString(str.data(), str.length());
}

std::string LibprotobufMapping::nsCString_ToProtobuf(const nsCString& str) {
    return std::string(str.get(), str.Length());
}

nsString LibprotobufMapping::nsString_ToIPC(const std::string& str) {
    //NS_ConvertUTF8toUTF16 converter(str.data(), str.length());
    //return nsString(converter);
    return nsString(reinterpret_cast<const char16_t*>(str.data()), str.length() / sizeof(char16_t));
}

std::string LibprotobufMapping::nsString_ToProtobuf(const nsString& str) {
    //NS_ConvertUTF16toUTF8 converter(str);
    //return std::string(converter.get(), converter.Length());
    return std::string(reinterpret_cast<const char*>(str.get()), str.Length() * sizeof(char16_t));
}

std::string LibprotobufMapping::ReadPayloadFromMessage(const IPC::Message& msg) {

    std::string ret;
    ret.resize(msg.header()->payload_size);

    Pickle::BufferList::IterImpl iter(msg.Buffers());
    if (! iter.AdvanceAcrossSegments(msg.Buffers(), sizeof(IPC::Message::Header))) {
        MOZ_FUZZING_NYX_PRINT("ReadPayloadFromMessage: Skipping header failed\n");
        return "";
    }


    // Vector<char, 256, InfallibleAllocPolicy> dumpBuffer;
    // if (!dumpBuffer.initLengthUninitialized(msg->Buffers().Size())) {
    //     MOZ_FUZZING_NYX_ABORT("dumpBuffer.initLengthUninitialized failed\n");
    // }

    // copy from buffer but skip header
    if (! msg.Buffers().ReadBytes(
            iter,
            ret.data(),
            msg.header()->payload_size)) {
        MOZ_FUZZING_NYX_PRINT("ReadPayloadFromMessage: ReadBytes failed\n");
        return "";
    }

    return ret;
    // return std::string(reinterpret_cast<char*>(dumpBuffer.begin() + sizeof(IPC::Message::Header)),
    //            dumpBuffer.length() - sizeof(IPC::Message::Header));
}

}  // namespace fuzzing
}  // namespace mozilla
