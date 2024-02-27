#!/bin/bash

function curlDirectoryMutation(){
    EXIT_IF_ERROR=${1}
    ENVIRONMENT=${2}
    ADMIN_SECRET_KEY=${3}
    OPERATION_DATA=${4}
    local HEADERS=${5:-}

    OPERATION=${OPERATION_DATA%% *}

    ENVIRONMENT_UPPERCASE=$(echo $ENVIRONMENT | tr '[:lower:]' '[:upper:]')
    OPERATION_UPPERCASE=$(echo $OPERATION | tr '[:lower:]' '[:upper:]')

    echo -e "${BASH_LPURP}-----${BASH_BLUE}START${BASH_LPURP} HASURA::$ENVIRONMENT_UPPERCASE: ${OPERATION_UPPERCASE}-----${BASH_NC}"

    #Update hasura dev
    #res=$(curlInsertAndCleanNewAppVersion "$hasuraSecretKeydev" "dev")
    echo -e "${BASH_LPURP}Aditional Headers: $HEADERS:${BASH_NC}"
    res=$(curl -X POST -H 'content-type: application/json' -H "x-hasura-admin-secret: ${ADMIN_SECRET_KEY}" ${HEADERS} --data "{\"query\": \"mutation {$OPERATION_DATA}\"}" https://${ENVIRONMENT}.adopus.no/api/directory/v1/graphql)

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
    VERSION_TO_DELETE=${1}
    OPERATION_DATA="delete_app_version (args:{existing_service_name:\\\"${serviceName}\\\",version_to_delete:\\\"${VERSION_TO_DELETE}\\\",is_s3_deleted:true}){updated_at}"
    
    echo -e "${BASH_YELLOW} delete versions from srv-directory as well. VERSION_TO_DELETE: ${BASH_RED}${VERSION_TO_DELETE}${BASH_NC}"

    if [[ -z "$VERSION_TO_DELETE" ]];then
        echo -e "${BASH_YELLOW}VERSION_TO_DELETE is empty exiting${BASH_NC}" 
        
        exit 1
     else
         echo -e "${BASH_LPURP}VERSION_TO_DELETE from s3: ${BASH_YELLOW}$VERSION_TO_DELETE${BASH_NC}"
    fi

    #delete version from hasura dev
    curlDirectoryMutation 1 "dev" "$hasuraSecretKeyDev" "$OPERATION_DATA"

    #delete version from stage
    curlDirectoryMutation 0 "stage" "$hasuraSecretKeyStage" "$OPERATION_DATA"

    #delete version from prod
    curlDirectoryMutation 0 "www" "$hasuraSecretKeyProd" "$OPERATION_DATA"
}

function curlDirectoryInsertAndCleanNewAppVersion(){

    LAST_COMMIT_MESSAGE=$(echo -n "${LAST_COMMIT_MESSAGE}" | jq -Rs @json | sed 's/^"//' | sed 's/"$//' )
    
    OPERATION_DATA="insert_and_clean_new_app_version (args:{new_service_name:\\\"${serviceName}\\\",new_version:\\\"${VERSION}\\\",new_pr_id:\\\"pr${BITBUCKET_PR_ID}\\\",new_commit_message:${LAST_COMMIT_MESSAGE}}){updated_at}"


    #insert version into hasura dev
    curlDirectoryMutation 1 "dev" "$hasuraSecretKeyDev" "$OPERATION_DATA"
    
    #execute operation if VERSION has following format: `numbers.numbers.numbers`
    if [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        #attach new app_versions to journals
        curlUpdateCustomerUserAppVersionInDev
    fi

    #insert version into hasura stage
    curlDirectoryMutation 0 "stage" "$hasuraSecretKeyStage" "$OPERATION_DATA"

    #insert version into hasura prod
    curlDirectoryMutation 0 "www" "$hasuraSecretKeyProd" "$OPERATION_DATA"
}

function curlUpdateCustomerUserAppVersionInDev(){
    echo -e "${BASH_LPURP}curlUpdateCustomerUserAppVersionInDev: set new customer_user_app_version for journals: [ADCURIS ADOPUS UNKNOWN] ${BASH_NC}"

    HEADERS="-H \"x-hasura-user-id: 00000000-0000-0000-0000-000000000000\""
    
    JOURNALS="UNKNOWN ADOPUS ADCURIS"
    
    for JOURNAL in $JOURNALS; do
        
        OPERATION_DATA="upsert_customer_user_app_version(args:{new_service:\\\"${serviceName}\\\",new_version:\\\"${VERSION}\\\",new_journal:\\\"${JOURNAL}\\\"}){updated_at}"
        
        curlDirectoryMutation 1 "dev" "$hasuraSecretKeyDev" "$OPERATION_DATA" "$HEADERS"
    done
}