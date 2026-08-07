#!/bin/sh
# Truth pin: fail CI if stale product facts reappear in tracked files.
# POSIX sh, no dependencies beyond git grep.
set -eu
cd "$(dirname "$0")/.."

fail=0

# Tracked text files, minus changelog history entries and this script itself.
PATHS=". :(exclude)CHANGELOG.md :(exclude)scripts/truthcheck.sh"

forbid() {
    pattern="$1"
    msg="$2"
    # shellcheck disable=SC2086
    if git grep -I -n -i -E "$pattern" -- $PATHS >/dev/null 2>&1; then
        echo "FORBIDDEN ($msg):"
        # shellcheck disable=SC2086
        git grep -I -n -i -E "$pattern" -- $PATHS || true
        fail=1
    fi
}

require() {
    pattern="$1"
    msg="$2"
    # shellcheck disable=SC2086
    if ! git grep -I -q -E "$pattern" -- $PATHS; then
        echo "MISSING ($msg): pattern '$pattern' not found"
        fail=1
    fi
}

# Stale quota copy: the old 100k/day story, in either order on a line.
forbid '100[,.]?000([^0-9]|$).*(/day|per day|daily)|(/day|per day|daily).*100[,.]?000([^0-9]|$)|100k.*(/day|per day|daily)' \
    'day quota for FREE is 100, not 100,000/100k'
# Free tier paired with 1,000/day (that is BASIC).
forbid 'free.*1[,.]?000([^0-9]|$).*(/day|per day|daily)|free.*(/day|per day|daily).*1[,.]?000([^0-9]|$)' \
    'free tier is 100/day, not 1,000/day'
forbid 'livetennisapi\.com/docs' 'docs live at docs.livetennisapi.com'
forbid 'bensynapse' 'use the Live Tennis API org identity'
forbid 'midnight UTC' 'daily reset is a local-midnight-derived instant, not midnight UTC'

# Required facts — this repo states quotas.
require '100 requests/day|100/day' 'FREE daily quota stated as 100/day'
require 'docs\.livetennisapi\.com' 'canonical docs URL present'

if [ "$fail" -ne 0 ]; then
    echo "truthcheck: FAILED"
    exit 1
fi
echo "truthcheck: OK"
