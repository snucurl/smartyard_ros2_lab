<#
.SYNOPSIS
    WSL2 및 동일 서브넷(10.10.61.0/24) 환경의 ROS 2 DDS 통신용 방화벽 설정 스크립트
.EXAMPLE
    .\scripts\configure_firewall.ps1 -DomainId 31 -LabSubnet '10.10.61.0/24'
#>

param (
    [Parameter(Mandatory=$false)]
    [int]$DomainId = 31,

    [Parameter(Mandatory=$false)]
    [string]$LabSubnet = "10.10.61.0/24"
)

# 1. 관리자 권한 확인
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "이 스크립트는 관리자 권한으로 실행해야 합니다. PowerShell을 '관리자 권한으로 실행' 후 다시 시도하세요."
    exit 1
}

# 2. 잘못된 CIDR 표기(/41 등) 자동 보정 및 검증
if ($LabSubnet -match '^(\d+\.\d+\.\d+\.)\d+/(\d+)$') {
    $Prefix = [int]$matches[2]
    if ($Prefix -gt 32) {
        Write-Warning "입력된 서브넷 '$LabSubnet'의 마스크(/$Prefix)가 유효 범위(0~32)를 초과했습니다."
        $LabSubnet = "$($matches[1])0/24"
        Write-Host " -> 동일 네트워크 대역인 '$LabSubnet'으로 자동 보정하여 진행합니다." -ForegroundColor Yellow
    }
}

# 3. ROS 2 DDS (RTPS) 표준 포트 계산 (Base: 7400, Domain Gain: 250)
$PortBase = 7400 + (250 * $DomainId)
$DiscoveryMulticastPort = $PortBase + 0      # 15150 (Domain 31 기준)
$UserMulticastPort      = $PortBase + 1      # 15151
$DiscoveryUnicastStart  = $PortBase + 10     # 15160
$DiscoveryUnicastEnd    = $PortBase + 11     # 15161
$UserUnicastStart       = $PortBase + 12     # 15162
$UserUnicastEnd         = $PortBase + 49     # 15199 (다중 노드 및 WSL 브릿지 여유 포트)

$UdpPorts = @(
    "$DiscoveryMulticastPort",
    "$UserMulticastPort",
    "$DiscoveryUnicastStart-$DiscoveryUnicastEnd",
    "$UserUnicastStart-$UserUnicastEnd"
)

$RulePrefix = "ROS2_WSL_Domain_${DomainId}"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "ROS 2 (WSL2 + 로컬 서브넷) 방화벽 설정을 시작합니다." -ForegroundColor Cyan
Write-Host " - Domain ID     : $DomainId"
Write-Host " - 허용 서브넷   : $LabSubnet"
Write-Host " - 허용 UDP 포트 : $($UdpPorts -join ', ')"
Write-Host "==================================================" -ForegroundColor Cyan

# 4. 기존 동일 이름의 규칙 삭제 (중복 방지)
Remove-NetFirewallRule -DisplayName "${RulePrefix}_*" -ErrorAction SilentlyContinue

# 5. 동일 네트워크 서브넷(LabSubnet) UDP 인바운드 허용
New-NetFirewallRule -DisplayName "${RulePrefix}_Subnet_UDP_Inbound" `
    -Direction Inbound `
    -Protocol UDP `
    -LocalPort $UdpPorts `
    -RemoteAddress $LabSubnet `
    -Action Allow `
    -Profile Any `
    -Description "ROS 2 DDS UDP traffic for Domain $DomainId from $LabSubnet" | Out-Null

# 6. WSL2 가상 네트워크 인터페이스(vEthernet (WSL)) 트래픽 전체 허용
$WslAdapter = Get-NetAdapter -Name "*WSL*" -ErrorAction SilentlyContinue
if ($WslAdapter) {
    New-NetFirewallRule -DisplayName "${RulePrefix}_WSL_Interface_Inbound" `
        -Direction Inbound `
        -InterfaceAlias $WslAdapter.Name `
        -Action Allow `
        -Profile Any `
        -Description "Allow ROS 2 DDS traffic from WSL2 virtual interface" | Out-Null
    Write-Host " - WSL 가상 어댑터($($WslAdapter.Name)) 인바운드 허용 완료" -ForegroundColor Gray
} else {
    Write-Warning "WSL 가상 어댑터(vEthernet (WSL))를 찾지 못했습니다. WSL2가 실행 중인지 확인하세요."
}

# 7. 멀티캐스트(239.255.0.1) Discovery 패킷 허용
New-NetFirewallRule -DisplayName "${RulePrefix}_Multicast_UDP_Inbound" `
    -Direction Inbound `
    -Protocol UDP `
    -LocalPort $UdpPorts `
    -RemoteAddress "239.255.0.0/16" `
    -Action Allow `
    -Profile Any `
    -Description "Allow ROS 2 DDS Multicast Discovery" | Out-Null

# 8. ICMP (Ping) 허용
New-NetFirewallRule -DisplayName "${RulePrefix}_ICMP_Inbound" `
    -Direction Inbound `
    -Protocol ICMPv4 `
    -IcmpType 8 `
    -RemoteAddress $LabSubnet `
    -Action Allow `
    -Profile Any `
    -Description "Allow Ping from $LabSubnet" | Out-Null

Write-Host "[완료] WSL2 및 $LabSubnet 환경의 방화벽 설정이 완료되었습니다." -ForegroundColor Green
