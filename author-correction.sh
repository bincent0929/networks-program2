git filter-branch -f --env-filter '
if [ "$GIT_AUTHOR_NAME" = "Vincent Roberson" ]; then
    export GIT_AUTHOR_NAME="Vincent Roberson"
    export GIT_AUTHOR_EMAIL="ghub@varmail.org"
fi
' -- --all