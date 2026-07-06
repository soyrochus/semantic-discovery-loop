#!/bin/sh

rm -rf /opt/homebrew/opt/tomcat@9/libexec/webapps/taskdesk-legacy
cp target/taskdesk-legacy.war /opt/homebrew/opt/tomcat@9/libexec/webapps/