#!/bin/bash

export MULTIV_DEPLOYMENT_STRATEGY=true
export hasuraSecretKeyDev=oUf822vk7z3oYPCpc  
export BITBUCKET_PR_ID=164

source $(dirname "$0")/prBitbucketPrerelease.sh


