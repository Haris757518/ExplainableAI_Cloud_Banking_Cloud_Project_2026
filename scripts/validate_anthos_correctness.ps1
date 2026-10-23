$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$patchManifest=Get-Content -Raw (Join-Path $projectRoot 'deploy\correctness-fix\patch-manifest.json') | ConvertFrom-Json
$javaRoot=Get-ChildItem 'D:\BankingResearch\Tools\JavaValidation\jdk' -Directory | Select-Object -First 1
$env:JAVA_HOME=$javaRoot.FullName
$env:MAVEN_OPTS='-Xmx1536m -Djava.io.tmpdir=D:\BankingResearch\Tools\JavaValidation\tmp'
$summaries=@()
foreach($service in @('balancereader','transactionhistory')){
 $serviceRoot=Join-Path $patchManifest.validation_tree "src\ledger\$service"
 $logPath="D:\BankingResearch\Reports\anthos-$service-final-validation.log"
 & 'D:\BankingResearch\Tools\JavaValidation\maven\apache-maven-3.9.9\bin\mvn.cmd' -f (Join-Path $serviceRoot 'pom.xml') -B '-Dmaven.repo.local=D:\BankingResearch\Tools\JavaValidation\m2' test *> $logPath
 $buildExit=$LASTEXITCODE
 Get-Content $logPath -Tail 12
 if($buildExit -ne 0){throw "Java validation failed for $service; see $logPath"}
 $tests=0;$failures=0;$errors=0;$skipped=0
 foreach($file in Get-ChildItem (Join-Path $serviceRoot 'target\surefire-reports') -Filter 'TEST-*.xml'){
  [xml]$testXml=Get-Content -Raw $file.FullName
  $tests+=[int]$testXml.testsuite.tests;$failures+=[int]$testXml.testsuite.failures
  $errors+=[int]$testXml.testsuite.errors;$skipped+=[int]$testXml.testsuite.skipped
 }
 $summaries+=@{service=$service;tests=$tests;failures=$failures;errors=$errors;skipped=$skipped;log=$logPath}
}
$resultDirectory=Join-Path $projectRoot 'results\correctness_fix'
New-Item -ItemType Directory -Force $resultDirectory | Out-Null
@{status='validated_locally';source='Executed Java unit tests and H2 SQL transactions';patch_sha256=$patchManifest.patch_sha256;services=$summaries;aws_deployed=$false;limitation='H2 PostgreSQL compatibility mode is not a PostgreSQL or AWS deployment test.';checked_at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $resultDirectory 'local-validation.json')
