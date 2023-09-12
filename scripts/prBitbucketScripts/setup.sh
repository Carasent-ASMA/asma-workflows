#!/bin/bash

#source "$(dirname "$0")
 source $(dirname "$0")/variables.sh

 source $(dirname "$0")/helperFns.sh

 source $(dirname "$0")/prBitbucketfindVersionTypeOrExitIfCommitMsgWrong.sh

 source $(dirname "$0")/prBitbucketVersionIncrease.sh



