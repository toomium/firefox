#!/bin/bash

rm -r ./orion-tom-non-proto/services/nyx/sharedir/firefox

cp -r obj-x86_64-pc-linux-gnu/dist/firefox/ ../orion-tom-non-proto/services/nyx/sharedir

echo "SourceStamp=9f59b559a71685a5078a92af991a211b88988c19" >> ../orion-tom-non-proto/services/nyx/sharedir/firefox/platform.ini

cat > ./orion-tom-non-proto/services/nyx/sharedir/firefox/firefox.fuzzmanagerconf << 'EOF'
[Main]
platform = x86-64
product = mozilla-central
product_version = 20250930-24347d6b356b
os = linux

[Metadata]
pathprefix = /builds/worker/checkouts/gecko
buildtype = ccov-fuzzing-asan-nyx-opt
EOF