#!/bin/bash
GREEN='\033[0;32m';
RED='\033[0;31m';
CYAN='\033[0;36m'
LPURP='\033[0;35m'
YELLOW='\033[0;33m'
NC='\033[0m';
ERROR_START="${RED}---------ERROR START---------${NC}"
ERROR_END="${RED}----------ERROR END----------${NC}"
OK_START="${GREEN}------OK START--------${NC}"
OK_END="${GREEN}-------OK END---------${NC}"

BITBUCKET_USER="andrei_kachan_carasent"
BITBUCKET_REPO_OWNER="carasent"

#GREEN=${GREEN};
#RED=${RED};
#CYAN=\e[36m;
#MAGNETA=${LPURP};
#YELLOW=${YELLOW};
#NC=${NC};
echo -e "${GREEN}Start of script${NC}"
echo "{\"test\": \"test\"}" | jq --indent 4


serviceName=$(echo ${BITBUCKET_REPO_SLUG} | cut -d'/' -f2)
echo -e "${LPURP}Install jq for json prettify${NC}"
apt-get install -y jq
echo -e "{"test": "test"}" | jq --indent 4

#Build application
echo -e "${LPURP}install globally pnpm${NC}"
npm i -g pnpm

echo -e "${LPURP}run pnpm install${NC}"
pnpm install

# Run the changeset status command and capture its output
changesetStatusMsg=$(npx changeset status 2>&1)

# Check for the presence of NO package bumps for patch, minor, and major
echo "$changesetStatusMsg" | grep -qi "NO packages to be bumped at patch"
NO_PATCH=$?
echo "$changesetStatusMsg" | grep -qi "NO packages to be bumped at minor"
NO_MINOR=$?
echo "$changesetStatusMsg" | grep -qi "NO packages to be bumped at major"
NO_MAJOR=$?
echo "$changesetStatusMsg" | grep -qi "error"
NO_CHANGESETS=$?

echo "NO_PATCH: $NO_PATCH"
echo "NO_MINOR: $NO_MINOR"
echo "NO_MAJOR: $NO_MAJOR"
echo "NO_CHANGESETS: $NO_CHANGESETS"
# Check the captured exit codes
if [[ $NO_CHANGESETS -eq 0 ]]; then
    echo -e "$ERROR_START"
    echo -e "${RED}$changesetStatusMsg${NC}"
    echo -e "$ERROR_END"
    exit 1
fi

if [[ $NO_PATCH -eq 0 && $NO_MINOR -eq 0 && $NO_MAJOR -eq 0 ]]; then
    echo -e "$ERROR_START"
    echo -e "${RED}$changesetStatusMsg${NC}"
    echo -e "$ERROR_END"
    exit 1
else
    echo -e "$OK_START"
    echo -e "${GREEN}$changesetStatusMsg${NC}"
    echo -e "$OK_END"
fi

echo -e "${LPURP}create new folder ${YELLOW}generated${NC}"
mkdir generated

echo -e "${LPURP}copy config/env.ts to ${YELLOW}generated ${LPURP}folder${NC}"
cp configs/env.ts generated/__ENV.ts

git config --global user.email "commits-noreply@bitbucket.org"
git config --global user.name "bitbucket-pipelines"
git checkout master

echo -e "${LPURP}run npx changeset version${NC}"
changesetVersionMsg=$(npx changeset version 2>&1)
# Print the full response to the console
if echo "$changesetVersionMsg" | grep -qi "warn No unreleased"; then
    echo -e  "$ERROR_START"
    echo -e "${RED}$changesetVersionMsg${NC}"
    echo -e  "$ERROR_END"
    exit 1
  else
    echo -e "$OK_START"
    echo -e "${GREEN}$changesetVersionMsg${NC}"
    echo -e "$OK_END"
fi
echo -e "${LPURP}get version from package.json${NC}"
VERSION=$(cat package.json \
  | grep version \
  | head -1 \
  | awk -F: '{ print $2 }' \
  | sed 's/[",]//g' \
  | sed 's/^ *//g')

git add -A

echo -e "${LPURP}create commit${NC}"
gitCommitMsg=$(git commit -am "ci(changeset): Bump version to ${VERSION} [skip ci]")
# Print the full response to the console
echo -e "${GREEN}$gitCommitMsg${NC}"

