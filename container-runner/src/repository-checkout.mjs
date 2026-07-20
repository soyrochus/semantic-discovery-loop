// container-runner/src/repository-checkout.mjs

import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";

export async function checkoutRepository({ workspace, repository }) {
  const directory = path.join(workspace, "repository");
  await mkdir(directory, { recursive: true });

  await runGit(["clone", "--quiet", "--no-tags", repository.url, directory]);
  await runGit(["-C", directory, "checkout", "--quiet", repository.ref]);

  const resolvedCommit = (
    await runGit(["-C", directory, "rev-parse", "HEAD"], { capture: true })
  ).trim();

  return {
    directory,
    requestedRef: repository.ref,
    resolvedCommit
  };
}

function runGit(args, { capture = false } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn("git", args, {
      stdio: ["ignore", capture ? "pipe" : "inherit", "inherit"]
    });

    let stdout = "";

    if (capture) {
      child.stdout.setEncoding("utf8");
      child.stdout.on("data", chunk => {
        stdout += chunk;
      });
    }

    child.on("error", reject);

    child.on("close", exitCode => {
      if (exitCode !== 0) {
        reject(new Error(`git ${args.join(" ")} exited with code ${exitCode}`));
        return;
      }

      resolve(stdout);
    });
  });
}
