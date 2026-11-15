# Run in an Administrator PowerShell AFTER checking your real lab subnet.
param(
    [ValidateRange(0,101)][int]$DomainId = 31,
    [Parameter(Mandatory=$true)][string]$LabSubnet,
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'
$ruleName = "SmartYard-DDS-$DomainId"
$hyperName = "SmartYard-WSL-DDS-$DomainId"
if ($Remove) {
    Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Get-NetFirewallHyperVRule -Name $hyperName -ErrorAction SilentlyContinue | Remove-NetFirewallHyperVRule
    return
}
if (-not (Get-Command New-NetFirewallHyperVRule -ErrorAction SilentlyContinue)) {
    throw 'Hyper-V firewall cmdlet not available. Update Windows/WSL and verify mirrored mode.'
}
$portBase = 7400 + 250 * $DomainId
$ddsPorts = "$portBase-$($portBase + 249)"
# 49150 is ros2 multicast diagnostic port, separate from DDS domain ports.
$ports = @($ddsPorts, '49150')
$creator = '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'
if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name $ruleName -DisplayName $ruleName -Direction Inbound `
        -Action Allow -Protocol UDP -LocalPort $ports -RemoteAddress $LabSubnet -Profile Private
}
if (-not (Get-NetFirewallHyperVRule -Name $hyperName -ErrorAction SilentlyContinue)) {
    New-NetFirewallHyperVRule -Name $hyperName -DisplayName $hyperName -Direction Inbound `
        -Action Allow -VMCreatorId $creator -Protocol UDP -LocalPorts $ports -RemoteAddresses $LabSubnet
}
Write-Host "Allowed UDP $ddsPorts and 49150 from $LabSubnet. Existing same-name rules were preserved."
