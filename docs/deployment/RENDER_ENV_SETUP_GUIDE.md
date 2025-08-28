# 📋 HOW TO ADD ENVIRONMENT VARIABLES TO RENDER

## 🎯 **STEP-BY-STEP RENDER CONFIGURATION**

### **Step 1: Access Your Service**
1. Log into your Render dashboard
2. Navigate to your Django service
3. Click on the **"Settings"** tab

### **Step 2: Environment Variables Section**
1. Scroll down to **"Environment Variables"**
2. Click **"Add Environment Variable"** for each variable below

### **Step 3: Add These Variables One by One**

Copy and paste each variable exactly as shown:

#### **🔧 CORE CONFIGURATION**
```
Key: DJANGO_SETTINGS_MODULE
Value: inventory_app.settings_production

Key: DEBUG
Value: False
```

#### **🔗 DATABASE**
```
Key: DATABASE_URL
Value: postgresql://postgres.xuzylmblpkncyztcjrhh:B0t3co1027.@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

#### **🏠 HOSTS & SECURITY**
```
Key: DJANGO_ALLOWED_HOSTS
Value: .onrender.com,localhost,127.0.0.1

Key: DJANGO_SECRET_KEY
Value: 849b052a49e2110ca225ae04ffaf57ec9f71f5cdefb5b7150127b342e1d076e9
```

#### **🔐 SSL/HTTPS CONFIGURATION**
```
Key: DJANGO_SECURE_SSL_REDIRECT
Value: True

Key: DJANGO_SECURE_HSTS_SECONDS
Value: 31536000

Key: DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS
Value: True

Key: DJANGO_SECURE_HSTS_PRELOAD
Value: True
```

#### **🛡️ SECURITY HEADERS**
```
Key: DJANGO_SECURE_CONTENT_TYPE_NOSNIFF
Value: True

Key: DJANGO_SECURE_BROWSER_XSS_FILTER
Value: True

Key: DJANGO_SECURE_REFERRER_POLICY
Value: strict-origin-when-cross-origin
```

#### **🍪 COOKIE SECURITY**
```
Key: DJANGO_SESSION_COOKIE_SECURE
Value: True

Key: DJANGO_CSRF_COOKIE_SECURE
Value: True
```

#### **📊 SUPABASE INTEGRATION**
```
Key: SUPABASE_URL
Value: https://xuzylmblpkncyztcjrhh.supabase.co

Key: SUPABASE_KEY
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1enlsbWJscGtuY3l6dGNqcmhoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDc5NDkxNSwiZXhwIjoyMDYwMzcwOTE1fQ.qOeTKh3s_Rota_ZhCM1H7CLJIPIHstb3oZszl4LSnEA
```

### **Step 4: Remove Conflicting Variables**
If you have these variables, **DELETE** them:
- `APP_ENV=staging` (conflicts with production settings)
- `DEBUG=FALSE` (replace with `DEBUG=False`)
- `DJANGO_SECURE_SSL_REDIRECT=TRUE` (replace with `True`)

### **Step 5: Save and Deploy**
1. Click **"Save"** after adding all variables
2. Render will automatically trigger a new deployment
3. Monitor the deployment logs for any issues

---

## ⚠️ **IMPORTANT NOTES**

### **Case Sensitivity:**
- Use `True` and `False` (not `TRUE`/`FALSE`)
- Environment variable names are case-sensitive

### **Security:**
- Never commit `.env` files with real credentials to Git
- Your `DJANGO_SECRET_KEY` should remain private
- Supabase keys should be kept secure

### **Testing:**
- After deployment, test your app thoroughly
- Check that HTTPS redirects work properly
- Verify that all features function correctly

---

## 🚀 **QUICK COPY-PASTE FORMAT**

For faster setup, here's a format you can copy section by section:

```bash
DJANGO_SETTINGS_MODULE=inventory_app.settings_production
DEBUG=False
DATABASE_URL=postgresql://postgres.xuzylmblpkncyztcjrhh:B0t3co1027.@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
DJANGO_ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
DJANGO_SECRET_KEY=849b052a49e2110ca225ae04ffaf57ec9f71f5cdefb5b7150127b342e1d076e9
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
DJANGO_SECURE_CONTENT_TYPE_NOSNIFF=True
DJANGO_SECURE_BROWSER_XSS_FILTER=True
DJANGO_SECURE_REFERRER_POLICY=strict-origin-when-cross-origin
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
SUPABASE_URL=https://xuzylmblpkncyztcjrhh.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1enlsbWJscGtuY3l6dGNqcmhoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDc5NDkxNSwiZXhwIjoyMDYwMzcwOTE1fQ.qOeTKh3s_Rota_ZhCM1H7CLJIPIHstb3oZszl4LSnEA
```

**✅ Ready for production deployment!**
