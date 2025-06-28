#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(realpath $(dirname $0))

cd $SCRIPT_DIR
docker build \
    --build-arg USER_NAME=$(id -un) \
    --build-arg USER_ID=$(id -u) \
    --build-arg GROUP_NAME=$(id -gn) \
    --build-arg GROUP_ID=$(id -g) \
    -t $(id -un)/simnet-dev \
    .
cd -