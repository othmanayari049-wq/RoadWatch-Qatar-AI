# Security policy

## Supported versions

The latest commit on `main` is the only supported development version until the first stable
release is published.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature for this repository when available:

`Security` → `Advisories` → `Report a vulnerability`

Do not include secrets, private road imagery, personal information, or exploit details in a
public issue. Include the affected component, reproduction conditions, impact, and a safe
proof of concept. Allow reasonable time for triage and remediation before disclosure.

## Deployment notes

- The reference API has no built-in user authentication. Put authenticated TLS termination
  in front of any network-accessible deployment.
- Replace all development passwords and keep secrets outside Git.
- Treat `.pt` and other serialized model artifacts as untrusted code unless they come from a
  controlled training pipeline and have verified digests.
- Restrict model and database filesystem permissions.
- Configure upload and reverse-proxy limits.
- Review raw image collection for faces, license plates, locations, and applicable privacy
  requirements.
- Keep Python packages, base images, Actions, and model runtimes patched.

Automated checks include dependency auditing, CodeQL analysis, Ruff security rules, tests,
and non-root containers. These checks reduce risk but do not replace threat modeling or a
deployment security review.

