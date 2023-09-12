#!/bin/bash
git fetch origin master:master

printMsg "BITBUCKET_PR_ID: ${BASH_YELLOW}$BITBUCKET_PR_ID"

# Run the changeset status command and capture its output
changesetStatusMsg=$(npx changeset status 2>&1)

# Check for the presence of NO package bumps for patch, minor, and major
echo "$changesetStatusMsg" | grep -qi "NO packages to be bumped at patch"
NO_PATCH=$?
echo "$changesetStatusMsg" | grep -qi "NO packages to be bumped at minor"
NO_MINOR=$?
echo "$changesetStatusMsg" | grep -qi "NO packages to be bumped at major"
NO_MAJOR=$?
echo "$changesetStatusMsg" | grep -qi "error"
NO_CHANGESETS=$?

echo -e "${BASH_YELLOW}NO_PATCH: ${BASH_GREEN}$NO_PATCH${BASH_NC}"
echo -e "${BASH_YELLOW}NO_MINOR: ${BASH_GREEN}$NO_MINOR${BASH_NC}"
echo -e "${BASH_YELLOW}NO_MAJOR: ${BASH_GREEN}$NO_MAJOR${BASH_NC}"
echo -e "${BASH_YELLOW}NO_SUM: ${BASH_GREEN}$(($NO_PATCH + $NO_MINOR + $NO_MAJOR))${BASH_NC}"
echo -e "${BASH_YELLOW}NO_CHANGESETS: ${BASH_GREEN}$NO_CHANGESETS${BASH_NC}"

# Exit if there are no changesets
exitOnGivenNumber 0 $NO_CHANGESETS "$changesetStatusMsg"

# Exit if there are no changesets
exitIfZeroOrOkMsg $(($NO_PATCH + $NO_MINOR + $NO_MAJOR)) "$changesetStatusMsg"



