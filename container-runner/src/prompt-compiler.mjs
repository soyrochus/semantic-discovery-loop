// container-runner/src/prompt-compiler.mjs

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PROMPTS_DIRECTORY = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "prompts"
);

const TEMPLATE_BY_MODE = {
  smoke: "smoke-test.prompt.txt",
  full: "execute-semantic-loop.prompt.txt"
};

export async function compilePrompt({
  mode,
  analysisScope,
  runtimeApproved,
  maxIterations
}) {
  const templateFile = TEMPLATE_BY_MODE[mode];

  if (!templateFile) {
    throw new Error(`No prompt template for mode "${mode}"`);
  }

  const template = await readFile(
    path.join(PROMPTS_DIRECTORY, templateFile),
    "utf8"
  );

  return template
    .replaceAll("{{analysisScope}}", analysisScope ?? "")
    .replaceAll("{{runtimeApproved}}", String(runtimeApproved))
    .replaceAll("{{maxIterations}}", String(maxIterations));
}
