# XTB Dividend Analysis - Test Runner (PowerShell)
# Run this script to execute all tests with coverage reporting.

Write-Host "XTB Dividend Analysis - Test Runner" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

# Change to the project directory (parent of scripts directory)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
Set-Location $projectPath
Write-Host "Working directory: $projectPath" -ForegroundColor Yellow

# Function to run commands and capture results
function Run-TestCommand {
    param(
        [string]$Command,
        [string]$Description
    )
    
    Write-Host "`n" + "="*60 -ForegroundColor Gray
    Write-Host "Running: $Description" -ForegroundColor Green
    Write-Host "Command: $Command" -ForegroundColor Gray
    Write-Host "="*60 -ForegroundColor Gray
    
    try {
        $output = Invoke-Expression $Command 2>&1
        Write-Host $output
        return $true
    }
    catch {
        Write-Host "❌ Command failed: $_" -ForegroundColor Red
        return $false
    }
}

# List of test commands to run
$testCommands = @(
    @("python -m pytest --version", "Checking pytest installation"),
    @("python -m pytest tests/ -v", "Running all tests"),
    @("python -m pytest tests/ -v --cov=data_processing --cov=data_acquisition --cov=visualization --cov=config --cov-report=term-missing", "Running tests with coverage"),
    @("python -c `"import data_processing.dataframe_processor; print('dataframe_processor imports successfully')`"", "Testing module imports")
)

$results = @()

foreach ($commandPair in $testCommands) {
    $command = $commandPair[0]
    $description = $commandPair[1]
    $success = Run-TestCommand -Command $command -Description $description
    $results += @{Description = $description; Success = $success}
}

# Print summary
Write-Host "`n" + "="*60 -ForegroundColor Gray
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "="*60 -ForegroundColor Gray

$allPassed = $true
foreach ($result in $results) {
    if ($result.Success) {
        Write-Host "PASSED: $($result.Description)" -ForegroundColor Green
    } else {
        Write-Host "FAILED: $($result.Description)" -ForegroundColor Red
        $allPassed = $false
    }
}

if ($allPassed) {
    Write-Host "`nAll tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome tests failed!" -ForegroundColor Red
    exit 1
}
