docker run \
    --rm -it \
    --gpus all \
    -v $(pwd):/home/$(id -un)/simnet \
    -w /home/$(id -un)/simnet \
    $(id -un)/simnet-dev
