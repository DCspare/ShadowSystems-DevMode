# 🐙 Git & GitHub Survival Guide (From Zero)
**Target:** Beginners using VS Code Terminal.
**Goal:** Prevent AI (LLMs) from breaking working code and manage Versions (v1, v2) professionally.

---

## 🛑 Phase 0: Setup (Do this once)

Before coding, you need to introduce yourself to the computer.

1.  **Install Git:**
    *   **Windows:** Download & Install [Git for Windows](https://git-scm.com/download/win). (Just click Next, Next, Next...).
    *   **Mac:** Open Terminal, type `git`. It will prompt to install XCode tools. Click Yes.
    *   **Linux:** `sudo apt install git`

2.  **Configure Identity (Terminal):**
    Open your VS Code Terminal (Ctrl+`) and type these (one by one):
    ```bash
    git config --global user.name "YourName"
    git config --global user.email "your-email@example.com"
    ```

3.  **Authenticate GitHub:**
    *   When you push for the first time, VS Code/Git will likely pop up a browser window asking you to **"Authorize GitHub"**. Click Yes.
    *   *Note:* You do NOT need to type your password in the terminal anymore.

---

## 🚀 Phase 1: Locking V1 (Your Save Point)

You said V1 is working (Hugging Face Streaming). We must save this state so we can never lose it.

1.  **Open VS Code** inside your `StreamVault` project folder.
2.  **Initialize the Repo:**
    ```bash
    git init
    # Response: Initialized empty Git repository...
    ```
3.  **Rename Master branch to Main (Standard practice):**
    ```bash
    git branch -M main
    ```
4.  **Stage Your Files (Prepare them):**
    ```bash
    git add .
    # This adds all your working files to the bucket.
    ```
5.  **Commit (Save the Snapshot):**
    ```bash
    git commit -m "Initial V1 Stable: Hugging Face Streaming working"
    ```
6.  **Connect to Cloud (GitHub):**
    *   Go to `github.com` -> Create New Repository -> Name it `StreamVault`.
    *   **Do not** check "Add README" (keep it empty).
    *   Copy the command that looks like: `git remote add origin https://github.com/YourName/StreamVault.git`
    *   Paste it in your terminal.
7.  **Push (Upload):**
    ```bash
    git push -u origin main
    ```
8.  **Tag V1 (The Golden Rule):**
    Now that the code is safe, label it.
    ```bash
    git tag v1.0.0
    git push origin v1.0.0
    ```

**🎉 Success:** You can now see your code on GitHub with a "Release" tag. Even if you delete your laptop, V1 is safe.

---

## 🛡️ Phase 2: The "AI Protection" Workflow (Daily Use)

**NEVER** let ChatGPT/AI modify files while you are on the `main` branch. If the AI messes up, your V1 is broken.
Always work in a "Sandbox" (Feature Branch).

### Step A: Start a New Feature
*Scenario: You want to add the 'ReadVault' database schema.*

1.  **Create and Switch to a new Branch:**
    ```bash
    git checkout -b feature/readvault-schema
    # Meaning: "Copy everything from Main, but move me to a new workspace named feature/readvault-schema"
    ```
2.  **Coding:**
    *   Now you talk to the AI.
    *   AI gives you code. You paste it.
    *   You run it.

### Step B: The "Oops" Moment (AI Broke it)
*Scenario: The AI code gave errors and now the bot won't start.*

1.  **Check which files changed:**
    ```bash
    git status
    ```
2.  **Undo Everything (The Panic Button):**
    ```bash
    git restore .
    # This deletes all changes in this branch since the last commit.
    # Your code goes back to how it was 10 minutes ago.
    ```

### Step C: It Works! (Saving)
*Scenario: The new schema works perfect.*

1.  **Save the Feature:**
    ```bash
    git add .
    git commit -m "Added ReadVault Database Schema"
    ```
2.  **Upload the Branch (Optional Backup):**
    ```bash
    git push origin feature/readvault-schema
    ```

---

## 🤝 Phase 3: Merging (Updating Main)

Once the feature in `feature/readvault-schema` is tested and perfect, we add it to the Gold Master.

1.  **Go back to Main:**
    ```bash
    git checkout main
    ```
2.  **Update Main (If you are working with others, otherwise optional):**
    ```bash
    git pull origin main
    ```
3.  **Merge the Feature:**
    ```bash
    git merge feature/readvault-schema
    # Meaning: "Take the changes from feature branch and put them into Main."
    ```
4.  **Update Cloud:**
    ```bash
    git push origin main
    ```
5.  **Delete the Sandbox (Cleanup):**
    ```bash
    git branch -d feature/readvault-schema
    ```

---

## 🏷️ Phase 4: Versioning Cheat Sheet

When do you create a new Tag?

| Command | Tag Name | Meaning |
| :--- | :--- | :--- |
| **Start** | `v1.0.0` | Initial working bot. |
| **Features** | `v1.1.0` | Added ReadVault Lite support. |
| **Bug Fix** | `v1.1.1` | Fixed bug where Worker Bot crashes on start. |
| **Big Shift** | `v2.0.0` | **ORACLE MIGRATION**. Switched from Python Streaming to Golang. |

**Command to update version:**
```bash
git tag v1.1.0
git push origin v1.1.0
```

---

### 📝 Daily Developer Checklist

1.  **Before asking AI to code:**
    `git checkout -b feat/what-i-want-to-do`

2.  **If AI succeeds:**
    `git add .` -> `git commit -m "Description"`

3.  **If AI fails/hallucinates:**
    `git restore .` (Start over fresh).

4.  **When fully done:**
    `git checkout main` -> `git merge feat/...` -> `git push`
