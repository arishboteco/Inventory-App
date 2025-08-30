# 🚀 Render.com Deployment Guide

> **Note:** Placeholder values below. Replace with real credentials in Render's dashboard and never commit live secrets.

## 📋 **STEP-BY-STEP RENDER CONFIGURATION**

### **1. Environment Variables Configuration**

In your Render service dashboard, add these environment variables:

#### **Required Variables:**

```bash
DJANGO_SETTINGS_MODULE=inventory_app.settings_production
DEBUG=False
DJANGO_ALLOWED_HOSTS=<RENDER_DOMAIN>
DJANGO_SECRET_KEY=<DJANGO_SECRET_KEY>
```

#### **Security Variables:**

```bash
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
```

#### **Optional Variables (if needed):**

```bash
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=<EMAIL_HOST_USER>
EMAIL_HOST_PASSWORD=<EMAIL_HOST_PASSWORD>
EMAIL_USE_TLS=True

# Error Tracking (recommended)
SENTRY_DSN=<SENTRY_DSN>
```

### **2. Service Configuration**

#### **Build Command:**

```bash
./build.sh
```

#### **Start Command:**

```bash
gunicorn --bind 0.0.0.0:$PORT --workers 4 --worker-class gevent --worker-connections 1000 --max-requests 1000 --max-requests-jitter 50 --preload --access-logfile - --error-logfile - inventory_app.wsgi:application
```

#### **Health Check Path:**

```
/healthz
```

### **3. Database Configuration**

#### **If using Render PostgreSQL:**

- Create a PostgreSQL database service in Render
- The `DATABASE_URL` will be automatically provided
- Make sure your database is in the same region as your web service

#### **If using external database (Supabase):**

- Set `DATABASE_URL` environment variable to your Supabase connection string
- Format: `postgresql://<DB_USER>:<DB_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>?sslmode=require`

### **4. Domain Configuration**

#### **Custom Domain Setup:**

1. Add your custom domain in Render dashboard
2. Update `DJANGO_ALLOWED_HOSTS` to include your domain:
   ```bash
   DJANGO_ALLOWED_HOSTS=<RENDER_DOMAIN>,yourdomain.com,www.yourdomain.com
   ```
3. Configure DNS records as instructed by Render

### **5. SSL/HTTPS Configuration**

Render automatically provides SSL certificates. Our production settings will:

- ✅ Force HTTPS redirects
- ✅ Set HSTS headers for security
- ✅ Use secure cookies
- ✅ Enable CSP headers

### **6. Static Files**

Static files are handled by WhiteNoise and will be automatically collected during build.

### **7. Performance Settings**

Our production configuration includes:

- ✅ **4 Gunicorn workers** with gevent for async handling
- ✅ **1000 connections per worker** for high concurrency
- ✅ **Request lifecycle management** (1000 requests per worker)
- ✅ **Preloading** for faster response times
- ✅ **Proper logging** to stdout/stderr

---

## 🔧 **RENDER DASHBOARD STEPS**

### **Step 1: Update Your Service**

1. Go to your Render dashboard
2. Select your Django service
3. Go to "Settings" tab

### **Step 2: Update Environment Variables**

1. Scroll to "Environment Variables" section
2. Add all the required variables listed above
3. **Important:** Generate a strong `DJANGO_SECRET_KEY` (50+ characters)

### **Step 3: Update Build & Start Commands**

1. Set **Build Command** to: `./build.sh`
2. Set **Start Command** to the gunicorn command above
3. Set **Health Check Path** to: `/healthz`

### **Step 4: Deploy**

1. Save changes
2. Trigger a new deployment
3. Monitor the build logs for any issues

---

## 🚨 **CRITICAL SECURITY REMINDERS**

### **Before Going Live:**

- [ ] Set `DEBUG=False` (CRITICAL!)
- [ ] Generate a new, secure `DJANGO_SECRET_KEY`
- [ ] Configure proper `DJANGO_ALLOWED_HOSTS`
- [ ] Enable SSL/HTTPS redirects
- [ ] Set up error monitoring (Sentry recommended)

### **Database Security:**

- [ ] Use strong database passwords
- [ ] Enable SSL connections to database
- [ ] Restrict database access to your Render services only

---

## 📊 **MONITORING & MAINTENANCE**

### **Health Checks:**

- Render will automatically check `/healthz` endpoint
- Our production settings include comprehensive health monitoring

### **Logging:**

- Application logs are sent to stdout/stderr
- Monitor logs in Render dashboard
- Consider setting up log aggregation for production

### **Performance Monitoring:**

- Monitor response times in Render dashboard
- Set up alerts for high error rates
- Consider adding APM tools for detailed monitoring

---

## 🐛 **TROUBLESHOOTING**

### **Common Issues:**

#### **Static Files Not Loading:**

- Ensure `python manage.py collectstatic --noinput` runs in build
- Check `STATIC_URL` and `STATIC_ROOT` settings
- Verify WhiteNoise is properly configured

#### **Database Connection Issues:**

- Verify `DATABASE_URL` is correctly set
- Check database is in same region as web service
- Ensure SSL mode is enabled for external databases

#### **502/504 Errors:**

- Check gunicorn workers are starting properly
- Monitor memory usage (upgrade plan if needed)
- Verify health check endpoint is responding

#### **SSL/HTTPS Issues:**

- Ensure custom domain DNS is properly configured
- Check certificate status in Render dashboard
- Verify HSTS settings aren't too aggressive

---

## ✅ **DEPLOYMENT CHECKLIST**

Before deploying to Render:

- [ ] All environment variables configured
- [ ] Build and start commands updated
- [ ] Health check path set to `/healthz`
- [ ] Database connection tested
- [ ] Static files build process working
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate active
- [ ] Error monitoring configured
- [ ] Performance monitoring set up

**🚀 You're ready to deploy!**
