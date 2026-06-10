param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BridgeArgs
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bridge = Join-Path $root "tools\ai-bridge.py"

if ($BridgeArgs.Count -eq 0) {
    & py -3.10 $bridge --repo-root $root status
    exit $LASTEXITCODE
}

$first = $BridgeArgs[0].ToLowerInvariant()
$commands = @("advise", "implement", "review", "triage", "status", "sync")

if ($commands -contains $first -or $first.StartsWith("--")) {
    & py -3.10 $bridge --repo-root $root @BridgeArgs
} else {
    & py -3.10 $bridge --repo-root $root advise ($BridgeArgs -join " ")
}
exit $LASTEXITCODE
