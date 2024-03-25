#!/bin/bash

export MULTIV_DEPLOYMENT_STRATEGY=true
export BASE_PATH_MULTIV_STRATEGY=https://cdn.advoca.no
#export COMMIT_MSG=$(git log -1 --pretty=%B)
LAST_COMMIT_MESSAGE=$(git log -1 --pretty=%B)
#LAST_VERSION=$(git describe --abbrev=0 --tags | sed 's/\(.*\)-\(.*\)-g\(.*\)/\1+\2.\3/' | sed 's/v\(.*\)/\1/')
LAST_VERSION=$(git tag -l | grep -E 'v[0-9]+\.[0-9][0-9]+\.[0-9]+$' | sort -V | sed 's/^v//' | tail -n 1)

BASH_RED='\033[0;31m'
BASH_GREEN='\033[0;32m'
BASH_YELLOW='\033[0;33m'
BASH_BLUE='\033[0;34m'
BASH_LPURP='\033[0;35m'
BASH_CYAN='\033[0;36m'
BASH_NC='\033[0m'
ERROR_START="${BASH_RED}---------START ERROR---------${BASH_NC}"
ERROR_END="${BASH_RED}----------END ERROR----------${BASH_NC}"
WARN_START="${BASH_YELLOW}---------START ERROR---------${BASH_NC}"
WARN_END="${BASH_YELLOW}----------END ERROR----------${BASH_NC}"
OK_START="${BASH_GREEN}------START OK--------${BASH_NC}"
OK_END="${BASH_GREEN}-------END OK---------${BASH_NC}"
MESSAGE_START="${BASH_CYAN}------START MESSAGE--------${BASH_NC}"
MESSAGE_END="${BASH_CYAN}-------END MESSAGE---------${BASH_NC}"