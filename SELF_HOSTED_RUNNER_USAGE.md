# Using the Self‑Hosted GitHub Action Runner

**Location of the runner:** `E:\actions-runner`

---

## 1. Overview
A self‑hosted runner allows you to execute GitHub Actions on your own hardware. This is useful when you need:
- Access to internal networks or private APIs (e.g., our ExchangeRate‑API key).
- More CPU / memory than the default GitHub‑hosted runners.
- Persistent state between workflow runs (e.g., cached data files).

---

## 2. Prerequisites
| Requirement | Details |
|-------------|---------|
| **Operating System** | Windows 11 (the runner is installed under `E:\actions-runner`). |
| **PowerShell** | Version 5.1+ (installed by default on Windows 11). |
| **Git** | Must be in the system `PATH` (used by the runner to fetch the repository). |
| **Network** | Outbound internet access to the APIs used by the project (ExchangeRate‑API, Binance, etc.). |
| **GitHub Token** | A **personal access token (PAT)** with `repo` and `admin:org` scopes, stored as a secret in the repository (`RUNNER_TOKEN`). |

---

## 3. Installation Steps (run once)
1. **Open PowerShell as Administrator** and navigate to the runner directory:
   ```powershell
   cd E:\actions-runner
   ```
2. **Download the latest runner package** (replace `x64` with the appropriate architecture if needed):
   ```powershell
   Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-win-x64-2.311.0.zip" -OutFile "runner.zip"
   ```
3. **Extract the archive**:
   ```powershell
   Expand-Archive -Path "runner.zip" -DestinationPath .
   ```
4. **Configure the runner** – you will need your repository URL and the PAT:
   ```powershell
   .\config.cmd --url https://github.com/YourOrg/YourRepo --token $env:RUNNER_TOKEN
   ```
   - When prompted, give the runner a name (e.g., `self-hosted-windows`).
   - Choose **`[Enter]`** for the default work folder.
   - Accept the default for **`[Enter]`** on the “run as a service” question if you want the runner to start automatically.
5. **Install the runner as a Windows service** (recommended for production):
   ```powershell
   .\svcinstall.cmd
   ```
6. **Start the service**:
   ```powershell
   Start-Service actions.runner.
‑ed   ```

---

## 4. Verifying the Runner
1. In GitHub, go to **Settings → Actions → Runners** for your repository.
2. You should see a runner named `self-hosted-windows` with a **green** status indicating it is online.
3. Run a quick workflow to confirm it works:
   ```yaml
   name: Test Self‑Hosted Runner
   on: [push]
   jobs:
     test:
       runs-on: self-hosted
       steps:
         - name: Echo runner info
           run: echo "Running on ${{ runner.name }}"
   ```
   - The job should complete and the log will show the runner name.

---

## 5. Updating the Runner
When a new runner version is released:
1. **Stop the service**:
   ```powershell
   Stop-Service actions.runner.
   ```
2. **Delete the old binaries** (keep the `config` folder):
   ```powershell
   Remove-Item * -Exclude config, .env -Recurse -Force
   ```
3. **Download and extract the new version** (repeat steps 2‑3 from the installation section).
4. **Re‑configure** (if you removed the `config` folder, run `config.cmd` again).
5. **Re‑install the service** (`svcinstall.cmd`) and start it.

---

## 6. Common Issues & Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Runner stays **offline** | Service not started or missing PAT | Run `Start-Service actions.runner.` and verify the token is still valid. |
| **CORS** errors still appear | Runner cannot reach external API due to firewall | Ensure outbound ports 443 and 80 are open for the runner machine. |
| **GitHub rate‑limit** errors | Runner uses the default anonymous IP address | Add your ExchangeRate‑API key to the repository secrets and reference it in the workflow. |
| **Missing Forex picks** after runner update | Cached data not cleared | Delete the `./cache` folder in the repository (or add a `run: rm -rf cache` step). |

---

## 7. Security Considerations
- **Least‑privilege token:** Use a PAT with only the scopes required for the runner.
- **Firewall rules:** Restrict inbound traffic to the runner machine; only allow outbound to required APIs.
- **File permissions:** Ensure the `E:\actions-runner` directory is not writable by non‑admin users.

---

## 8. References
- [GitHub Docs – Adding a self‑hosted runner] (https://docs.github.com/en/actions/hosting-your-own-runners/adding-self-hosted-runners)
- [GitHub Docs – Using self‑hosted runners] (https://docs.github.com/en/actions/hosting-your-own-runners/using-self-hosted-runners)
- [ExchangeRate‑API Docs] (https://www.exchangerate-api.com/docs)
- [Binance API CORS Workarounds] (https://github.com/axios/axios/issues/1234)

---

*Prepared by the Content Research Writer skill, following the collaborative writing workflow.*