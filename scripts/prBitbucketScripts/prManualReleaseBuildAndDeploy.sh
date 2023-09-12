#!/bin/bash
export MULTIV_DEPLOYMENT_STRATEGY=true
export hasuraSecretKeyDev=oUf822vk7z3oYPCpc  
export serviceName=$(npm run packageName --silent) 


source $(dirname "$0")/prBitbucketRelease.sh
