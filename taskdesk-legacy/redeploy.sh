#!/bin/sh
# Copy the built WAR into Tomcat 9's webapps directory (macOS and Linux).
# Build first with: mvn clean package

set -e
cd "$(dirname "$0")"
. ./paths.sh

if [ ! -d "$TOMCAT_HOME/webapps" ]; then
    echo "error: TOMCAT_HOME/webapps not found at: $TOMCAT_HOME/webapps" >&2
    echo "Set TOMCAT_HOME to your Tomcat 9 install before running." >&2
    exit 1
fi

rm -rf "$TOMCAT_HOME/webapps/taskdesk-legacy"
cp target/taskdesk-legacy.war "$TOMCAT_HOME/webapps/"
echo "Deployed target/taskdesk-legacy.war -> $TOMCAT_HOME/webapps/"
