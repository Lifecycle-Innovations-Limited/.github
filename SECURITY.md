# Security Policy
Healify is dedicated to the security and privacy of its users. We encourage responsible vulnerability disclosure and will work proactively to resolve security issues impacting our public code, APIs, and systems.

## Scope
This policy applies to:
- Public Healify repositories, open-source software, and APIs
- Healify web applications and services exposed to the public internet

**Note:** Do not run tests against production systems containing real PHI/PII or sensitive health data without explicit authorization.

## Reporting a Vulnerability
If you discover a vulnerability related to Healify, please report it via **support@healify.ai** with:
- Detailed description of the issue
- Steps to reproduce (ideally with proof-of-concept)
- Affected components, commit SHAs, endpoints, or versions
- Impact assessment (confidentiality/integrity/availability)
- Your contact information & preferred disclosure timeline

Alternatively, use GitHub Security Advisories to make a private report.  
**Do not post public GitHub issues for security concerns.**

## Coordinated Disclosure Policy
- Allow Healify reasonable time to investigate and address vulnerabilities before public disclosure.
- Our team will acknowledge reports within **72 hours**, provide a status update within **7 days**, and aim to resolve or mitigate critical vulnerabilities as quickly as possible, depending on severity and complexity.
- Responsible disclosures are valued; we offer public recognition and, where applicable, discretionary rewards.

## Safe Harbor
Healify will not pursue legal action for good-faith, compliant research that:
- Does *not* degrade service, exfiltrate, modify, or persist data
- Only accesses your accounts/data
- Follows ethical guidelines and avoids rate limit or DoS testing

**If in doubt, contact us first at support@healify.ai.**

## Out of Scope
- Social engineering (phishing, vishing, etc.)
- Physical attacks
- DoS/volumetric/resource exhaustion tests
- Automated scanner results with no actionable exploitation
- Vulnerabilities in third-party platforms unless directly impacting Healify

## Severity & SLA Guidance
Healify uses [CVSS v3.1](https://www.first.org/cvss/) for triage.

| Severity   | Example Impact                                | Target Fix / Mitigation  |
|------------|-----------------------------------------------|-------------------------|
| Critical   | Remote code execution, auth bypass, PHI leak  | ASAP, public fix in ≤7d |
| High       | Privilege escalation, major data risk         | ≤ 14-30 days            |
| Medium     | CSRF/XSS (limited), info leak, insecure defaults | Normal cadence        |
| Low        | Hardening, best-practices                     | Next maintenance        |

## Sensitive Data Handling
- **Do not send reports containing real PHI/PII or patient data.**  
- Always redact or synthesize data in your PoC. If you believe PHI/PII exposure is present, email us first for encrypted transfer instructions.
- Healify can provide a PGP public key for secure communications upon request.

## Bounty & Recognition
Healify does **not** run a formal bug bounty program but may, at its discretion:
- Credit researchers in release notes/Hall of Fame
- Offer thank-you gifts or bonuses for impactful, well-documented reports

## Security Practices (High-Level)
For transparency, Healify shares these practices:
- Principle of least privilege for infra and CI/CD
- Automated dependency/container scans, secrets rotation and access control
- Code review (security checks, CodeQL/SCA, supply-chain controls)
- Defense-in-depth for auth, rate limiting, monitoring
- Regular incident response drills and post-incident reviews

## Contact
- Email: **support@healify.ai** or via the chat on our website

### PGP
Healify’s public PGP key available upon request. Email to obtain current fingerprint.

## Legal Notice
By submitting a vulnerability report, you agree to comply with all applicable laws and this policy. You do *not* have permission to access or test data you do not own, nor undertake prohibited actions as described above.

