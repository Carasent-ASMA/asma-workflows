#!/bin/bash
set -e


source $(dirname "$0")/variables.sh

source $(dirname "$0")/helperFns.sh

source $(dirname "$0")/curlHasuraInsertsFns.sh

source $(dirname "$0")/prBitbucketCheckIfTagExistsOnLastCommit.sh


source $(dirname "$0")/prBItbucketGetPrIdFromCommitMsg.sh

#source $(dirname "$0")/prBitbucketChangesetStatus.sh

#source $(dirname "$0")/prBitbucketChangeset.sh

#VERSION=$(npm run version --silent)
source $(dirname "$0")/prBitbucketFindVersionTypeOrExitIfCommitMsgWrong.sh

source $(dirname "$0")/prBitbucketVersionIncrease.sh

#LAST_COMMIT_MSG=$(git log -1 --pretty=%B)
serviceName=$(jq -r ".name" package.json)    

source $(dirname "$0")/prBitbucketBuildSendToS3AndHasura.sh

source $(dirname "$0")/prBitbucketGitUtilities.sh

source $(dirname "$0")/prBitbucketTagCommitAndPush.sh