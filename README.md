# Switch inventory report

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Welcome to the manual of a switch inventory script - a tool enabling checking network device details and interface
maintenance reporting.
Script works for Cisco IOS and Aruba devices, obtaining:
- device serial number,
- device model,
- ports with their statuses.

## ➕ Dependencies

Script works on ssh communication protocol managed by ``netmiko`` library:

``pip install netmiko``

## 📃 Outputs

Default script execution outputs:
- logs: exported to ``\logs`` subdirectory, which is being created on a first script execution,
- reports: exported to ``\exports`` subdirectory, created on a first successful run through network devices.

Report format:

| IP Address     | Serial Number | Model        | Port  | Port Status |
|----------------|----------------|---------------|-------|--------------|
| 192.168.1.10   | SN1234567890  | Cisco 2960X   | Gi0/1 | Up           |

## 📝 Annotations

Script operates on a config file, which is being created from a template on a script first run in a script directory.
If a config file is already in place, make sure to provide correct details:

```python
{
    "username": "",
    "password": "",
    "devices": {
        "cisco_ios": [
            "10.xx.xx.xx",
            "10.xx.xx.xxx"
        ]
    }
}
```
**IMPORTANT!** this configuration template should be used for development purposes. Final version of this script, 
in order to ensure safety standard, should obtain credentials from:
- secure key vault,
- environment variables.
Please treat this as a PoC approach for this script and do not apply this in production environment.

## 📜 License

Project is available under terms of **[Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0)**.  
Full license text can be found in file: [LICENSE](./LICENSE).

---

© 2025 **Vismaanen** — simple coding for simple life