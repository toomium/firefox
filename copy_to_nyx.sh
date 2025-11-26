#!/bin/bash

rm -r ~/orion-tom/services/nyx/sharedir/firefox

cp -r obj-x86_64-pc-linux-gnu/dist/firefox/ ~/orion-tom/services/nyx/sharedir

echo "SourceStamp=9f59b559a71685a5078a92af991a211b88988c19" >> ~/orion-tom/services/nyx/sharedir/firefox/platform.ini
