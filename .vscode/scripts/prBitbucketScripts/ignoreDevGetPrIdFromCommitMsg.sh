#!/bin/bash

source $(dirname "$0")/variables.sh

source $(dirname "$0")/helperFns.sh

hasuraSecretKeyDev=oUf822vk7z3oYPCpc

hasuraSecretKeyStage=rwxGVMk3DZTDtnqjC2oeDM

hasuraSecretKeyProd=P_gynTEejs-gKmxaVgk6UFq_

VERSION_TO_DELETE=$(npm run version --silent)

source $(dirname "$0")/prBItbucketGetPrIdFromCommitMsg.sh
