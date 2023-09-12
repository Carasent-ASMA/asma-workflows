#!/bin/bash
#set -e
serviceName="asma-scripts"

source $(dirname "$0")/scripts/prBitbucketScripts/variables.sh

source $(dirname "$0")/scripts/prBitbucketScripts/helperFns.sh

source $(dirname "$0")/scripts/prBitbucketScripts/prBitbucketFindVersionTypeOrExitIfCommitMsgWrong.sh

source $(dirname "$0")/scripts/prBitbucketScripts/prBitbucketVersionIncrease.sh

deleteFromS3AsmaAppCdn "$VERSION"

publishToS3Bucket "scripts"

source "$(dirname "$0")/scripts/prBitbucketScripts/prBitbucketTagCommitAndPush.sh"
