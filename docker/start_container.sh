#!/bin/bash

SCRIPT_DIR=$(realpath $(dirname $0))

cd $SCRIPT_DIR
docker run \
    --rm -it \
    --gpus all \
    -v $(realpath $SCRIPT_DIR/..):/home/$(id -un)/simnet \
    -w /home/$(id -un)/simnet \
    $(id -un)/simnet-dev
cd - > /dev/null
