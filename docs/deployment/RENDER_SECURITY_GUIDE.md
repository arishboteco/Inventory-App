# 🔐 SECURE ENVIRONMENT VARIABLES FOR RENDER

> **Note:** Placeholder values only. Replace them with real credentials in your deployment environment—never commit actual secrets.

## ⚠️ SECURITY NOTICE

**NEVER commit files containing real credentials to Git!**

## 📋 HOW TO SECURELY CONFIGURE RENDER

### **Step 1: Use the Template**

1. Copy `.env.render.template`
2. Create a local `.env.render` file (already in `.gitignore`)
3. Replace all placeholder values with your real credentials

### **Step 2: Add to Render Dashboard Only**

**Manually add these variables in Render dashboard:**

#### **🔧 CORE SETTINGS**

```
DJANGO_ENV=production
DEBUG=False
```

#### **🔗 DATABASE**

```
DATABASE_URL=<SUPABASE_DATABASE_URL>
```

#### **🏠 HOSTS & SECURITY**

```
DJANGO_ALLOWED_HOSTS=<RENDER_DOMAIN>,localhost,127.0.0.1
DJANGO_SECRET_KEY=<DJANGO_SECRET_KEY>
```

#### **🔐 SSL/HTTPS**

```
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
```

#### **🛡️ SECURITY HEADERS**

```
DJANGO_SECURE_CONTENT_TYPE_NOSNIFF=True
DJANGO_SECURE_BROWSER_XSS_FILTER=True
DJANGO_SECURE_REFERRER_POLICY=strict-origin-when-cross-origin
```

#### **🍪 COOKIE SECURITY**

```
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
```

#### **📊 SUPABASE**

```
SUPABASE_URL=<SUPABASE_URL>
SUPABASE_KEY=<SUPABASE_SERVICE_ROLE_KEY>
```

## 🔒 SECURITY BEST PRACTICES

### **✅ DO:**

- Add environment variables directly in Render dashboard
- Use `.env.render.template` as a reference
- Generate new secret keys for production
- Keep credentials in secure password managers
- Use different credentials for staging/production

### **❌ DON'T:**

- Commit real credentials to Git
- Share environment files via chat/email
- Use the same secret key across environments
- Store credentials in plaintext files
- Reuse credentials from development

## 🛠️ TOOLS FOR SECURE CREDENTIAL MANAGEMENT

### **Secret Key Generation:**

- Django Secret Key Generator: https://djecrety.ir/
- Random.org: https://www.random.org/passwords/

### **Environment Management:**

- Use Render's built-in environment variable system
- Consider 1Password, Bitwarden, or similar for team credential sharing
- Use separate environments for development/staging/production

## 🚨 IF CREDENTIALS WERE COMPROMISED

If you accidentally committed credentials:

1. **Immediately rotate all credentials:**
   - Generate new Django secret key
   - Reset Supabase database password
   - Regenerate Supabase service keys

2. **Clean Git history:**

   ```bash
   git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env.render*' --prune-empty --tag-name-filter cat -- --all
   ```

3. **Force push cleaned history:**

   ```bash
   git push --force --all
   ```

4. **Update all deployments with new credentials**

## ✅ CURRENT STATUS

- ✅ Sensitive files removed from Git
- ✅ `.gitignore` updated to prevent future commits
- ✅ Secure templates created
- ✅ Step-by-step secure configuration guide provided

**Your repository is now secure!** 🛡️
