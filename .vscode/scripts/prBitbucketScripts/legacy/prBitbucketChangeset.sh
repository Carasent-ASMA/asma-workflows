#!/bin/bash

echo -e "${BASH_LPURP}run npx changeset version${BASH_NC}"
changesetVersionMsg=$(npx changeset version 2>&1)
# Print the full response to the console

echo "$changesetVersionMsg" | grep -qi "warn No unreleased"
NO_UNRELEASED=$?
exitIfZeroOrOkMsg $NO_UNRELEASED "$changesetVersionMsg"




echo -e "${BASH_LPURP}run npx changeset tag${BASH_NC}"
changesetTag=$(npx changeset tag)

echo "$changesetTag" | grep -qi "already exists"
ALREADY_EXISTS=$?
exitIfZeroOrOkMsg $ALREADY_EXISTS "$changesetTag"
newAppVersion=$(npm run version --silent)

git add -A

echo -e "${BASH_LPURP}create commit${BASH_NC}"
gitCommitMsg=$(git commit -am"ci: Clean changesets files & update package.json for version :$newAppVersion [skip ci]" 2>&1)
# Print the full response to the console
printMsg "$gitCommitMsg"

#git push

echo -e "${BASH_LPURP}create and push tags to repo${BASH_NC}"
gitPushTags=$(git push --follow-tags 2>&1)

echo "$gitPushTags" | grep -qi "rejected"
REJECTED=$?
exitIfZeroOrOkMsg $REJECTED "$gitPushTags"



