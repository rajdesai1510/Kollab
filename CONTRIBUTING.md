# Kollab Contribution Guidelines

Welcome to Kollab! To maintain code quality and keep our project history clean and readable, please follow these guidelines when developing, committing, or pushing code.

---

## 1. Branching Strategy

Our repository uses three permanent branches:

1. **`develop`** (Active Development): 
   * All active feature development and bug fixes are integrated here. 
   * This is our primary working branch.
2. **`staging`** (Pre-production Testing):
   * Code from `develop` is merged here for integration testing and staging deployment.
3. **`main`** (Production):
   * Stable, production-ready release code. Only thoroughly tested staging builds are merged into `main`.

---

## 2. Commit Message Guidelines

All commit messages **must** follow a strict format to allow easy tracking of changes and association with issues.

### Format
```text
[TYPE] [issue_number] Short title

Detailed description of the changes made, bulleted where appropriate.
```

### Rules
1. **Commit Type:** Must be written in **UPPERCASE** within square brackets. Supported types are:
   * `[INITIALIZE]` - Initial repository setup, base scaffolding, and structural foundations.
   * `[FEATURE]` - New features, API endpoints, or user interface components.
   * `[BUGFIX]` - Resolving errors, exceptions, or unintended behaviors.
   * `[REFACTOR]` - Restructuring code without changing its external behavior.
   * `[DOCS]` - Adding or modifying documentation files (like README or guides).
   * `[CHORE]` - Updates to dependencies, environment configs, or build scripts.
2. **Issue Number:** Must be specified in square brackets (e.g., `[#1]`).
3. **Title Length:** Keep the short title under 72 characters.
4. **Separation:** Ensure there is a blank line between the title and the description body.
5. **Precision:** Keep commit descriptions, issue updates, and pull request comments small, precise, and directly to the point. Avoid verbose explanations.

### Examples
* **Initial commit:**
  ```text
  [INITIALIZE] [#1] Setup base project structure and celery integration
  ```
* **Adding a feature:**
  ```text
  [FEATURE] [#2] Implement GPS location state and district auto-lookup
  ```
* **Fixing a bug:**
  ```text
  [BUGFIX] [#3] Resolve event loop collision error in Celery task worker
  ```

---

## 3. Contribution Workflow

1. Always pull latest changes from the remote repository before starting work.
2. Create/checkout to the `develop` branch.
3. Verify that all linting tests and compilation checks pass locally (`py_compile` for python, `npx tsc --noEmit` for frontend).
4. Stage and commit your changes using the guidelines above.
5. Push to the remote branch (`develop`).
