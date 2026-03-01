#!/bin/bash

function findVersionType(){

    local MAJOR_REGEX='(feat|fix|docs|style|refactor|hotfix|chore|revert|ci)(\([^)]*\))?!:'

    local MINOR_REGEX='(feat)(\([^)]*\))?:'

    local PATCH_REGEX='(fix|docs|style|refactor|hotfix|chore|revert|ci)(\([^)]*\))?:|^Merged |^Merge'

    if [[ $LAST_COMMIT_MESSAGE =~ $MAJOR_REGEX ]]; then
        echo "major"
    elif [[ $LAST_COMMIT_MESSAGE =~ $MINOR_REGEX ]]; then
        echo "minor"
    elif [[ $LAST_COMMIT_MESSAGE =~ $PATCH_REGEX ]]; then
        echo "patch"
    else
        echo "error"
    fi
}

increaseVersionType=$(findVersionType)

COMMIT_MSG_PRINT=$([[ -z $LAST_COMMIT_MESSAGE ]] && echo "empty" || echo "$LAST_COMMIT_MESSAGE" )

if echo "$increaseVersionType" | grep -qi "error"; then
    errorMsg "${BASH_RED}could not determine increaseVersionType from commit message: "'\n'"${BASH_CYAN}~~$COMMIT_MSG_PRINT~~"'\n'"${BASH_RED}Please check if your commit message follow convetion!${BASH_NC}"
    exit 1
else
    okMsg "increaseVersionType: ${BASH_GREEN}$increaseVersionType${BASH_NC}"
fi
