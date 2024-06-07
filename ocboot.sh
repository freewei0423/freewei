#!/bin/bash

buildah --version || {
    echo "buildah is not installed, or not in PATH, please make sure buildah executable"
    echo "Try:"
    echo "  yum install -y buildah"
	echo "or:"
	echo "  apt-get install -y buildah"
    exit -1
}

set -e

REGISTRY=${REGISTRY:-registry.cn-beijing.aliyuncs.com/yunionio}
VERSION=${VERSION:-v4-k3s.4}
OCBOOT_IMAGE="$REGISTRY/ocboot:$VERSION"

CUR_DIR="$(pwd)"
CONTAINER_NAME="buildah-ocboot"

buildah_from_image() {
    if buildah ps | grep $CONTAINER_NAME; then
        buildah rm $CONTAINER_NAME
    fi
    local img="$1"
    echo "Using buildah pull $img"
    buildah from --name $CONTAINER_NAME "$img"
}

buildah_from_image "$OCBOOT_IMAGE"

mkdir -p "$HOME/.ssh"

CMD="ocboot.py"

buildah run -t \
    --net=host \
    -v "$HOME/.ssh:/root/.ssh" \
    -v "$(pwd):/ocboot" \
    -v "$(pwd)/airgap_assets/k3s-install.sh:/airgap_assets/k3s-install.sh:ro" \
    "$CONTAINER_NAME" $CMD $@
