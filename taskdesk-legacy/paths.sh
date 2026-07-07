#!/bin/sh
# Shared environment for building and deploying TaskDesk Legacy.
# Source this from the taskdesk-legacy directory (works for humans and AI agents):
#
#   . ./paths.sh
#
# Sets, without clobbering values you have already exported:
#   JAVA_HOME        (Linux only, if the tarball install at ~/opt/jdk17 exists)
#   PATH             (prepends JDK and Maven bin dirs when using ~/opt installs)
#   TOMCAT_HOME      Tomcat 9 install directory
#   TASKDESK_DB_URL  JDBC URL for the demo SQLite DB, derived from this repo's location

# Directory containing this script (POSIX sh has no BASH_SOURCE; fall back to $0).
_paths_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE:-$0}")" && pwd)

case "$(uname -s)" in
    Darwin)
        if [ -z "$TOMCAT_HOME" ] && command -v brew >/dev/null 2>&1; then
            TOMCAT_HOME="$(brew --prefix tomcat@9)/libexec"
        fi
        ;;
    Linux)
        if [ -z "$JAVA_HOME" ] && [ -d "$HOME/opt/jdk17" ]; then
            JAVA_HOME="$HOME/opt/jdk17"
            PATH="$JAVA_HOME/bin:$PATH"
            export JAVA_HOME
        fi
        if [ -d "$HOME/opt/maven/bin" ]; then
            PATH="$HOME/opt/maven/bin:$PATH"
        fi
        TOMCAT_HOME="${TOMCAT_HOME:-$HOME/opt/tomcat9}"
        ;;
esac

export PATH
export TOMCAT_HOME

# Demo DB lives at <repo-root>/db/runtime-data, one level above taskdesk-legacy.
_db_file=$(CDPATH= cd -- "$_paths_dir/.." && pwd)/db/runtime-data/taskdesk-demo.sqlite
export TASKDESK_DB_URL="${TASKDESK_DB_URL:-jdbc:sqlite:$_db_file}"

unset _paths_dir _db_file
