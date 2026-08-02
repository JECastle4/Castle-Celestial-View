#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Bandit security scan wrapper
    
.DESCRIPTION
    Runs bandit security scanning on the API code, excluding test, audit, and non-production directories.
    Audit scripts (test-*.py) intentionally use assertions and random generators, which are legitimate
    in test/audit code but flagged by bandit's B101 and B311 checks.
    
.EXAMPLE
    .\run-bandit.ps1
    .\run-bandit.ps1 -Severity medium
    .\run-bandit.ps1 -Confidence high
#>
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run bandit with proper exclusions
& python -m bandit -r $scriptDir `
    -x "./tests,./htmlcov,./__pycache__,./.venv,./scripts/stability-audit,./research,./icon-generator,./frontend" `
    @Args

exit $LASTEXITCODE
