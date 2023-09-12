#!/bin/bash

source $(dirname "$0")/variables.sh

source $(dirname "$0")/helperFns.sh

source $(dirname "$0")/prBitbucketfindVersionTypeOrExitIfCommitMsgWrong.sh

#source $(dirname "$0")/prBitbucketPersistPrVersion.sh

VERSION="pr$BITBUCKET_PR_ID"


source $(dirname "$0")/prBitbucketBuildSendToS3AndHasura.sh