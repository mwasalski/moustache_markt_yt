# CI/CD with GitHub Actions

Three workflows in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | push to `main`, pull request, manual | lint → tests (Python 3.10/3.12/3.13) → build wheel → smoke test of the installed wheel → deploy to **dev** (`main` only) |
| `release.yml` | tag `sim-v*` | build wheel → GitHub Release with the wheel attached + deploy to **prod** (after approval) |
| `deploy.yml` | called by the two above | uploads the wheel to a Unity Catalog volume using the environment's secrets |

Run the same checks locally before pushing:

```bash
pip install -r requirements-dev.txt ruff==0.17.4
ruff check .
pytest
python -m build retail-simulator --outdir dist   # needs: pip install build
```

---

## 1. Artifacts vs packages

Two things that sound alike:

**A GitHub Actions artifact** is a file (or folder) that a workflow run saves *with that run*:
test reports, a built wheel, a data sample, a SQL plan. You use artifacts to

- **pass files between jobs.** Every job runs on a fresh machine, so `smoke` and `deploy` would
  not see `build`'s `dist/` folder otherwise (`upload-artifact` → `download-artifact`),
- **download results from the run page** (Actions → run → *Artifacts* at the bottom).

Artifacts expire (90 days by default, `retention-days` sets less) and belong to one run.
**They are not a place your team installs code from.**

**A package** is a versioned, installable release that teammates depend on:
`pip install retail-simulator==0.1.0`. In this repo the wheel built in CI is turned into a package
in two places:

| Where | How teammates use it |
|---|---|
| GitHub Release (`release.yml`) | `pip install https://github.com/mwasalski/moustache_markt_yt/releases/download/sim-v0.1.0/retail_simulator-0.1.0-py3-none-any.whl` |
| Unity Catalog volume (`deploy.yml`) | `%pip install /Volumes/moustache_markt_dev/ops/libs/retail_simulator-0.1.0-py3-none-any.whl` in a notebook, or as a job/cluster library |

Without any release, straight from git (any tag, branch or commit):

```bash
pip install "retail-simulator[parquet] @ git+https://github.com/mwasalski/moustache_markt_yt@sim-v0.1.0#subdirectory=retail-simulator"
```

> GitHub Packages supports npm, Maven, NuGet, RubyGems and containers, but **not** Python.
> For a real package index use PyPI (public), or a private index (Azure Artifacts, AWS CodeArtifact,
> JFrog, a GCP Artifact Registry). For a private repo, the Release URL and the git URL need
> GitHub credentials.

The principle behind the pipeline: **build once, deploy the same file everywhere.** The wheel tested
by `smoke` is byte-for-byte the wheel uploaded to dev, because both download the same artifact.

---

## 2. Secrets and variables

| | Secret | Variable |
|---|---|---|
| Stored | encrypted, write-only (you cannot read it back) | plain text |
| In logs | masked as `***` | visible |
| In YAML | `${{ secrets.NAME }}` | `${{ vars.NAME }}` |
| Use for | tokens, passwords, keys | URLs, paths, names |

They can live at three levels: **organization**, **repository** or **environment**. With the same name,
environment beats repository, and repository beats organization. This repo uses
**environments** (`dev`, `prod`): one name (`DATABRICKS_TOKEN`) has a different value per
workspace, and `prod` can require a human approval.

### 2.1 Prepare Databricks (once per workspace)

1. **Target volume** for wheels. Run in a SQL editor or notebook:
   ```sql
   CREATE VOLUME IF NOT EXISTS moustache_markt_dev.ops.libs COMMENT 'Python wheels deployed by CI';
   CREATE VOLUME IF NOT EXISTS moustache_markt_prod.ops.libs COMMENT 'Python wheels deployed by CI';
   ```
2. **Token.** Top right avatar → *Settings* → *Developer* → *Access tokens* → *Generate new token*.
   Name it `github-actions-dev`, set an expiry (e.g. 90 days), copy the value now, because it is shown
   only once. For production, use a **service principal** instead of your personal token (see 2.5).
3. **Host**: the workspace URL from the browser, e.g. `https://dbc-1234abcd-5678.cloud.databricks.com`.

### 2.2 Create the environments in GitHub (web UI)