echo -e "${LPURP}push commit to repo${NC}"
gitPushBucket=$(git push https://$BITBUCKET_USER:$BITBUCKET_APP_PASSWORD@bitbucket.org/$BITBUCKET_REPO_OWNER/$BITBUCKET_REPO_SLUG.git master 2>&1)

# Print the full response to the console
if echo "$gitPushBucket" | grep -qi "denied"; then
    echo -e  "$ERROR_START"
    echo -e "${RED}$gitPushBucket${NC}"
    echo -e  "$ERROR_END"
    exit 1
  else
    echo -e "$OK_START"
    echo -e "${GREEN}$gitPushBucket${NC}"
    echo -e "$OK_END"
fi

echo -e "${LPURP}run npx changeset tag${NC}"
npx changeset tag

echo -e "${LPURP}push tags to repo${NC}"
gitPushTags=$(git push --follow-tags 2>&1)

# Print the full response to the console
if echo "$gitPushTags" | grep -qi "rejected"; then
    echo -e  "$ERROR_START"
    echo -e "${RED}$gitPushTags${NC}"
    echo -e  "$ERROR_END"
    exit 1
  else
    echo -e "$OK_START"
    echo -e "${GREEN}$gitPushTags${NC}"
    echo -e "$OK_END"
fi

echo -e "${LPURP}run npm run build${NC}"
npm run build

echo -e "${LPURP}copy configs/env.ts to dist/assets/__ENV-*.js${NC}"
cp configs/env.ts dist/assets/__ENV-*.js

echo -e "${LPURP}Update hasura dev${NC}"
#Update hasura dev
hasuraResponseDev=$(curl -X POST -H 'content-type: application/json' -H "x-hasura-admin-secret: ${hasuraSecretKeyDev}" --data "{\"query\": \"mutation { insert_and_clean_new_app_version (args:{new_service_name:\\\"${serviceName}\\\",new_version:\\\"${VERSION}\\\"}){updated_at}}\"}" https://dev.adopus.no/api/directory/v1/graphql)
# Print the full response to the console
echo -e "${LPURP}Response from Hasura Dev:${NC}"
#echo "---------------${NC}"
#echo "\e[36m$hasuraResponseDev${NC}"
#echo "---------------${NC}"
# Check if the response contains the word "error"


hasuraResponseDevFormat=$(echo "$hasuraResponseDev" | jq --indent 4)

if echo "$hasuraResponseDev" | grep -qi "error"; then
    echo -e  "$ERROR_START"
    #echo -e "$hasuraResponseDevFormat"
    echo "$hasuraResponseDev" | jq --indent 4
    echo -e  "$ERROR_END"
    exit 1
  else
    echo -e "$OK_START"
   #echo -e "${GREEN}$hasuraResponseDevFormat${NC}"
    echo "$hasuraResponseDev" | jq --indent 4
   echo -e "$OK_END"

fi

echo -e "${LPURP}Update hasura stage${NC}"
#Update hasura stage
hasuraResponseStage=$(curl -X POST -H 'content-type: application/json' -H "x-hasura-admin-secret: ${hasuraSecretKeyStage}" --data "{\"query\": \"mutation { insert_and_clean_new_app_version (args:{new_service_name:\\\"${serviceName}\\\",new_version:\\\"${VERSION}\\\"}){updated_at}}\"}" https://stage.adopus.no/api/directory/v1/graphql)
# Print the full response to the console
echo -e "${LPURP}Response from Hasura Stage:${NC}"
#echo "---------------${NC}"
#echo "$hasuraResponseStage"
#echo "---------------${NC}"
# Check if the response contains the word "error"
if echo "$hasuraResponseStage" | grep -qi "error"; then
    echo -e  "$ERROR_START"
    #echo -e "$hasuraResponseStageFormat"
    echo "$hasuraResponseStage" | jq --indent 4
    echo -e  "$ERROR_END"
    # commented temporarily till we update directory stage to latest verison
    #exit 1
  else
    echo -e "$OK_START"
    #echo -e "${GREEN}$hasuraResponseStageFormat${NC}"
    echo "$hasuraResponseStage" | jq --indent 4
    echo -e "$OK_END"
fi

echo -e "${LPURP}Update hasura prod${NC}"
#Update hasura prod
hasuraResponseProd=$(curl -X POST -H 'content-type: application/json' -H "x-hasura-admin-secret: ${hasuraSecretKeyProd}" --data "{\"query\": \"mutation { insert_and_clean_new_app_version (args:{new_service_name:\\\"${serviceName}\\\",new_version:\\\"${VERSION}\\\"}){updated_at}}\"}" https://www.adopus.no/api/directory/v1/graphql)
# Print the full response to the console
echo -e "${LPURP}Response from Hasura Prod:${NC}"
#echo "---------------${NC}"
#echo "$hasuraResponseProd${NC}"
#echo "---------------${NC}"
# Check if the response contains the word "error"
if echo "$hasuraResponseProd" | grep -qi "error"; then
    echo -e  "$ERROR_START"
    echo "$hasuraResponseProd" | jq --indent 4
    echo -e  "$ERROR_END"
    #commented temporarily till we update directory prod to latest verison
    #exit 1
  else
    echo -e "$OK_START"
    #echo -e "${GREEN}$hasuraResponseProd${NC}"
    echo "$hasuraResponseProd" | jq --indent 4
    echo -e "$OK_END"
fi

checkFolderExist=$(aws --endpoint-url=https://s3.fjit.no s3 ls s3://asma-app-cdn/${serviceName}/ | grep -w "${VERSION}")
checkFolderExistStatus=$?

#Upload to S3
echo -e "${LPURP}if else Block Upload to S3${NC}"

if [[ $checkFolderExistStatus -eq 1 ]]; then
#if echo aws --endpoint-url=https://s3.fjit.no s3 ls s3://asma-app-cdn/${serviceName}/ | grep -w "${VERSION}"; then
    #Upload to S3
    echo -e "\e[36mUpload to S3 when version does not exist from before${NC}"
    aws --endpoint-url=https://s3.fjit.no s3 cp ./dist s3://asma-app-cdn/${serviceName}/${VERSION}/ --recursive
else
    #Delete version
    echo -e "\e[36mDelete from S3 when version already exist${NC}"
    aws --endpoint-url=https://s3.fjit.no s3 rm s3://asma-app-cdn/${serviceName}/${VERSION} --recursive
    #Upload to S3
    echo -e "\e[36mUpload to S3 same version after clean${NC}"
    aws --endpoint-url=https://s3.fjit.no s3 cp ./dist s3://asma-app-cdn/${serviceName}/${VERSION}/ --recursive
fi
