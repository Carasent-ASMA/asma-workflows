#!/bin/bash

#LAST_COMMIT_SHA=$(git rev-parse HEAD)
#LAST_COMMIT_VERSION=$(git describe --tags --exact-match $LAST_COMMIT_SHA 2>/dev/null)
#
##echo "$LAST_COMMIT_VERSION" | grep -qi "fatal"
#ERROR_ON_LAST_COMMIT_TAG=$(stringContainsSubstring "$LAST_COMMIT_VERSION" "fatal")
#
#echo "ERROR_ON_LAST_COMMIT_TAG: $ERROR_ON_LAST_COMMIT_TAG"

#if [[ -n $LAST_COMMIT_VERSION ]]; then
 #       warnMsg "commit is already set on current commit! LAST_COMMIT_VERSION: $LAST_COMMIT_VERSION!"

        #git tag -d $LAST_COMMIT_VERSION
        #git push --delete origin $LAST_COMMIT_VERSION

        #printMsg "set LAST_VERSION to LAST_COMMIT_VERSION: $LAST_COMMIT_VERSION!"

        #LAST_VERSION=$LAST_COMMIT_VERSION
        #$(git describe --abbrev=0 --tags | sed 's/\(.*\)-\(.*\)-g\(.*\)/\1+\2.\3/' | sed 's/v\(.*\)/\1/')
 #   else
  #      okMsg "${BASH_LPURP}current commit clean! ${BASH_GREEN} LAST_COMMIT_VERSION is empty! continue {BASH_NC}"
#fi

#exitOnGivenNumber 1 $ERROR_ON_LAST_COMMIT_TAG "tag to last commit is set! LAST_COMMIT_VERSION: ${BASH_GREEN}$LAST_COMMIT_TAG${BASH_NC}" 