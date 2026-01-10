COMMIT_MESSAGE=$(git log -1 --pretty=%B)

# Extract only the first line (PR merges can have multiple commit messages)
FIRST_LINE=$(echo "$COMMIT_MESSAGE" | head -1)

IGNORE_JIRA_KEY_IF_EMPTY=false
if [[ "$FIRST_LINE" == *"—skip-jira-key"* ]]; then
    IGNORE_JIRA_KEY_IF_EMPTY=true
    echo -e "${BASH_RED}╔════════════════════════════════════════════════════════════════════╗${BASH_NC}"
    echo -e "${BASH_RED}║                        ⚠️  WARNING  ⚠️                              ║${BASH_NC}"
    echo -e "${BASH_RED}║                                                                    ║${BASH_NC}"
    echo -e "${BASH_RED}║  The —skip-jira-key flag is ACTIVE!                    ║${BASH_NC}"
    echo -e "${BASH_RED}║                                                                    ║${BASH_NC}"
    echo -e "${BASH_RED}║  This flag should be used CAREFULLY and ONLY with permission       ║${BASH_NC}"
    echo -e "${BASH_RED}║  from team leaders.                                                ║${BASH_NC}"
    echo -e "${BASH_RED}║                                                                    ║${BASH_NC}"
    echo -e "${BASH_RED}║  Proceeding without JIRA key may skip important tracking.          ║${BASH_NC}"
    echo -e "${BASH_RED}╚════════════════════════════════════════════════════════════════════╝${BASH_NC}"
fi

# Portable regex (no -P), non-fatal
MATCHES=$(echo "$COMMIT_MESSAGE" | grep -oE '(^|[ /-])ASMA-[0-9]+([ /-]|$)' || true)

# Normalize matches (strip separators)
MATCHES=$(echo "$MATCHES" | sed 's|^[ /-]||;s|[ /-]$||')

JIRA_KEY=$(echo "$MATCHES" | head -1)
MATCH_COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')

if [[ $MATCH_COUNT -gt 1 ]]; then
    echo -e "${BASH_YELLOW}Warning: Multiple JIRA keys found, using first: $JIRA_KEY${BASH_NC}"
fi

if [[ -z "$JIRA_KEY" ]]; then
    echo -e "${BASH_RED}Error: JIRA_KEY could not be determined from commit message:${BASH_NC}"
    echo "$COMMIT_MESSAGE"

    if [[ "$IGNORE_JIRA_KEY_IF_EMPTY" == true ]]; then
        echo -e "${BASH_YELLOW}Continuing without JIRA key due to override flag${BASH_NC}"
    else
        echo -e "${BASH_BLUE}╔════════════════════════════════════════════════════════════════════╗${BASH_NC}"
        echo -e "${BASH_BLUE}║                        ⚠️  WARNING  ⚠️                              ║${BASH_NC}"
        echo -e "${BASH_BLUE}║                                                                    ║${BASH_NC}"
        echo -e "${BASH_BLUE}║  You can add —skip-jira-key to your commit message to proceed.     ║${BASH_NC}"
        echo -e "${BASH_BLUE}║                                                                    ║${BASH_NC}"
        echo -e "${BASH_BLUE}║  However, this flag should be used CAREFULLY and ONLY with         ║${BASH_NC}"
        echo -e "${BASH_BLUE}║  permission from team leaders.                                     ║${BASH_NC}"
        echo -e "${BASH_BLUE}║                                                                    ║${BASH_NC}"
        echo -e "${BASH_BLUE}║  Proceeding without JIRA key may skip important tracking.          ║${BASH_NC}"
        echo -e "${BASH_BLUE}╚════════════════════════════════════════════════════════════════════╝${BASH_NC}"
        exit 1
    fi
else
    echo -e "${BASH_GREEN}JIRA_KEY determined from commit message: $JIRA_KEY${BASH_NC}"
fi

export JIRA_KEY
