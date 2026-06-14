Security & Responsible Use

Asset Sentinel is a centralized IT asset monitoring platform designed to collect hardware inventory data and identify hardware configuration changes across Windows-based systems.

This platform is intended exclusively for authorized system administration, asset management, and hardware monitoring purposes. Users are responsible for ensuring that deployment and use of Asset Sentinel comply with applicable organizational policies, legal requirements, and industry regulations.

---

Data & Asset Information

Asset Sentinel collects hardware-related information, including:

- System identification details
- RAM configuration
- Motherboard information
- Hardware inventory records
- Alert history

Asset Sentinel is not designed to collect:

- Personal files
- User documents
- Browser data
- Passwords
- Financial information
- Personal communications

The platform is designed to focus solely on hardware inventory and configuration monitoring, minimizing the collection of non-essential user data.

---

Secrets & Credentials

Asset Sentinel may require credentials for email notifications and future third-party integrations.

To safeguard sensitive information, the following security practices are recommended:

- Store credentials securely using environment variables or approved secret management solutions.
- Never hardcode secrets or credentials within source code.
- Exclude sensitive configuration files from source control repositories.
- Do not commit email passwords, API keys, authentication tokens, or other confidential information to version control systems.

Organizations should implement appropriate access controls and credential management procedures to further protect sensitive data.

---

Reporting Security Issues

If you identify a security vulnerability or potential security concern, please report it responsibly to the project maintainer.

When submitting a report, please include:

- A clear description of the vulnerability
- Detailed steps to reproduce the issue
- An assessment of the potential impact
- Suggested remediation or mitigation measures, if available

To support responsible disclosure practices, please refrain from publicly sharing security vulnerabilities until they have been reviewed and addressed.

---

Scope & Limitations

Asset Sentinel is designed specifically for hardware inventory monitoring and hardware change detection.

The platform does not provide:

- Endpoint protection
- Antivirus capabilities
- Malware detection
- Network intrusion detection
- Data loss prevention

Asset Sentinel should be deployed as part of a broader security strategy and used alongside appropriate security controls, monitoring tools, and endpoint protection solutions.