# SEO Analyzer - Quick Start Guide

## 📋 Current Status

### ✅ Completed
- ✅ **Phase 1:** Environment setup complete
  - Node.js 18.20.8 installed
  - Redis 6.0.16 installed
  - Python packages installed
  - Django app `seo_analyzer` created
  - Celery configured

- ✅ **Phase 2 (Partial):** Backend models
  - 7 database models created and migrated
  - Django Admin configured (for internal use)
  - Models: Domain, Page, SEOMetrics, AnalyticsData, HistoricalMetrics, APIQuotaUsage, ScanJob

- ✅ **Phase 3:** React Frontend **COMPLETE**
  - All components implemented
  - Routing configured
  - State management with Zustand
  - API service layer ready
  - Compiles successfully

### ⏳ Remaining Work
See [TODO_BACKEND.md](TODO_BACKEND.md) for detailed backend tasks:
- REST API endpoints (Serializers, ViewSets, URLs)
- Google API services (PageSpeed, Search Console, Analytics)
- Celery background tasks
- Domain scanner service

---

## 🚀 Quick Start Commands

### 1. Start React Development Server
```bash
cd /root/telegram_bot/frontend
npm start
```
Opens at: http://localhost:3000

### 2. Start Django Development Server
```bash
cd /root/telegram_bot
python3 manage.py runserver 0.0.0.0:8000
```
API will be at: http://localhost:8000/api/v1/

### 3. Start Redis (for Celery)
```bash
sudo systemctl start redis-server
sudo systemctl status redis-server
```

### 4. Start Celery Worker (when needed)
```bash
cd /root/telegram_bot
celery -A telegram_bot worker -l info
```

### 5. Start Celery Beat Scheduler (when needed)
```bash
cd /root/telegram_bot
celery -A telegram_bot beat -l info
```

---

## 📁 Project Structure

```
/root/telegram_bot/
├── seo_analyzer/              # Django app
│   ├── models.py              ✅ Complete (7 models)
│   ├── admin.py               ✅ Complete
│   ├── views.py               ⏳ TODO
│   ├── serializers.py         ⏳ TODO
│   ├── urls.py                ⏳ TODO
│   ├── tasks.py               ⏳ TODO
│   └── services/              ⏳ TODO
│       ├── google_api_client.py
│       ├── pagespeed_insights.py
│       ├── search_console.py
│       ├── analytics.py
│       ├── domain_scanner.py
│       └── seo_calculator.py
│
├── frontend/                  # React app
│   ├── src/
│   │   ├── components/        ✅ Complete
│   │   ├── pages/             ✅ Complete
│   │   ├── services/          ✅ Complete
│   │   └── store/             ✅ Complete
│   └── package.json           ✅ Complete
│
├── config/
│   └── google_service_account.json  ✅ Ready
│
├── TODO_BACKEND.md            📝 Backend tasks
├── FRONTEND_IMPLEMENTATION.md 📝 Frontend docs
└── QUICK_START.md             📝 This file
```

---

## 🎯 Next Steps

### Option 1: Test Frontend with Mock Data
Create a simple REST API endpoint to test the frontend:

1. Create basic serializers in `seo_analyzer/serializers.py`
2. Create a simple DomainViewSet in `seo_analyzer/views.py`
3. Set up URL routing in `seo_analyzer/urls.py`
4. Add some test data via Django shell
5. Test frontend connection

### Option 2: Continue Backend Implementation
Follow the implementation order in [TODO_BACKEND.md](TODO_BACKEND.md):

1. **REST API First** (enables frontend testing)
   - Serializers
   - ViewSets with basic CRUD
   - URL routing
   - Test with frontend

2. **Google API Services** (real data)
   - PageSpeed Insights
   - Search Console
   - Analytics
   - Domain scanner

3. **Celery Tasks** (background processing)
   - Full scan task
   - Refresh task
   - Nightly updates

4. **Production Deployment**
   - Build React app
   - Configure Nginx
   - Set up systemd services

---

## 🔧 Useful Commands

### Django
```bash
# Create migrations
python3 manage.py makemigrations

# Apply migrations
python3 manage.py migrate

# Create superuser
python3 manage.py createsuperuser

# Django shell (for testing)
python3 manage.py shell

# Run Django server
python3 manage.py runserver 0.0.0.0:8000
```

### React
```bash
# Install dependencies
npm install

# Start dev server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Git (if needed)
```bash
# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "Add frontend implementation"

# Push
git push
```

---

## 📊 Testing the Frontend

### With Mock Data
1. Create a simple Django view that returns mock domain data
2. Start both Django and React servers
3. Open http://localhost:3000
4. Test:
   - Domain list display
   - Add domain form
   - Navigation to analysis page
   - Tree visualization (will need mock tree data)
   - Dashboard metrics

### Expected API Endpoints
The frontend expects these endpoints:

```
GET    /api/v1/domains/                  # List domains
POST   /api/v1/domains/                  # Create domain
GET    /api/v1/domains/{id}/             # Get domain
POST   /api/v1/domains/{id}/scan/        # Trigger scan
POST   /api/v1/domains/{id}/refresh/     # Refresh data
GET    /api/v1/domains/{id}/tree/        # Get tree structure
DELETE /api/v1/domains/{id}/             # Delete domain

GET    /api/v1/pages/                    # List pages
GET    /api/v1/pages/{id}/               # Get page
GET    /api/v1/pages/{id}/metrics/       # Get metrics
GET    /api/v1/pages/{id}/metrics/history/  # Get history
```

---

## 🐛 Common Issues & Solutions

### Issue: React app won't start
**Solution:**
```bash
cd /root/telegram_bot/frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### Issue: Django CORS errors
**Solution:** Ensure CORS settings in `settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```

### Issue: API 404 errors
**Solution:** Check that `seo_analyzer.urls` is included in main `urls.py`:
```python
urlpatterns = [
    path('api/v1/', include('seo_analyzer.urls')),
]
```

### Issue: Celery won't connect to Redis
**Solution:**
```bash
# Start Redis
sudo systemctl start redis-server

# Check Redis is running
redis-cli ping
# Should return: PONG
```

---

## 📝 Documentation Files

1. **[TODO_BACKEND.md](TODO_BACKEND.md)** - Detailed backend tasks
2. **[FRONTEND_IMPLEMENTATION.md](FRONTEND_IMPLEMENTATION.md)** - Frontend documentation
3. **[QUICK_START.md](QUICK_START.md)** - This file
4. **Plan File:** `/root/.claude/plans/snug-wishing-goblet.md` - Original implementation plan

---

## 💡 Tips

1. **Start Simple:** Test frontend with minimal backend API first
2. **Mock Data:** Use Django shell to create test domains/pages
3. **Incremental:** Implement one API endpoint at a time
4. **Test Often:** Run frontend after each backend change
5. **Use Django Admin:** View/edit data at http://localhost:8000/admin

---

## 🎉 Summary

The frontend is **complete and ready**! You can now:
- ✅ View the React app UI (with mock data)
- ✅ Test all components and navigation
- ✅ Understand the expected data structure
- ⏳ Implement backend APIs to power the frontend
- ⏳ Integrate Google APIs for real data
- ⏳ Deploy to production

**Next:** Implement REST API endpoints to connect the frontend to the backend.
