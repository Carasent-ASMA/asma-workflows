#!/bin/bash

EXISTING_BITBUCKET_PR_ID=$(cat auto_gen_pr_id.txt)
FILE_EXISTS=$?
if [[ $FILE_EXISTS -eq 1 ]]; then
  EXISTING_BITBUCKET_PR_ID=0
fi

echo -e "${BASH_GREEN}EXISTING_BITBUCKET_PR_ID: ${BASH_YELLOW}${EXISTING_BITBUCKET_PR_ID}${BASH_NC}"
echo -e "${BASH_GREEN}BITBUCKET_PR_ID: ${BASH_YELLOW}${BITBUCKET_PR_ID}${BASH_NC}"
echo -e "${BASH_GREEN}ARE EQUAL: ${BASH_YELLOW}$(($EXISTING_BITBUCKET_PR_ID != $BITBUCKET_PR_ID))${BASH_NC}"

if [ "$EXISTING_BITBUCKET_PR_ID" != "$BITBUCKET_PR_ID" ]; then
    echo -e "${BASH_GREEN}Create auto_gen_pr_id.txt file with current pr number!${BASH_NC}"
    echo "$BITBUCKET_PR_ID" > auto_gen_pr_id.txt
    
    gitMsg=$(git add auto_gen_pr_id.txt && git commit -m "ci: Updated PR ID into auto_gen_pr_id.txt [skip ci]" && git push)
    
    printMsg "$gitMsg"
    #echo -e "$MESSAGE_START"
    #echo -e "${GREEN}$gitMsg${BASH_NC}"
    #echo -e "$MESSAGE_END"
else
    echo -e "${BASH_YELLOW}auto_gen_pr_id.txt file already exists! ${BASH_PURPLE}content: ${BASH_YELLOW}${EXISTING_BITBUCKET_PR_ID}${BASH_NC}"
    #rm auto_gen_pr_id.txt
   #
    #gitMsg=$( git add . && git commit -m "ci: remove auto_gen_pr_id.txt [skip ci]" && git push)
    #echo -e "$OK_START"
    #echo -e "${GREEN}$gitMsg${BASH_NC}"
    #echo -e "$OK_END"
fi