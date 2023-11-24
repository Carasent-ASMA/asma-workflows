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

function increaseVersion() {
  local version=$1
  local increaseVersionType=$2

  local major=$(echo $version | cut -d. -f1)
  local minor=$(echo $version | cut -d. -f2)
  local patch=$(echo $version | cut -d. -f3)

  if [ "$increaseVersionType" == "major" ]; then
    major=$(increasePartitionOrSetToZero "$major")
    minor=0
    patch=0
  elif [ "$increaseVersionType" == "minor" ]; then
    minor=$(increasePartitionOrSetToZero "$minor")
    patch=0
  elif [ "$increaseVersionType" == "patch" ]; then
    patch=$(increasePartitionOrSetToZero "$patch")
  fi

  ((major))||major=0
  ((minor))||minor=0
  ((patch))||patch=0

  echo "$major.$minor.$patch"
}

#LAST_VERSION=$(git describe --abbrev=0 --tags | sed 's/\(.*\)-\(.*\)-g\(.*\)/\1+\2.\3/' | sed 's/v\(.*\)/\1/' )
printMsg "Last version: $LAST_VERSION"

export VERSION=$(increaseVersion "$LAST_VERSION" "$increaseVersionType")
    
TAG_MSG=$(git rev-list "v$VERSION" 2>&1)
    
    if echo "$TAG_MSG" | grep -qi "fatal"; then
        okMsg " OK tag does not exist.. continue TAG_MSG: $TAG_MSG"
    else
        errorMsg "tag already exists! recalculating .. TAG: v$VERSION"
        
        export VERSION=$(increaseVersion "$VERSION" "$increaseVersionType")
        
        TAG_MSG=$(git rev-list "v$VERSION" 2>&1)
        
            if echo "$TAG_MSG" | grep -qi "fatal"; then
                okMsg " OK tag does not exist.. continue TAG_MSG: $TAG_MSG"
            else
                errorMsg "tag already exists! Please fix manually! exitig.. TAG: v$VERSION"
    fi

printMsg "New version: $VERSION"
