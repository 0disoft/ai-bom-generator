# Security Policy

## Supported Versions

AI-BOM Generator provides security fixes for the latest released minor line.

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| 0.1.x and earlier | No |

This table is updated when a newer minor line becomes the supported release.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's
**Security** tab and select **Report a vulnerability** to submit a private
vulnerability report for this repository.

Include the following when it is safe to do so:

- affected AI-BOM Generator version and invocation surface (CLI or Action);
- operating system and runner environment;
- minimal reproduction steps and expected versus observed behavior;
- security impact, including whether paths, secrets, generated reports, or
  caller-owned files are exposed or modified;
- redacted logs or proof-of-concept files; and
- any known mitigation or suggested remediation.

Do not include real credentials, private model weights, private prompts,
customer data, or private dataset contents. Replace them with the smallest
synthetic reproduction that demonstrates the issue.

The maintainer will triage reports on a best-effort basis, coordinate disclosure
through the private advisory, and publish a new immutable patch release when a
supported version requires a fix. No response-time SLA is currently promised.

## Security Scope

Relevant reports include path or symlink escapes, redaction bypasses, unsafe
output replacement, malicious config or dependency-file handling, GitHub Action
permission or output injection, and release or dependency supply-chain issues.

AI-BOM Generator does not claim that generated BOMs prove model safety,
vulnerability status, license compliance, or complete provenance.
