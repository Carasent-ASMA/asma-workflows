#!/bin/bash

function okMsg(){
    echo -e "$OK_START"
    echo -e "$1"
    echo -e "$OK_END"
}
function printMsg(){
    echo -e "$MESSAGE_START"
    echo -e "$1"
    echo -e "$MESSAGE_END"
}

function errorMsg(){
    echo -e "$ERROR_START"
    echo -e "$1"
    echo -e "$ERROR_END"
}

function exitOnGivenNumber(){
    local CODE=${1}
    local EXEC_CODE=${2}
    local MSG=${3}
    if [ $EXEC_CODE -eq $CODE ]; then
        errorMsg "$MSG"
        exit 1
    fi
}

function exitOnGivenNumberOrOkMsg(){
    local CODE=${1}
    local EXEC_CODE=${2}
    local SUCCESS_MSG=${3}
    local ERROR_MSG=${4:-$SUCCESS_MSG}
    exitOnGivenNumber $CODE $EXEC_CODE "$ERROR_MSG"
    okMsg "$SUCCESS_MSG"
}

function errorOnGivenNumberOrOkMsg(){
    local CODE=${1}
    local EXEC_CODE=${2}
    local SUCCESS_MSG=${3}
    local ERROR_MSG=${4:-$SUCCESS_MSG}

    if [ $EXEC_CODE -eq $CODE ]; then
            errorMsg "$ERROR_MSG"
        else
            okMsg "$SUCCESS_MSG"
    fi
}

function exitIfZeroOrOkMsg(){
    local EXEC_CODE=${1}
    local SUCCESS_MSG=${2}
    local ERROR_MSG=${3:-$SUCCESS_MSG}
    exitOnGivenNumberOrOkMsg 0 $EXEC_CODE "$SUCCESS_MSG" "$ERROR_MSG"
}

function deleteFromS3AsmaAppCdn(){
    VERSION_TO_DELETE=${1}
    #LIST_OF_FOLDERS=$(aws --endpoint-url=https://s3.fjit.no s3 ls s3://asma-app-cdn/${serviceName}/ | grep -w "${VERSION_TO_DELETE}")
    #checkFolderExistStatus=$(stringContainsSubstring "$LIST_OF_FOLDERS" "${VERSION_TO_DELETE}" "w" )

    #Delete version
    if aws --endpoint-url=https://s3.fjit.no s3 ls s3://asma-app-cdn/${serviceName}/ | grep -w "${VERSION_TO_DELETE}"; then
            echo -e "${BASH_LPURP}service: ${BASH_YELLOW}$serviceName${BASH_LPURP} with version: ${BASH_YELLOW}$VERSION_TO_DELETE ${BASH_LPURP}exsists in s3 bucket asma-app-cdn , deleting${BASH_NC}"
            aws --endpoint-url=https://s3.fjit.no s3 rm s3://asma-app-cdn/${serviceName}/${VERSION_TO_DELETE} --recursive
        else
            echo -e "${BASH_LPURP}service: ${BASH_YELLOW}$serviceName${BASH_LPURP} with version: ${BASH_YELLOW}$VERSION_TO_DELETE ${BASH_LPURP}does not exist from before, skip deletion ${BASH_NC}"
    fi
}
function publishToS3Bucket(){
    FOLDER_TO_UPLOAD=${1:-"dist"}
    echo -e "${BASH_LPURP}Upload to S3 ${BASH_NC}"
    aws --endpoint-url=https://s3.fjit.no s3 cp ./${FOLDER_TO_UPLOAD} s3://asma-app-cdn/${serviceName}/${VERSION}/ --recursive
}
function stringContainsSubstring(){
    local STRING=${1}
    local SUBSTRING=${2}
    if echo "$increaseVersionType" | grep -qi "$SUBSTRING"; then
        echo 0
    else
        echo 1
    fi
}
