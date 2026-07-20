FROM node:22-bookworm-slim

ARG COPILOT_CLI_VERSION=""

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       git \
       jq \
       python3 \
       tar \
       tini \
    && rm -rf /var/lib/apt/lists/*

# COPILOT_CLI_VERSION pins the npm-distributed CLI; leave it unset to install the
# latest release via GitHub's standalone installer (installs to /usr/local/bin, which
# is already on PATH for root).
RUN if [ -n "$COPILOT_CLI_VERSION" ]; then \
      npm install --global "@github/copilot@${COPILOT_CLI_VERSION}"; \
    else \
      curl -fsSL https://gh.io/copilot-install | bash; \
    fi

WORKDIR /app

COPY container-runner/package.json container-runner/package-lock.json ./
RUN npm ci --omit=dev

COPY container-runner/src ./src
COPY container-runner/prompts ./prompts

COPY .agent-loop /opt/semantic-discovery-loop/.agent-loop

ENV NODE_ENV=production
ENV SEMANTIC_LOOP_HOME=/opt/semantic-discovery-loop/.agent-loop
ENV RUN_REQUEST_PATH=/input/request.json
ENV RUN_OUTPUT_PATH=/output
ENV RUN_MODE=full
ENV COPILOT_HOME=/tmp/copilot-home

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "src/main.mjs"]
