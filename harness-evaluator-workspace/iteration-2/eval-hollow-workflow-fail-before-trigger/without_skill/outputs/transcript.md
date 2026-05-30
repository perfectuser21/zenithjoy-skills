# Evaluation Transcript

## Input
File: `/tmp/eval-evaluator-fixtures/hollow-workflow.yml`

## Step 1: Read the workflow file

The workflow is named `agent-hollow-check`. It is triggered via `workflow_dispatch` with one input (`artifact_path`). It runs on `windows-latest` and has a single job (`verify`) with two steps:

1. `Download artifact` — downloads `zenithjoy-agent` using `actions/download-artifact@v3`
2. `Check file exists` — PowerShell script that checks the downloaded `.exe` is at least 1 MB; throws if smaller, prints size if OK

## Step 2: Apply evaluation criteria

Real business logic testing requires at least one of:
- Installing and launching the agent
- Connecting to a real backend API endpoint
- Authenticating a user session
- Verifying a golden-path step (login, profile setup, publish, etc.)
- Reading/writing to a real database
- Asserting on observable behavioral output

None of these are present. The only assertion is `$file.Length -lt 1MB`.

## Step 3: Classify

**Classification: HOLLOW**

A file-size threshold is a packaging check. It tells us the build artifact was produced and is non-trivially sized. It says nothing about whether the artifact functions correctly.

## Step 4: Decision

Do NOT trigger final E2E. The workflow does not demonstrate that any business logic works.
