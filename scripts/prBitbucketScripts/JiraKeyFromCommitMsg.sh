COMMIT_MESSAGE=$(git log -1 --pretty=%B)

export JIRA_KEY=$(echo "$COMMIT_MESSAGE" | grep -oP '(?<=^|[-/ ])ASMA-\d+(?=[-/ ]|$)' | head -1)

MATCHES=$(echo "$COMMIT_MESSAGE" | grep -oP '(?<=^|[-/ ])ASMA-\d+(?=[-/ ]|$)')

MATCH_COUNT=$(echo "$MATCHES" | wc -l)

if [[ $MATCH_COUNT -gt 1 ]]; then
    echo -e "${BASH_YELLOW}Warning: Multiple JIRA keys found, using first: $(echo "$MATCHES" | head -1)${BASH_NC}"
fi

if [[ -z "$JIRA_KEY" ]]; then
    echo -e "${BASH_RED}Error: JIRA_KEY could not be determined from commit message: $COMMIT_MESSAGE${BASH_NC}"
    echo -e "${BASH_RED}Commit message must contain JIRA key in format: ASMA-{numbers} (preceded by -, /, space, or start; followed by -, space, or end)${BASH_NC}"
    #exit 1
else
    echo -e "${BASH_GREEN}JIRA_KEY determined from commit message: $JIRA_KEY${BASH_NC}"
fi