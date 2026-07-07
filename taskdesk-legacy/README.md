# TaskDesk Legacy

TaskDesk Legacy is a simulated Struts 1.x / JSP / JDBC application packaged as a WAR. It uses SQLite for the local demo database and is intended to run on a legacy-compatible servlet container.

These instructions cover macOS (Homebrew) and Linux (tested on Ubuntu 26.04).

## Requirements

- JDK 8 or newer (the build targets Java 8; JDK 17 works fine)
- Maven
- **Tomcat 9, not Tomcat 10.** Struts 1.x and this application use the older `javax.servlet` APIs; Tomcat 10 moved to `jakarta.servlet` and will not run this WAR.

### macOS install

```bash
brew install maven tomcat@9
```

### Linux install

Recent Ubuntu releases ship only `tomcat10` in apt, which does not work with this app, so install Tomcat 9 from Apache. If you have root, the JDK and Maven can come from apt (`sudo apt install openjdk-17-jdk maven`); the fully user-space alternative below needs no root and is what `paths.sh` expects by default:

```bash
mkdir -p ~/opt && cd ~/opt

# Temurin JDK 17
curl -sSLo jdk17.tar.gz "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"
# Maven (check https://maven.apache.org/download.cgi for the current version)
curl -sSLo maven.tar.gz "https://dlcdn.apache.org/maven/maven-3/3.9.16/binaries/apache-maven-3.9.16-bin.tar.gz"
# Tomcat 9 (check https://tomcat.apache.org/download-90.cgi for the current version)
curl -sSLo tomcat9.tar.gz "https://dlcdn.apache.org/tomcat/tomcat-9/v9.0.120/bin/apache-tomcat-9.0.120.tar.gz"

tar xzf jdk17.tar.gz && tar xzf maven.tar.gz && tar xzf tomcat9.tar.gz && rm -f *.tar.gz
ln -sfn jdk-17* jdk17
ln -sfn apache-maven-* maven
ln -sfn apache-tomcat-9* tomcat9
```

To uninstall, delete `~/opt`.

## Environment: paths.sh

All platform differences are captured in one sourceable script. From this directory:

```bash
. ./paths.sh
```

It sets (without overriding values you have already exported):

| Variable          | macOS                              | Linux                          |
|-------------------|------------------------------------|--------------------------------|
| `TOMCAT_HOME`     | `$(brew --prefix tomcat@9)/libexec` | `~/opt/tomcat9`               |
| `JAVA_HOME`/`PATH`| untouched (system JDK)             | `~/opt/jdk17`, `~/opt/maven` (if present) |
| `TASKDESK_DB_URL` | derived from the repo location on both platforms | |

Source it in every shell where you build, deploy, or run Tomcat — humans and AI agents alike. This is the single place to fix if an install location changes.

## Database

The demo database already exists at the repository root:

```text
../db/runtime-data/taskdesk-demo.sqlite
```

The app reads the JDBC URL from `src/main/resources/taskdesk.properties`, but that file contains a machine-specific absolute path. Prefer the `TASKDESK_DB_URL` environment variable, which overrides it without rebuilding — sourcing `paths.sh` sets it to the correct absolute path for the current machine automatically. A JVM system property `-Dtaskdesk.db.url=...` also works.

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
. ./paths.sh
mvn clean package
```

The WAR is created at `target/taskdesk-legacy.war`.

## Deploy And Run

Build, deploy, and (re)start:

```bash
. ./paths.sh
mvn clean package
./redeploy.sh
```

`redeploy.sh` removes any previously exploded `taskdesk-legacy` webapp from `$TOMCAT_HOME/webapps` and copies in the fresh WAR. It sources `paths.sh` itself, so it works standalone too.

Then start (or restart) Tomcat:

```bash
# Foreground (both platforms) — inherits TASKDESK_DB_URL from your shell:
"$TOMCAT_HOME/bin/catalina.sh" run

# Background (both platforms):
"$TOMCAT_HOME/bin/catalina.sh" start
"$TOMCAT_HOME/bin/catalina.sh" stop

# macOS service alternative:
brew services restart tomcat@9
```

Open the app:

```text
http://localhost:8080/taskdesk-legacy/login.do
```

Logs:

```bash
tail -f "$TOMCAT_HOME/logs/catalina.out"
```

### DB override for background/service Tomcat

`catalina.sh start` from a shell where you sourced `paths.sh` inherits `TASKDESK_DB_URL`. Tomcat started as a service (e.g. `brew services`) does not; give it the variable via `setenv.sh`:

```bash
cat > "$TOMCAT_HOME/bin/setenv.sh" <<EOF
export TASKDESK_DB_URL="$TASKDESK_DB_URL"
EOF
chmod +x "$TOMCAT_HOME/bin/setenv.sh"
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

Tomcat is resolving a relative or wrong-machine SQLite path. Make sure Tomcat was started with `TASKDESK_DB_URL` set (source `paths.sh` first, or use `setenv.sh` as above).

### Wrong Tomcat Version

If deployment fails with servlet API or JSP tag errors, you are on Tomcat 10. Install Tomcat 9: `brew install tomcat@9` on macOS, or the Apache tarball on Linux (see the Linux install section — apt's `tomcat10` will not work).
