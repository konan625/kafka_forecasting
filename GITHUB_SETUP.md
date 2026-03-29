# Push this project to GitHub (private repo, first push)

The repository is initialized on `main` with the first commit. Complete the upload on your machine:

## Option A — GitHub CLI (recommended)

1. Install the CLI (Ubuntu):

   ```bash
   sudo apt install gh
   ```

2. Log in:

   ```bash
   gh auth login
   ```

   Choose GitHub.com → HTTPS → authenticate in the browser.

3. From the project directory, create a **private** repo and push:

   ```bash
   cd /home/aanchal-sharma/dev/kafka
   gh repo create ufs-kafka-minimal --private --source=. --remote=origin --push
   ```

   Change `ufs-kafka-minimal` to any repo name you want. If the name is taken, pick another.

## Option B — GitHub website + git

1. On GitHub: **New repository** → name it (e.g. `ufs-kafka-minimal`) → **Private** → **do not** add README/gitignore (this repo already has them).

2. Push:

   ```bash
   cd /home/aanchal-sharma/dev/kafka
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

   Use SSH instead of HTTPS if you prefer: `git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git`

## Git author on this machine

This repo uses a local identity for commits:

- `user.name`: Aanchal Sharma  
- `user.email`: aanchal-sharma@users.noreply.github.com  

To match your real GitHub email or noreply address:

```bash
cd /home/aanchal-sharma/dev/kafka
git config user.email "your-email@example.com"
git config user.name "Your Name"
# Optional: amend the last commit to refresh author
git commit --amend --reset-author --no-edit
```
