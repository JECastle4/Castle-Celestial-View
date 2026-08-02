$target = "castlecelestialview.net:443"
$versions = @("tls1", "tls1_1", "tls1_2", "tls1_3")

Write-Host "Testing TLS Protocol Support on $target"
Write-Host "======================================="
Write-Host ""

foreach ($version in $versions) {
    Write-Host -NoNewline "$version : "
    
    # Run openssl and capture output
    $output = & openssl s_client -connect $target -$version 2>&1 | Out-String
    
    # Check if connection succeeded
    if ($output -match "Cipher|Protocol" -and $output -notmatch "alert|sslv3 alert") {
        Write-Host "SUPPORTED" -ForegroundColor Yellow
    } else {
        Write-Host "NOT supported" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Expected Results:"
Write-Host "  tls1   : NOT supported (GOOD)"
Write-Host "  tls1_1 : NOT supported (GOOD)"
Write-Host "  tls1_2 : SUPPORTED (GOOD)"
Write-Host "  tls1_3 : SUPPORTED (GOOD)"
