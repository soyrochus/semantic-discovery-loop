# TaskDesk Legacy

TaskDesk Legacy is a simulated Struts 1.x / JSP / JDBC application packaged as a WAR. It uses SQLite for the local demo database and is intended to run on a legacy-compatible servlet container.

These instructions target macOS only.

## Prerequisites

Install Homebrew if needed, then install Maven and Tomcat 9:

```bash
brew install maven tomcat@9
```

Use Tomcat 9, not Tomcat 10. Struts 1.x and this application use the older `javax.servlet` APIs; Tomcat 10 moved to `jakarta.servlet`.

Check the tools:

```bash
mvn -version
$(brew --prefix tomcat@9)/libexec/bin/version.sh
```

## Database

The demo database already exists at the repository root:

```text
../db/runtime-data/taskdesk-demo.sqlite
```

The app reads the JDBC URL from:

```text
src/main/resources/taskdesk.properties
```

Current default:

```properties
taskdesk.db.url=jdbc:sqlite:/Users/ivanderk/src/semantic-discovery-loop/db/runtime-data/taskdesk-demo.sqlite
```

You can override this without rebuilding by setting either:

```bash
export TASKDESK_DB_URL=jdbc:sqlite:/absolute/path/to/taskdesk-demo.sqlite
```

or a JVM system property:

```bash
-Dtaskdesk.db.url=jdbc:sqlite:/absolute/path/to/taskdesk-demo.sqlite
```

Demo users:

```text
operator1 / demo
operator2 / demo
manager1  / demo
```

To inspect the database:

```bash
sqlite3 ../db/runtime-data/taskdesk-demo.sqlite \
  'select username, display_name, role from app_user order by user_id;'
```

## Build

From this directory:

```bash
mvn clean package
```

The WAR is created at:

```text
target/taskdesk-legacy.war
```

## Run On Tomcat 9

Find the Tomcat install:

```bash
export TOMCAT_HOME="$(brew --prefix tomcat@9)/libexec"
```

Stop Tomcat if it is already running:

```bash
brew services stop tomcat@9
```

Remove any previously exploded deployment and copy the new WAR:

```bash
rm -rf "$TOMCAT_HOME/webapps/taskdesk-legacy"
cp target/taskdesk-legacy.war "$TOMCAT_HOME/webapps/"
```

Start Tomcat:

```bash
brew services start tomcat@9
```

Open the app:

```text
http://localhost:8080/taskdesk-legacy/login.do
```

## Redeploy Script

This directory includes a macOS helper script:

```text
./redeploy-mac.sh
```

It removes the exploded `taskdesk-legacy` webapp from the Homebrew Tomcat 9 deployment directory and copies the built WAR into Tomcat.

Use it from this directory after building:

```bash
mvn clean package
./redeploy-mac.sh
brew services restart tomcat@9
```

The script assumes the Homebrew Tomcat 9 path:

```text
/opt/homebrew/opt/tomcat@9/libexec/webapps
```

## Running With A DB Override

If you do not want to use the packaged absolute path, run Tomcat with `TASKDESK_DB_URL`.

For a one-off foreground run:

```bash
export TOMCAT_HOME="$(brew --prefix tomcat@9)/libexec"
export TASKDESK_DB_URL="jdbc:sqlite:/Users/ivanderk/src/semantic-discovery-loop/db/runtime-data/taskdesk-demo.sqlite"
"$TOMCAT_HOME/bin/catalina.sh" run
```

For Homebrew service usage, set JVM options in Tomcat's environment configuration. A simple local option is to create or edit:

```text
$(brew --prefix tomcat@9)/libexec/bin/setenv.sh
```

Example:

```bash
cat > "$(brew --prefix tomcat@9)/libexec/bin/setenv.sh" <<'EOF'
export TASKDESK_DB_URL="jdbc:sqlite:/Users/ivanderk/src/semantic-discovery-loop/db/runtime-data/taskdesk-demo.sqlite"
EOF
chmod +x "$(brew --prefix tomcat@9)/libexec/bin/setenv.sh"
brew services restart tomcat@9
```

## Useful Tomcat Commands

```bash
brew services start tomcat@9
brew services stop tomcat@9
brew services restart tomcat@9
tail -f "$(brew --prefix tomcat@9)/libexec/logs/catalina.out"
```

## Common Issues

### Missing Struts Messages

If a JSP reports a missing key such as `login.title`, rebuild and redeploy the WAR. The Struts message bundle must be packaged at:

```text
WEB-INF/classes/resources/ApplicationResources.properties
```

Verify with:

```bash
jar tf target/taskdesk-legacy.war | grep ApplicationResources
```

### SQLite Path Does Not Exist

If login fails with a message like:

```text
path to '../runtime-data/taskdesk-demo.sqlite' does not exist
```

Tomcat is resolving a relative SQLite path from its own working directory. Use an absolute `TASKDESK_DB_URL` or update `src/main/resources/taskdesk.properties`, rebuild, and redeploy.

### Wrong Tomcat Version

If deployment fails with servlet API or JSP tag errors on Tomcat 10, switch to Tomcat 9:

```bash
brew install tomcat@9
```

## Clean Redeploy

Preferred path after code changes:

```bash
cd taskdesk-legacy
mvn clean package
./redeploy-mac.sh
brew services restart tomcat@9
```

Manual fallback:

```bash
mvn clean package
export TOMCAT_HOME="$(brew --prefix tomcat@9)/libexec"
brew services stop tomcat@9
rm -rf "$TOMCAT_HOME/webapps/taskdesk-legacy"
cp target/taskdesk-legacy.war "$TOMCAT_HOME/webapps/"
brew services start tomcat@9
```
