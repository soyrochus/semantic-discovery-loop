// container-runner/src/copilot-process.mjs

import { spawn } from "node:child_process";
import { createWriteStream } from "node:fs";
import path from "node:path";

export function executeCopilot({ cwd, prompt, timeoutSeconds, logsDirectory }) {
  return new Promise((resolve, reject) => {
    const args = [
      "--prompt",
      prompt,
      "--output-format=json",
      "--no-ask-user",
      "--no-auto-update",
      "--no-custom-instructions",
      "--no-remote",
      "--no-remote-export",
      "--allow-all-tools",
      "--deny-tool=shell(git push)",
      "--deny-tool=shell(gh:*)"
    ];

    const child = spawn("copilot", args, {
      cwd,
      shell: false,
      env: {
        PATH: process.env.PATH,
        HOME: "/tmp/copilot-home",
        COPILOT_HOME: "/tmp/copilot-home",
        COPILOT_GITHUB_TOKEN: process.env.COPILOT_GITHUB_TOKEN
      },
      stdio: ["ignore", "pipe", "pipe"]
    });

    // Written as chunks arrive, not buffered until close, so a long run is
    // observable on the host by tailing these files (specs/strenghten-container-run.md).
    const stdoutLog = createWriteStream(
      path.join(logsDirectory, "copilot.jsonl"),
      { flags: "a" }
    );
    const stderrLog = createWriteStream(
      path.join(logsDirectory, "copilot.stderr.log"),
      { flags: "a" }
    );

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");

    child.stdout.on("data", chunk => {
      process.stdout.write(chunk);
      stdoutLog.write(chunk);
    });

    child.stderr.on("data", chunk => {
      process.stderr.write(chunk);
      stderrLog.write(chunk);
    });

    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
    }, timeoutSeconds * 1000);

    child.on("error", error => {
      clearTimeout(timeout);
      stdoutLog.end();
      stderrLog.end();
      reject(error);
    });

    child.on("close", exitCode => {
      clearTimeout(timeout);
      stdoutLog.end();
      stderrLog.end();

      resolve({ exitCode });
    });
  });
}
