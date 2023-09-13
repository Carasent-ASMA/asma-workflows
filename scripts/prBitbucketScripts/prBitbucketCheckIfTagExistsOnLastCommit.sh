#!/bin/bash

LAST_COMMIT_SHA=$(git rev-parse HEAD)
LAST_COMMIT_TAG=$(git describe --tags --exact-match $LAST_COMMIT_SHA 2>&1)

#echo "$LAST_COMMIT_TAG" | grep -qi "fatal"
ERROR_ON_LAST_COMMIT_TAG=$(stringContainsSubstring "$LAST_COMMIT_TAG" "fatal")

echo "ERROR_ON_LAST_COMMIT_TAG: $ERROR_ON_LAST_COMMIT_TAG"

if [[ $ERROR_ON_LAST_COMMIT_TAG -eq 1 ]]; then
        warnMsg "commit is already set on current commit! LAST_COMMIT_TAG: $LAST_COMMIT_TAG, ${BASH_RED}removing and continue!"

        git tag -d $LAST_COMMIT_TAG
        git push --delete origin $LAST_COMMIT_TAG

        printMsg "reassigning LAST_VERSION after removing tag!"
        LAST_VERSION=$(git describe --abbrev=0 --tags | sed 's/\(.*\)-\(.*\)-g\(.*\)/\1+\2.\3/' | sed 's/v\(.*\)/\1/')
    else
        okMsg "${BASH_LPURP}current commit clean! ${BASH_GREEN}$LAST_COMMIT_TAG{BASH_NC}"
fi

#exitOnGivenNumber 1 $ERROR_ON_LAST_COMMIT_TAG "tag to last commit is set! LAST_COMMIT_TAG: ${BASH_GREEN}$LAST_COMMIT_TAG${BASH_NC}" 