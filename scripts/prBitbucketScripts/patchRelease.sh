#!/bin/bash
#set -e

source $(dirname "$0")/variables.sh

source $(dirname "$0")/helperFns.sh

# Get the current branch name
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

# Check if there are any differences between the current branch and the remote master branch
#if [ -z "$(git diff origin/master..$BRANCH_NAME)" ]; then
#    warnMsg "No differences with remote master branch. Skipping execution."
#    exit 0
#fi

# Check if the branch name matches the required format
if [[ $BRANCH_NAME =~ ^releases/v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    VERSION_FROM_BRANCH_NAME=${BRANCH_NAME#releases/}
else
    errorMsg "Error: Branch name does not match the required format (releases/v{number}.{number}.{number})"
    exit 1
fi

printMsg "Current branch: $BRANCH_NAME"
printMsg "VERSION_FROM_BRANCH_NAME: $VERSION_FROM_BRANCH_NAME"
# Get the last tag from the current branch

LAST_TAG=$(git tag -l | grep -E "^$VERSION_FROM_BRANCH_NAME-[0-9]+$" | sort -V | tail -n 1)

# If there's no tag on the current branch, get the version from the branch name
if [[ -z "$LAST_TAG" ]]; then
    LAST_TAG="$VERSION_FROM_BRANCH_NAME"
fi

# Remove the leading 'v' from the last tag
export LAST_VERSION=${LAST_TAG#v}

printMsg "LAST_TAG: $LAST_TAG"

printMsg "LAST_VERSION: $LAST_VERSION"

source $(dirname "$0")/curlHasuraInsertsFns.sh

source $(dirname "$0")/prBitbucketCheckIfTagExistsOnLastCommit.sh


#source $(dirname "$0")/prBItbucketGetPrIdFromCommitMsg.sh

#source $(dirname "$0")/prBitbucketChangesetStatus.sh

#source $(dirname "$0")/prBitbucketChangeset.sh

#VERSION=$(npm run version --silent)
#source $(dirname "$0")/prBitbucketFindVersionTypeOrExitIfCommitMsgWrong.sh

source $(dirname "$0")/patchReleaseVersionIncrease.sh

#LAST_COMMIT_MSG=$(git log -1 --pretty=%B)
serviceName=$(jq -r ".name" package.json)    

source $(dirname "$0")/prBitbucketBuildSendToS3AndHasura.sh

#source $(dirname "$0")/prBitbucketGitUtilities.sh

source $(dirname "$0")/prBitbucketTagCommitAndPush.sh