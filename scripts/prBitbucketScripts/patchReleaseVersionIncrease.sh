#!/bin/bash

function increasePartitionOrSetToZero(){
  local number=${1}
  if [ -z "$number" ];then
      number=0
    else
      number=$((number + 1))
    fi
  echo "$number"
}

increasePatchVersion() {
    local LAST_VERSION=$1
    local IFS='-' # set delimiter
    read -ra ADDR <<< "$LAST_VERSION" # split LAST_VERSION into array ADDR
    local lastNumber=0 # set lastNumber to 0 by default
    if [[ -n "${ADDR[1]}" && "${ADDR[1]}" =~ ^[0-9]+$ ]]; then
        lastNumber=${ADDR[1]} # set lastNumber to ADDR[1] if ADDR[1] is set and is a number
    fi
    let "lastNumber++" # increment the last number
    echo "${ADDR[0]}-$lastNumber" # construct the new version
}

#LAST_VERSION=$(git describe --abbrev=0 --tags | sed 's/\(.*\)-\(.*\)-g\(.*\)/\1+\2.\3/' | sed 's/v\(.*\)/\1/' )

if [ -n "$LAST_COMMIT_VERSION" ]; then
    export VERSION="$LAST_COMMIT_VERSION"
else
    printMsg "Last version: $LAST_VERSION"
    export VERSION=$(increasePatchVersion "$LAST_VERSION")
fi
    
TAG_MSG=$(git rev-list "v$VERSION" 2>&1)
    
    if echo "$TAG_MSG" | grep -qi "fatal"; then
        okMsg " OK tag does not exist.. continue TAG_MSG: $TAG_MSG"
    else
        errorMsg "tag already exists! exiting.. TAG: v$VERSION"
        exit 1
    fi

printMsg "patch version: $VERSION"
