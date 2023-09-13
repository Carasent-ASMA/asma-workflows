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

TS_V=$(tsc -v)
echo -e "${BASH_LPURP}typescript v: ${BASH_YELLOW}$TS_V${BASH_NC}"
echo -e "${BASH_LPURP}run pnpm run build${BASH_NC}"
pnpm run build



echo -e "${BASH_LPURP}copy configs/env.ts to dist/assets/__ENV-*.js${BASH_NC}"
cp configs/env.ts dist/assets/__ENV-*.js

curlDirectoryInsertAndCleanNewAppVersion

#Upload to S3
echo -e "${BASH_LPURP}Upload to S3, replace old build with new if version already exists${BASH_NC}"

deleteFromS3AsmaAppCdn "$VERSION"

    #Upload to S3
publishToS3Bucket


