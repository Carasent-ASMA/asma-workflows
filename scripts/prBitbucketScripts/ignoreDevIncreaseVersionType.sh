#!/bin/bash

source $(dirname "$0")/variables.sh
source $(dirname "$0")/helperFns.sh

source $(dirname "$0")/prBitbucketCheckIfTagExistsOnLastCommit.sh
source $(dirname "$0")/prBitbucketfindVersionTypeOrExitIfCommitMsgWrong.sh
source $(dirname "$0")/prBitbucketVersionIncrease.sh