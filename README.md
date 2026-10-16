# domain-surveyor
DomainSurveyor is a bulk domain assessment tool designed for ISPs and MSPs. It analyzes large sets of domains and produces structured reports (CSV/JSON) including DNS records (A, MX, SPF, DMARC), authoritative SOA data, registrar information (WHOIS/RDAP), and actionable configuration insights for auditing and operational workflows.

## Example configuration file

A possible runtime option file is available at `config/domain_surveyor.example.yaml`.
It includes sections for:

- `logging`
- `dns_external_services`
- `domain_external_services`
- `runtime`

Use it as a baseline and adapt enabled providers, timeouts, rate limits, and credential environment variable names to your environment.
