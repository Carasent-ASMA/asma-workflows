if  [[ -n "$VERSION" && -z "$LAST_COMMIT_VERSION" ]]; then
    
    git tag "v$VERSION"
    resGitTagPush=$(git push --tags 2>&1)
    
    #echo "$resGitTagPush" | grep -qi "rejected"
    REJECTED=$(stringContainsSubstring "$resGitTagPush" "rejected")
    
    errorOnGivenNumberOrOkMsg 0 $REJECTED "$resGitTagPush"
    else
    
    errorMsg "VERSION is empty!"
fi