---
description: How to deploy the application and what to check
---

1. Run the build and push command:
   ```pwsh
   npm run build && node scripts/create-nojekyll.js && git add . && git commit -m "deploy: update application" && git push origin main
   ```

2. Wait for the GitHub Action to complete. You can monitor it here:
   [GitHub Actions Tab](https://github.com/eltonaguiar/FAVCREATORS/actions)

3. Once the action is finished (green checkmark), check the live site at:
   [https://eltonaguiar.github.io/FAVCREATORS/](https://eltonaguiar.github.io/FAVCREATORS/)

4. **Pro Tip**: If the page doesn't show your changes immediately, perform a **Hard Refresh** (`Ctrl + F5` or `Cmd + Shift + R`).
