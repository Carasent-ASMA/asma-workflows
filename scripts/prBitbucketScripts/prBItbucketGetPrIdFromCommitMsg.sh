#!/bin/bash

#LAST_COMMIT_MSG_RAW=$(git log -1 --pretty=%B)

echo -e "${BASH_LPURP}Finding BITBUCKET_PR_ID from last git commit msg. ${BASH_NC}"
function prBItbucketGetPrIdFromCommitMsg(){
    
    local COMMIT_MSG_PROCESSED=$(echo "$LAST_COMMIT_MESSAGE" | tr '\n' ' ')  
    local MATCH1="(pull request #"
    local MATCH2=")"
    local number_regex='^[0-9]+$'
    
    BITBUCKET_PR_ID=$(sed 's/'"$MATCH1"'/&\n/;s/.*\n//;s/'"$MATCH2"'/\n&/;s/\n.*//'  <<< "$COMMIT_MSG_PROCESSED")

    if ! [[ $BITBUCKET_PR_ID =~ $number_regex ]]; then
        BITBUCKET_PR_ID=
        exit 1
    fi
    
    echo "$BITBUCKET_PR_ID"
    exit 0
}

BITBUCKET_PR_ID=$(prBItbucketGetPrIdFromCommitMsg)
HAS_PR_ID=$?

exitOnGivenNumberOrOkMsg 1 $HAS_PR_ID "BITBUCKET_PR_ID: ${BASH_LPURP}$BITBUCKET_PR_ID${BASH_NC}" "${BASH_RED}"'BITBUCKET_PR_ID Not found in commit message!\nDirect commits to master are strongly discouraged! Please create a PR for that!\n'"${BASH_LPURP}LAST_COMMIT_MSG: ${BASH_CYAN}$LAST_COMMIT_MESSAGE${BASH_NC}"