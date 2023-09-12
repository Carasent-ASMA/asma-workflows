#!/bin/bash
#set -e
serviceName="asma-scripts"

source $(dirname "$0")/scripts/prBitbucketScripts/setup.sh

publishToS3Bucket "scripts"

source "$(dirname "$0")/scripts/prBitbucketScripts/prBitbucketTagCommitAndPush.sh"
