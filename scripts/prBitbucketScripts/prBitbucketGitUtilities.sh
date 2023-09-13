#!/bin/bash
#Delete version
#Check if build is in release mode and delete the prerelease folder /pr${BITBUCKET_PR_ID}

VERSION_TO_DELETE="pr$BITBUCKET_PR_ID"

echo -e "${BASH_LPURP}VERSION_TO_DELETE: ${BASH_YELLOW}${VERSION_TO_DELETE}${BASH_NC}"

#Check if build is in release mode and delete the prerelease folder /pr${BITBUCKET_PR_ID}
echo -e "${BASH_LPURP}Check if pr is accepted and delete the VERSION_TO_DELETE(BITBUCKET_PR_ID): ${BASH_YELLOW}/pr${BITBUCKET_PR_ID}${BASH_NC}"

#echo "$VERSION"| grep -qi "pr"
IS_PR=$(stringContainsSubstring "$VERSION" "pr")

echo -e "${BASH_YELLOW}IS_PR: ${BASH_GREEN}$IS_PR${BASH_NC}"

if [[ $IS_PR -eq 1 ]]; then
    
    deleteFromS3AsmaAppCdn "$VERSION_TO_DELETE"
    
    
    curlDirectoryDeleteAppVersion "$VERSION_TO_DELETE"
else
    echo -e "${BASH_LPURP}Skip deletion for: ${BASH_GREEN}$VERSION_TO_DELETE${BASH_NC}"
fi
