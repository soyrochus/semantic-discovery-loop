// container-runner/src/copilot-process.mjs

import { spawn } from "node:child_process";

export function executeCopilot({ cwd, prompt, timeoutSeconds }) {
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

    let stdout = "";
    let stderr = "";

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");

    child.stdout.on("data", chunk => {
      stdout += chunk;
      process.stdout.write(chunk);
    });

    child.stderr.on("data", chunk => {
      stderr += chunk;
      process.stderr.write(chunk);
    });

    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
    }, timeoutSeconds * 1000);

    child.on("error", error => {
      clearTimeout(timeout);
      reject(error);
    });

    child.on("close", exitCode => {
      clearTimeout(timeout);

      resolve({
        exitCode,
        stdout,
        stderr
      });
    });
  });
}
