if  [[ -n "$VERSION" && -z "$LAST_COMMIT_VERSION" ]]; then
    
    git tag "v$VERSION"
    resGitTagPush=$(git push --tags 2>&1)
    
    #echo "$resGitTagPush" | grep -qi "rejected"
    REJECTED=$(stringContainsSubstring "$resGitTagPush" "rejected")
    
    errorOnGivenNumberOrOkMsg 0 $REJECTED "$resGitTagPush"
    else
    
    warnMsg "VERSION is empty, or ! VERSION: $VERSION, LAST_COMMIT_VERSION: $LAST_COMMIT_VERSION"
fi