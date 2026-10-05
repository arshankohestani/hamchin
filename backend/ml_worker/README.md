# Worker رایگان یادگیری هم‌چین

این worker خارج از تابع اصلی Vercel اجرا می‌شود تا حجم CatBoost باعث خراب‌شدن انتشار سایت نشود.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
$env:DATABASE_URL="آدرس اتصال Neon"
.\.venv\Scripts\python.exe -m ml_worker.train --target-term 1405-1
```

مدل تقاضا پس از وجود حداقل ۸ رکورد از دو نیم‌سال آموزش می‌بیند و پیش‌بینی‌ها را در Neon می‌نویسد. Ranker پس از ثبت حداقل ۵ امتیاز متفاوت مدیرگروه آموزش می‌بیند. API اصلی نتیجه‌های ذخیره‌شده را بدون نیاز به نصب CatBoost مصرف می‌کند.
