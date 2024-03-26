#!/bin/bash
set -ex

source $(dirname "$0")/variables.sh
echo "variables.sh"
source $(dirname "$0")/helperFns.sh
echo "helperFns.sh"
source $(dirname "$0")/curlHasuraInsertsFns.sh
echo "curlHasuraInsertsFns.sh"
source $(dirname "$0")/prBitbucketFindVersionTypeOrExitIfCommitMsgWrong.sh
echo "prBitbucketFindVersionTypeOrExitIfCommitMsgWrong.sh"
#source $(dirname "$0")/prBitbucketPersistPrVersion.sh

export VERSION="pr$BITBUCKET_PR_ID"

serviceName=$(jq -r ".name" package.json)
echo "after serviceName var
source $(dirname "$0")/prBitbucketBuildSendToS3AndHasura.sh
echo "prBitbucketBuildSendToS3AndHasura.sh