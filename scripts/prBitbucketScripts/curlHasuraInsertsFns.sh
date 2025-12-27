#!/bin/bash

function curlDirectoryMutation(){
    local EXIT_IF_ERROR=${1}
    local ENVIRONMENT=${2}
    local ADMIN_SECRET_KEY=${3}
    local OPERATION_DATA=${4}
    #local HEADERS=${5:-}

    local OPERATION=${OPERATION_DATA%% *}

    local ENVIRONMENT_UPPERCASE=$(echo $ENVIRONMENT | tr '[:lower:]' '[:upper:]')
    local OPERATION_UPPERCASE=$(echo $OPERATION | tr '[:lower:]' '[:upper:]')

    echo -e "${BASH_LPURP}-----${BASH_BLUE}START${BASH_LPURP} HASURA::$ENVIRONMENT_UPPERCASE: ${OPERATION_UPPERCASE}-----${BASH_NC}"

    #Update hasura dev
    #res=$(curlInsertAndCleanNewAppVersion "$hasuraSecretKeydev" "dev")
    #echo -e "${BASH_LPURP}Aditional Headers: ${HEADERS} ${BASH_NC}"
    res=$(curl -X POST -H 'content-type: application/json' -H "x-hasura-admin-secret: ${ADMIN_SECRET_KEY}" -H "x-hasura-user-id: 00000000-0000-0000-0000-000000000000" -H "x-hasura-journal-user-name: BitbucketScripts" --data "{\"query\": \"mutation {$OPERATION_DATA}\"}" https://${ENVIRONMENT}.adopus.no/api/directory/v1/graphql)

    # Print the full response to the console
    echo -e "${BASH_LPURP}Response from Hasura $ENVIRONMENT:${BASH_NC}"

    #echo "$res" | grep -qi "error"
    ERROR=$(stringContainsSubstring "$res" "error")
    
    RES_JSON=$(echo "$res" | jq --indent 4)
    
    if [[ $EXIT_IF_ERROR -eq 1 ]]; then
            exitOnGivenNumberOrOkMsg 0 $ERROR "$RES_JSON"
        else
            errorOnGivenNumberOrOkMsg 0 $ERROR "$RES_JSON"
    fi
    echo -e "${BASH_LPURP}-----${BASH_BLUE}END${BASH_LPURP} HASURA::$ENVIRONMENT_UPPERCASE: ${OPERATION_UPPERCASE}-----${BASH_NC}"
}

function curlDirectoryDeleteAppVersion(){
    local VERSION_TO_DELETE=${1}
    local NEW_VERSION=${2}
    local OPERATION_DATA="delete_app_version (args:{existing_service_name:\\\"${serviceName}\\\",version_to_delete:\\\"${VERSION_TO_DELETE}\\\",is_s3_deleted:true,new_version:\\\"${NEW_VERSION}\\\"}){updated_at}"
    
    echo -e "${BASH_YELLOW} delete versions from srv-directory as well. VERSION_TO_DELETE: ${BASH_RED}${VERSION_TO_DELETE}${BASH_NC}"

    if [[ -z "$VERSION_TO_DELETE" ]];then
        echo -e "${BASH_YELLOW}VERSION_TO_DELETE is empty exiting${BASH_NC}" 
        
        exit 1
     else
         echo -e "${BASH_LPURP}VERSION_TO_DELETE from s3: ${BASH_YELLOW}$VERSION_TO_DELETE${BASH_NC}"
    fi

    #delete version from hasura dev
    curlDirectoryMutation 1 "web.dev" "$hasuraSecretKeyDev" "$OPERATION_DATA"

    #delete version from stage
    curlDirectoryMutation 1 "web.stage" "$hasuraSecretKeyStage" "$OPERATION_DATA"

    #delete version from prod
    curlDirectoryMutation 1 "web" "$hasuraSecretKeyProd" "$OPERATION_DATA"
}

function curlDirectoryInsertAndCleanNewAppVersion(){

    local LAST_COMMIT_MESSAGE=$(echo -n "${LAST_COMMIT_MESSAGE}" | jq -Rs @json | sed 's/^"//' | sed 's/"$//' )

    # Set JIRA_ISSUE_ID to null if JIRA_KEY is empty, otherwise wrap in quotes
    local JIRA_ISSUE_ID
    
    if [[ -z "$JIRA_KEY" ]]; then
        echo -e "${BASH_YELLOW}WARNING: JIRA_KEY is not set, jira_issue_id will be set to null${BASH_NC}"
        JIRA_ISSUE_ID="null"
    else
        JIRA_ISSUE_ID="\\\"${JIRA_KEY}\\\""
    fi
    
    local OPERATION_DATA="revman_insert_and_clean_new_app_version (args:{new_service_name:\\\"${serviceName}\\\",new_version:\\\"${VERSION}\\\",new_pr_id:\\\"pr${BITBUCKET_PR_ID}\\\",new_commit_message:${LAST_COMMIT_MESSAGE},jira_issue_id:${JIRA_ISSUE_ID}}){updated_at}"


    #insert version into hasura dev
    curlDirectoryMutation 1 "web.dev" "$hasuraSecretKeyDev" "$OPERATION_DATA"
    
    #execute operation if VERSION has following format: `numbers.numbers.numbers`
    if [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        
        #attach new app_versions to journals
        curlUpdateCustomerUserAppVersionInDev
    fi

    #insert version into hasura stage
    curlDirectoryMutation 1 "web.stage" "$hasuraSecretKeyStage" "$OPERATION_DATA"

    #insert version into hasura prod
    curlDirectoryMutation 1 "web" "$hasuraSecretKeyProd" "$OPERATION_DATA"
}

function curlUpdateCustomerUserAppVersionInDev(){
    echo -e "${BASH_LPURP}curlUpdateCustomerUserAppVersionInDev: set new customer_user_app_version for journals: [ADCURIS ADOPUS UNKNOWN] ${BASH_NC}"

    #HEADERS="-H \"x-hasura-user-id: 00000000-0000-0000-0000-000000000000\""

    local JOURNALS="UNKNOWN ADOPUS ADCURIS"
    
    for JOURNAL in $JOURNALS; do
        
        local CUAV_OPERATION_DATA="revman_upsert_customer_user_app_version(args:{new_service:\\\"${serviceName}\\\",new_version:\\\"${VERSION}\\\",new_journal:\\\"${JOURNAL}\\\"}){updated_at}"
        
        curlDirectoryMutation 1 "web.dev" "$hasuraSecretKeyDev" "$CUAV_OPERATION_DATA" #"$HEADERS"
    done
}

export -f curlDirectoryMutation
export -f curlDirectoryDeleteAppVersion
export -f curlDirectoryInsertAndCleanNewAppVersion
export -f curlUpdateCustomerUserAppVersionInDev