Repository → **Settings** → **Environments** → **New environment** → name `dev` → *Configure environment*:

1. **Environment secrets** → *Add environment secret*
   - `DATABRICKS_TOKEN` = the token from 2.1
2. **Environment variables** → *Add environment variable*
   - `DATABRICKS_HOST` = `https://dbc-....cloud.databricks.com`
   - `DATABRICKS_WHEEL_DIR` = `/Volumes/moustache_markt_dev/ops/libs`

Repeat for `prod` (prod token and `/Volumes/moustache_markt_prod/ops/libs`), and also set:

- **Required reviewers**: add yourself. A prod deployment then pauses with a *Review deployments*
  button until approved.
- **Deployment branches and tags** → *Selected branches and tags* → add the tag rule `sim-v*`.
  Prod secrets then cannot be used by any other branch, even if someone edits a workflow.

> Environments with these protection rules are free for **public** repositories. In a private repo
> they need a paid plan (required reviewers: Enterprise). There, fall back to repository secrets
> (Settings → Secrets and variables → Actions) and drop `environment:` from `deploy.yml`.

### 2.3 The same with the GitHub CLI

```bash
gh secret set DATABRICKS_TOKEN --env dev          # prompts for the value, keeps it out of shell history
gh variable set DATABRICKS_HOST --env dev --body "https://dbc-1234abcd-5678.cloud.databricks.com"
gh variable set DATABRICKS_WHEEL_DIR --env dev --body "/Volumes/moustache_markt_dev/ops/libs"
gh secret list --env dev                          # names and dates only, never values
```

### 2.4 How the workflow uses them (`deploy.yml`)

```yaml
jobs:
  deploy:
    environment: ${{ inputs.environment }}            # unlocks that environment's secrets
    env:
      DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST }}
      DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}  # the Databricks CLI reads these two
```

Rules worth remembering:

- **Pass secrets through `env:`**, then use `"$NAME"` in the script. Do not paste `${{ secrets.X }}` or
  any user-controlled `${{ }}` value (PR title, branch name) directly into `run:`. The expression is
  substituted into the script text before bash runs, which allows script injection.
- **A missing secret is an empty string**, not an error. That is why `deploy.yml` checks first.
- **Masking only covers the exact value.** Base64-encoding or slicing a secret and printing it
  leaks it. Never `echo` a secret.
- **Pull requests from forks get no secrets** (and a read-only `GITHUB_TOKEN`). That is why
  deployment runs only on `push` to `main` and on tags.
- **`GITHUB_TOKEN` is a built-in secret**: created for each run, expires when the job ends, and can
  do only what `permissions:` allows. `release.yml` gives `contents: write` to the one job that
  creates the release. Everything else is `contents: read`.

### 2.5 Next step: no long-lived token at all

A personal access token is a long-lived password. The better setup for prod is a Databricks
**service principal** with **workload identity federation (OIDC)**: GitHub issues a short-lived
token for each run (`permissions: id-token: write`), and Databricks trusts it for this repo and
environment only. Nothing secret is stored in GitHub. See the Databricks docs:
*"Enable workload identity federation for GitHub Actions"*.

---

## 3. Releasing a version

```bash
# 1. bump the version
#    retail-simulator/simulator/__init__.py:  __version__ = "0.2.0"
git commit -am "Release retail-simulator 0.2.0" && git push

# 2. tag it - this starts release.yml
git tag sim-v0.2.0
git push origin sim-v0.2.0
```

Actions → *Release simulator* → approve **prod** → the wheel lands in the prod volume, and the
Releases page shows `sim-v0.2.0` with the wheel attached. If the tag and `__version__` differ,
the build fails before anything is published.

## 4. Exercises

1. **Branch protection**: Settings → Branches → rule for `main` → *Require status checks to pass*
   → select `lint` and the `test` jobs. A PR with failing tests then cannot be merged.
2. Break a test on a branch, open a PR, download the `test-report-*` artifact from the failed run.
3. Change `config/platform.yml` (add a system) in a PR and read the SQL plan in the `uc-plan` job summary.
4. Add `.github/dependabot.yml` with `package-ecosystem: github-actions`, so action versions get
   update PRs.
5. Add a `libs` volume to `uc_bootstrap.py`, so step 2.1.1 is no longer manual.
