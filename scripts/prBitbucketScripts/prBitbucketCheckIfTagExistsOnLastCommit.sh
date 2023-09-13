#!/bin/bash

LAST_COMMIT_SHA=$(git rev-parse HEAD)
LAST_COMMIT_TAG=$(git describe --tags --exact-match $LAST_COMMIT_SHA 2>&1)

#echo "$LAST_COMMIT_TAG" | grep -qi "fatal"
ERROR_ON_LAST_COMMIT_TAG=$(stringContainsSubstring "$LAST_COMMIT_TAG" "fatal")

echo "ERROR_ON_LAST_COMMIT_TAG: $ERROR_ON_LAST_COMMIT_TAG"

if [[ $ERROR_ON_LAST_COMMIT_TAG -eq 1 ]]; then
        errorMsg "$LAST_COMMIT_TAG"
        exit 1
    else
        okMsg "tag to last commit is set! LAST_COMMIT_TAG: ${BASH_GREEN}$LAST_COMMIT_TAG${BASH_NC}"
fi

#exitOnGivenNumber 1 $ERROR_ON_LAST_COMMIT_TAG "tag to last commit is set! LAST_COMMIT_TAG: ${BASH_GREEN}$LAST_COMMIT_TAG${BASH_NC}" 