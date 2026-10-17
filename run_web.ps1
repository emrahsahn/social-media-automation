Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   Sosyal Medya Otomasyon - Web Arayüzü Başlatılıyor" -ForegroundColor Cyan
Write-Host "   Adres: http://localhost:8000" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pipeline.web
