#!/bin/bash
set -e

source $(dirname "$0")/variables.sh

source $(dirname "$0")/helperFns.sh

source $(dirname "$0")/curlHasuraInsertsFns.sh

source $(dirname "$0")/prBitbucketFindVersionTypeOrExitIfCommitMsgWrong.sh

#source $(dirname "$0")/prBitbucketPersistPrVersion.sh

VERSION="pr$BITBUCKET_PR_ID"


source $(dirname "$0")/prBitbucketBuildSendToS3AndHasura.sh