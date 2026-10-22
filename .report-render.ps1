$ErrorActionPreference='Stop'
$root=(Get-Location).Path
New-Item -ItemType Directory -Force "$root\.report-qa" | Out-Null
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try{
 $doc=$word.Documents.Open("$root\submission\Revised_Project_Report.docx")
 $doc.Repaginate()
 Write-Output "Report pages: $($doc.ComputeStatistics(2))"
 $doc.ExportAsFixedFormat("$root\.report-qa\report.pdf",17)
 $doc.Close(0)
}finally{$word.Quit()}
