# Security

## What this package contains

`system-design-skill` is an instruction and local-report package:

- one Agent Skill under `skills/system-design/`;
- Markdown reference files;
- one self-contained HTML/SVG report template;
- one optional local renderer test.

It does not ship an MCP server, hooks, background agents, network clients, executable plugin commands, or install-time scripts. The generated HTML report makes no network requests.

## Review before installation

Agent skills become instructions for a coding agent that may already have access to source code, terminals, credentials, and external services. Review third-party skills before enabling them.

For this package, the primary files to inspect are:

- [`skills/system-design/SKILL.md`](skills/system-design/SKILL.md)
- [`skills/system-design/INTERVIEW.md`](skills/system-design/INTERVIEW.md)
- [`skills/system-design/HTML-REPORT.md`](skills/system-design/HTML-REPORT.md)
- [`skills/system-design/assets/report-template.html`](skills/system-design/assets/report-template.html)
- [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)

Pin production or team installations to a tagged release when reproducibility matters.

## Data handling

The skill reads repository files through the permissions of the host coding agent. It writes design artifacts inside the current repository and a rendered HTML file under the operating system’s temporary directory. It does not transmit repository contents or generated designs to a service.

The host agent and any model provider may have their own data-handling behavior. Review those products separately.

## Reporting a vulnerability

Do not publish a security issue before maintainers have had a reasonable opportunity to investigate it.

Report vulnerabilities privately through [GitHub’s security advisory form](https://github.com/pinchen147/system-design-skill/security/advisories/new). Include:

- the affected version or commit;
- the file and behavior involved;
- reproduction steps;
- the potential impact;
- any suggested remediation.
