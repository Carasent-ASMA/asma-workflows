COMMIT_MESSAGE=$(git log -1 --pretty=%B)

# Extract only the first line for checking (PR merges can have multiple commit messages)
FIRST_LINE=$(echo "$COMMIT_MESSAGE" | head -1)

# Check for --ignore-jira-key-if-empty flag in first line only
IGNORE_JIRA_KEY_IF_EMPTY=false
if [[ "$FIRST_LINE" == *"--ignore-jira-key-if-empty"* ]]; then
    IGNORE_JIRA_KEY_IF_EMPTY=true
    echo -e "${BASH_RED}╔════════════════════════════════════════════════════════════════════╗${BASH_NC}"
    echo -e "${BASH_RED}║                        ⚠️  WARNING  ⚠️                              ║${BASH_NC}"
    echo -e "${BASH_RED}║                                                                    ║${BASH_NC}"
    echo -e "${BASH_RED}║  The --ignore-jira-key-if-empty flag is ACTIVE!                    ║${BASH_NC}"
    echo -e "${BASH_RED}║                                                                    ║${BASH_NC}"
    echo -e "${BASH_RED}║  This flag should be used CAREFULLY and ONLY with permission       ║${BASH_NC}"
    echo -e "${BASH_RED}║  from team leaders.                                                ║${BASH_NC}"
    echo -e "${BASH_RED}║                                                                    ║${BASH_NC}"
    echo -e "${BASH_RED}║  Proceeding without JIRA key may skip important tracking.          ║${BASH_NC}"
    echo -e "${BASH_RED}╚════════════════════════════════════════════════════════════════════╝${BASH_NC}"
fi

export JIRA_KEY=$(echo "$COMMIT_MESSAGE" | grep -oP '(?<=^|[-/ ])ASMA-\d+(?=[-/ ]|$)' | head -1)

MATCHES=$(echo "$COMMIT_MESSAGE" | grep -oP '(?<=^|[-/ ])ASMA-\d+(?=[-/ ]|$)')

MATCH_COUNT=$(echo "$MATCHES" | wc -l)

if [[ $MATCH_COUNT -gt 1 ]]; then
    echo -e "${BASH_YELLOW}Warning: Multiple JIRA keys found in latest commit message, using first: $(echo "$MATCHES" | head -1)${BASH_NC}"
fi

if [[ -z "$JIRA_KEY" ]]; then
    echo -e "${BASH_RED}Error: JIRA_KEY could not be determined from commit message: $COMMIT_MESSAGE${BASH_NC}"
    echo -e "${BASH_RED}Commit message must contain JIRA key in format: ASMA-{numbers} (preceded by -, /, space, or start; followed by -, space, or end)${BASH_NC}"
    
    if [[ "$IGNORE_JIRA_KEY_IF_EMPTY" == true ]]; then
        echo -e "${BASH_YELLOW}Continuing without JIRA key due to --ignore-jira-key-if-empty flag in commit message${BASH_NC}"
    else
        echo -e "${BASH_BLUE}Add --ignore-jira-key-if-empty to commit message to proceed without JIRA key (requires leader permission)${BASH_NC}"
        exit 1
    fi
else
    echo -e "${BASH_GREEN}JIRA_KEY determined from commit message: $JIRA_KEY${BASH_NC}"
fi