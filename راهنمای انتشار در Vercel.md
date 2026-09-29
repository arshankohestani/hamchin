# راهنمای انتشار هم‌چین در Vercel

## پوشهٔ اصلی پروژه

```text
C:\Users\Admin\Desktop\desktop my website\course-scheduler-ai
```

این پوشه را کامل در یک مخزن GitHub قرار دهید. در Vercel همین مخزن را **دو بار** Import می‌کنیم؛ یک بار برای API و یک بار برای سایت.

## ۱. قراردادن پروژه در GitHub

1. در GitHub یک Repository خالی، مثلاً با نام `hamchin` بسازید.
2. در پوشهٔ اصلی پروژه یک ترمینال باز کنید.
3. دستورات زیر را با آدرس مخزن خودتان اجرا کنید:

```powershell
git add .
git commit -m "Prepare Hamchin smart scheduler for deployment"
git branch -M main
git remote add origin https://github.com/USERNAME/hamchin.git
git push -u origin main
```

پوشه‌های سنگین و محلی مثل `node_modules`، `.next` و `.venv` به‌وسیلهٔ `.gitignore` ارسال نمی‌شوند و نباید دستی آپلود شوند.

## ۲. انتشار بک‌اند

1. وارد داشبورد Vercel شوید و `Add New > Project` را بزنید.
2. مخزن `hamchin` را Import کنید.
3. نام پروژه را مثلاً `hamchin-api` بگذارید.
4. در بخش `Root Directory` فقط `backend` را انتخاب کنید.
5. تنظیم Build یا Output Directory را تغییر ندهید.
6. `Deploy` را بزنید.
7. بعد از پایان، آدرس API را کپی کنید؛ مثلاً:

```text
https://hamchin-api.vercel.app
```

این نشانی را در مرورگر آزمایش کنید:

```text
https://hamchin-api.vercel.app/api/health
```

باید پاسخ `{"status":"ok"}` دیده شود.

## ۳. انتشار فرانت‌اند

1. دوباره `Add New > Project` را بزنید و همان مخزن `hamchin` را Import کنید.
2. نام پروژه را مثلاً `hamchin-app` بگذارید.
3. در `Root Directory` فقط `frontend` را انتخاب کنید.
4. Vercel باید Framework را `Next.js` تشخیص دهد.
5. پیش از Deploy، در `Environment Variables` این متغیر را بسازید:

```text
Name: NEXT_PUBLIC_API_URL
Value: https://hamchin-api.vercel.app
```

آدرس را با نشانی واقعی بک‌اند خودتان جایگزین کنید و در انتهای آن `/` نگذارید. متغیر را برای Production و Preview فعال کنید.

6. `Deploy` را بزنید و آدرس نهایی سایت را کپی کنید؛ مثلاً:

```text
https://hamchin-app.vercel.app
```

## ۴. محدودکردن ارتباط بک‌اند به سایت نهایی

1. به پروژهٔ `hamchin-api` در Vercel بروید.
2. مسیر `Settings > Environment Variables` را باز کنید.
3. متغیر زیر را اضافه کنید:

```text
Name: FRONTEND_ORIGINS
Value: https://hamchin-app.vercel.app
```

4. به تب Deployments برگردید و آخرین Deployment بک‌اند را Redeploy کنید.

## ۵. آزمون نهایی

در سایت نهایی این مسیر را یک بار کامل امتحان کنید:

1. یک درس، زمان آزاد یا ظرفیت را تغییر دهید.
2. یک سناریوی تقاضای دانشجو بسازید.
3. «ساخت برنامهٔ هوشمند» را بزنید.
4. مطمئن شوید جدول هفتگی، درصد پوشش و پیشنهادهای ظرفیت نمایش داده می‌شوند.
5. برنامه را تأیید کنید و پس از Refresh باقی‌ماندن نسخهٔ تأییدشده در همان مرورگر را بررسی کنید.

## ۶. دامنه

آدرس `vercel.app` از همان لحظهٔ Deploy قابل استفاده است و برای ارائهٔ فردا کافی است. برای دامنهٔ شخصی، در پروژهٔ `hamchin-app` مسیر `Settings > Domains` را باز کنید، دامنه را وارد کنید و DNS پیشنهادی Vercel را در پنل فروشندهٔ دامنه ثبت کنید. دامنه را به پروژهٔ فرانت‌اند متصل کنید، نه بک‌اند.

## نکتهٔ مهم دربارهٔ نگهداری داده

نسخهٔ پایلوت، آخرین برنامه و تأیید را در مرورگر مدیرگروه نگه می‌دارد. فایل SQLite بک‌اند روی اجرای Serverless پایدار نیست؛ بنابراین برای نسخهٔ چندکاربره و رسمی باید پایگاه‌دادهٔ ابری PostgreSQL (مانند Neon یا Supabase)، ورود امن مدیرگروه و ثبت تاریخچهٔ دائمی اضافه شود. این محدودیت روی کیفیت حل برنامه اثر ندارد، اما روی ماندگاری و اشتراک داده میان دستگاه‌ها اثر دارد.
