# asma-workflows

Centralized CI/CD workflows and scripts for ASMA project repositories.

## Purpose

This repository provides:

- **GitHub Actions workflows** - Reusable workflow templates for GitHub repos
- **Bitbucket pipeline scripts** - Shell scripts for Bitbucket CI/CD operations

## Dual Hosting

This repository is hosted on both platforms with different names:

- **GitHub** (primary): `Carasent-ASMA/asma-workflows` - Public repo for GitHub Actions
- **Bitbucket**: `carasent/asma-scripts` - Private repo with historical name

## GitHub Actions Workflows

Located in `.github/workflows/`, these can be referenced remotely by other repositories.

### Usage

Reference workflows from your repository:

```yaml
jobs:
  publish:
    uses: Carasent-ASMA/asma-workflows/.github/workflows/reusable-npm-publish.yml@master
    with:
      publish_npm: true
      package_name: "your-package-name"
    secrets: inherit
```

### Available Workflows

#### reusable-npm-publish.yml

Build and publish npm packages with automatic versioning and tagging.

**Inputs:**

- `publish_npm` (boolean, default: true) - Whether to publish to npm registry
- `package_name` (string) - Package name for logging

**Features:**

- Detects code changes since last tag
- Builds TypeScript projects
- Publishes to npm (if enabled)
- Creates GitHub releases
- Automatic version tagging

### Squash Merge Policy

For repositories using commit-message-based release detection:

1. Enable `Allow squash merging` in GitHub repository settings.
2. Set the squash default message to `Pull request title and commit details`.
3. Keep the generated commit details when merging so `feat:`, `fix:`, and similar commit lines remain in the final squash commit body.

This keeps release detection working for both squash merges and direct pushes to `master`.

#### scaffold-doctor.yml

Validate repository structure and configuration.

## Bitbucket Pipeline Scripts

Located in `scripts/prBitbucketScripts/`, these scripts support Bitbucket CI/CD operations:

- Version management and tagging
- Build and deployment to S3
- Hasura integration
- Jira integration
- Release management (prerelease, patch, full release)

## Repository Structure

```text
asma-workflows/
├── .github/
│   └── workflows/              # GitHub Actions reusable workflows
│       ├── reusable-npm-publish.yml
│       └── scaffold-doctor.yml
├── scripts/
│   └── prBitbucketScripts/    # Bitbucket pipeline scripts
├── bitbucket-pipelines.yml    # Bitbucket pipeline configuration
└── readme.md
```

## Git History

This repository was originally named `asma-scripts` and contains rich git history dating back to the early infrastructure setup. The rename to `asma-workflows` better reflects its expanded purpose to include both Bitbucket and GitHub CI/CD tooling.

## Development

### Updating Workflows

1. Make changes in this repository
2. Commit with conventional commit messages
3. Push to GitHub: `git push origin master`
4. Push to Bitbucket: `git push bitbucket master`

All repositories using these workflows will receive updates automatically.

## References

All ASMA shared libraries reference these workflows:

- asma-core-helpers
- asma-micro-app
- asma-types
- asma-ui-\* libraries
