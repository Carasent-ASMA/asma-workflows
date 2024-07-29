#!/bin/bash

export MULTIV_DEPLOYMENT_STRATEGY=true
export BASE_PATH_MULTIV_STRATEGY=/cdn
#export COMMIT_MSG=$(git log -1 --pretty=%B)
export LAST_COMMIT_MESSAGE=$(git log -1 --pretty=%B)
#LAST_VERSION=$(git describe --abbrev=0 --tags | sed 's/\(.*\)-\(.*\)-g\(.*\)/\1+\2.\3/' | sed 's/v\(.*\)/\1/')
export LAST_VERSION=$(git tag -l | grep -E 'v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | sed 's/^v//' | tail -n 1)


export LAST_COMMIT_TAG=$(git describe --tags --exact-match 2>/dev/null || true)
export LAST_COMMIT_VERSION=${LAST_COMMIT_TAG#v}



export BASH_RED='\033[0;31m'
export BASH_GREEN='\033[0;32m'
export BASH_YELLOW='\033[0;33m'
export BASH_BLUE='\033[0;34m'
export BASH_LPURP='\033[0;35m'
export BASH_CYAN='\033[0;36m'
export BASH_NC='\033[0m'
export ERROR_START="${BASH_RED}---------START ERROR---------${BASH_NC}"
export ERROR_END="${BASH_RED}----------END ERROR----------${BASH_NC}"
export WARN_START="${BASH_YELLOW}---------START ERROR---------${BASH_NC}"
export WARN_END="${BASH_YELLOW}----------END ERROR----------${BASH_NC}"
export OK_START="${BASH_GREEN}------START OK--------${BASH_NC}"
export OK_END="${BASH_GREEN}-------END OK---------${BASH_NC}"
export MESSAGE_START="${BASH_CYAN}------START MESSAGE--------${BASH_NC}"
export MESSAGE_END="${BASH_CYAN}-------END MESSAGE---------${BASH_NC}"

if [[ -n "$LAST_COMMIT_VERSION" ]]; then
    echo -e "${BASH_GREEN}current branch is taget with version: $LAST_COMMIT_VERSION, using it as increased version${BASH_NC}"
fi