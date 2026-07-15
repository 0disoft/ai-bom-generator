import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const PIPENV_VERSIONS = ["2023.12.1", "2026.6.2"] as const;
const OUTPUT_DIRECTORY = resolve("tests/fixtures/pipenv-lock-corpus");
const PIPFILE = `[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
attrs = {version = "==24.2.0", markers = "python_version >= '3.8'"}

[dev-packages]
idna = "==3.10"

[requires]
python_version = "3.12"
`;

type PipenvLock = {
  _meta?: { "pipfile-spec"?: unknown };
  default?: Record<string, unknown>;
  develop?: Record<string, unknown>;
};

function generate(version: string, cwd: string): string {
  const result = Bun.spawnSync({
    cmd: ["uvx", "--from", `pipenv==${version}`, "pipenv", "lock", "--clear"],
    cwd,
    env: {
      ...process.env,
      PIPENV_IGNORE_VIRTUALENVS: "1",
      PIPENV_NOSPIN: "1",
      PIPENV_YES: "1",
    },
    stdout: "pipe",
    stderr: "pipe",
    timeout: 180_000,
  });
  if (result.exitCode !== 0) {
    const stderr = new TextDecoder().decode(result.stderr).trim();
    throw new Error(`Pipenv ${version} failed: ${stderr || `exit ${result.exitCode}`}`);
  }
  return join(cwd, "Pipfile.lock");
}

function validate(version: string, text: string): string {
  const document = JSON.parse(text) as PipenvLock;
  if (document._meta?.["pipfile-spec"] !== 6) {
    throw new Error(`Pipenv ${version} did not emit Pipfile.lock specification 6`);
  }
  if (!("attrs" in (document.default ?? {}))) {
    throw new Error(`Pipenv ${version} output is missing the default attrs package`);
  }
  if (!("idna" in (document.develop ?? {}))) {
    throw new Error(`Pipenv ${version} output is missing the develop idna package`);
  }
  return `${JSON.stringify(document, null, 2)}\n`;
}

const temporaryRoot = await mkdtemp(join(tmpdir(), "ai-bom-pipenv-corpus-"));
const outputs = new Map<string, string>();

try {
  for (const version of PIPENV_VERSIONS) {
    const workingDirectory = join(temporaryRoot, version);
    await mkdir(workingDirectory, { recursive: true });
    await writeFile(join(workingDirectory, "Pipfile"), PIPFILE, "utf8");
    const lockPath = generate(version, workingDirectory);
    outputs.set(version, validate(version, await readFile(lockPath, "utf8")));
  }

  await mkdir(OUTPUT_DIRECTORY, { recursive: true });
  for (const [version, output] of outputs) {
    await writeFile(join(OUTPUT_DIRECTORY, `pipenv-${version}.lock`), output, "utf8");
    console.log(`generated Pipenv ${version} compatibility lock`);
  }
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}
