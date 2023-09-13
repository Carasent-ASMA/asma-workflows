#!/bin/bash

echo -e "${BASH_LPURP}create new folder ${BASH_YELLOW}generated${BASH_NC}"
mkdir generated

echo -e "${BASH_LPURP}copy config/env.ts to ${BASH_YELLOW}generated ${BASH_LPURP}folder${BASH_NC}"
cp configs/env.ts generated/__ENV.ts

echo -e "${LPURP}install globally pnpm${NC}"
npm i -g pnpm

echo -e "${LPURP}install globally typescript${NC}"
npm i -g "typescript@$TS_VERSION"

echo -e "${BASH_LPURP}run pnpm install${BASH_NC}"
pnpm install

#res=$("$resPnpmInstall" | grep -qi "error")
#ERROR_PNPM_INSTALL=$(stringContainsSubstring "$resPnpmInstall" "error")
#echo -e "${BASH_YELLOW}ERROR_PNPM_INSTALL: ${BASH_GREEN}$ERROR_PNPM_INSTALL${BASH_NC}"
#exitOnGivenNumberOrOkMsg 0 $ERROR_PNPM_INSTALL "$resPnpmInstall"
TS_V=tsc -v
echo -e "${BASH_LPURP}typescript v: ${BASH_YELLOW}$TS_V${BASH_NC}"
echo -e "${BASH_LPURP}run pnpm run build${BASH_NC}"
pnpm run build

#echo "$resNpmRunBuild" | grep -qi "error"
#if echo "$increaseVersionType" | grep -qi "error"; then
#   errorMsg "$resNpmRunBuild"
#   exit 1
#else
#    okMsg "$resNpmRunBuild"
#fi
#ERROR_NPM_RUN_BUILD=$(stringContainsSubstring "$resNpmRunBuild" "error")

#exitOnGivenNumberOrOkMsg 0 $ERROR_NPM_RUN_BUILD "$resNpmRunBuild"

echo -e "${BASH_LPURP}copy configs/env.ts to dist/assets/__ENV-*.js${BASH_NC}"
cp configs/env.ts dist/assets/__ENV-*.js

curlDirectoryInsertAndCleanNewAppVersion

#checkFolderExist=$(aws --endpoint-url=https://s3.fjit.no s3 ls s3://asma-app-cdn/${serviceName}/ | grep -w "${VERSION}")
#checkFolderExistStatus=$?

#Upload to S3
echo -e "${BASH_LPURP}Upload to S3, replace old build with new if version already exists${BASH_NC}"

deleteFromS3AsmaAppCdn "$VERSION"

    #Upload to S3
publishToS3Bucket
#echo -e "${BASH_LPURP}Upload to S3 ${BASH_NC}"
#aws --endpoint-url=https://s3.fjit.no s3 cp ./dist s3://asma-app-cdn/${serviceName}/${VERSION}/ --recursive

