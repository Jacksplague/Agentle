$ErrorActionPreference = "Stop"

function Invoke-PythonModule {
    param([Parameter(Mandatory)][string[]] $Arguments)

    & python -m @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Invoke-PythonModule -Arguments @("ruff", "check", ".")
Invoke-PythonModule -Arguments @("mypy", "src")
Invoke-PythonModule -Arguments @("pytest")
