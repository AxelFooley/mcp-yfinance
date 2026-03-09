# Debug Session: CI/CD Workflow Repository Name Mismatch

**Created:** 2026-03-09
**Status:** ROOT CAUSE FOUND

## Summary

Discovered repository name inconsistency in CI/CD workflow that will cause Docker image push to fail.

## Symptoms

| Field | Value |
|-------|-------|
| **Expected** | Image pushed to correct GHCR repository |
| **Actual** | Image will be pushed to wrong repository name |
| **Error** | Docker push may fail or push to incorrect location |

## Root Cause

**Repository Names:**
- Git remote: `git@github.com:AxelFooley/mcp-yfinance.git`
- CI workflow image name: `ghcr.io/axelfooley/finance-mcp-server`

**The Problem:**
The repository is `mcp-yfinance` but the Docker image is named `finance-mcp-server`. This creates a mismatch between the repository name and the image name.

**Additionally:**
The documentation mentions `TrackFolio` as the repo URL in CLAUDE.md, but the actual remote is `mcp-yfinance`.

## Fix Required

Update `.github/workflows/ci.yml` line 16:

**Current (WRONG):**
```yaml
IMAGE: ghcr.io/axelfooley/finance-mcp-server
```

**Should be:**
```yaml
IMAGE: ghcr.io/axelfooley/mcp-yfinance
```

Or alternatively, rename the repository to match the image name.

## Additional Check

Also verify that `README.md` and any other documentation reference the correct repository URL.

## Resolution

✅ **Identified** - Repository name mismatch in CI workflow

**Next Steps:**
1. Update CI workflow with correct image name
2. Update README.md with correct repository URL
3. Commit and push correction
