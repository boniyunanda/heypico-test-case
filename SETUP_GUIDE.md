# Setup Guide - Google Maps API Key & Deployment

## Step 1: Get Google Maps API Key

### 1.1 Create Google Cloud Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Accept the terms and create a new project

### 1.2 Enable Required APIs
1. In the Google Cloud Console, go to **APIs & Services > Library**
2. Enable these APIs:
   - **Maps JavaScript API**
   - **Places API** 
   - **Directions API**
   - **Geocoding API**

### 1.3 Create API Key
1. Go to **APIs & Services > Credentials**
2. Click **+ CREATE CREDENTIALS > API Key**
3. Copy the API key (you'll need this for the .env file)

### 1.4 Secure Your API Key (IMPORTANT!)
1. Click on your API key to edit it
2. Under **Application restrictions**:
   - Select "HTTP referrers (web sites)"
   - Add: `http://localhost:3000/*` and `https://yourdomain.com/*`
3. Under **API restrictions**:
   - Select "Restrict key"
   - Choose the 4 APIs you enabled above
4. Click **SAVE**

## Step 2: Configure Environment

### 2.1 Create .env File
```bash
# Copy the template
copy env.example .env

# Edit .env file and replace with your actual values:
GOOGLE_MAPS_API_KEY=your-actual-api-key-from-step-1.3
WEBUI_SECRET_KEY=your-random-secret-key-here
```

### 2.2 Generate Secure Keys
You can generate secure keys using:

**For WEBUI_SECRET_KEY:**
```bash
# PowerShell
[System.Web.Security.Membership]::GeneratePassword(32, 0)

# Or online: https://www.random.org/passwords/
```

**For ENCRYPTION_KEY:**
```python
# Python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## Step 3: Deploy the Application

### 3.1 Prerequisites Check
- ✅ Docker Desktop installed and running
- ✅ 8GB+ RAM available
- ✅ Google Maps API key obtained
- ✅ .env file configured

### 3.2 Start the Application
```bash
# Navigate to project directory
cd local-llm-maps

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f open-webui
```

### 3.3 Wait for Services
The first startup takes 5-10 minutes because:
- Ollama downloads the Llama 3 model (~4GB)
- Open WebUI initializes the database
- All services need to start and connect

### 3.4 Access the Application
- **Main App**: http://localhost:3000
- **Grafana Monitoring**: http://localhost:3001 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090

## Step 4: Test the Integration

### 4.1 First Login
1. Open http://localhost:3000
2. Create a new account (first user becomes admin)
3. Wait for the LLM model to finish loading

### 4.2 Test Google Maps Integration
Try these example queries:
- "Find coffee shops near Times Square, New York"
- "Show me restaurants within 2 miles of Central Park"
- "Get directions from Brooklyn Bridge to Statue of Liberty"
- "Where is the nearest gas station to JFK Airport?"

### 4.3 Verify Map Display
You should see:
- ✅ Interactive Google Map embedded in chat
- ✅ Markers for found places
- ✅ Clickable info windows with details
- ✅ "Open in Google Maps" links

## Step 5: Troubleshooting

### Common Issues

**"Google Maps API error"**
- Check API key is correct in .env file
- Verify all 4 APIs are enabled in Google Cloud
- Check API key restrictions allow localhost:3000

**"Map not loading"**
- Check browser console for JavaScript errors
- Verify GOOGLE_MAPS_API_KEY is set correctly
- Ensure Maps JavaScript API is enabled

**"LLM not responding"**
- Check Docker logs: `docker-compose logs ollama`
- Verify model download completed
- Restart if needed: `docker-compose restart open-webui`

**"Services not starting"**
- Check Docker is running
- Verify ports 3000, 3001, 6379, 9090 are available
- Check system resources (8GB+ RAM recommended)

### Useful Commands
```bash
# View all logs
docker-compose logs -f

# Restart specific service
docker-compose restart open-webui

# Stop all services
docker-compose down

# Clean restart
docker-compose down -v && docker-compose up -d

# Check service health
docker-compose ps
```

## Step 6: Production Deployment (Optional)

For production deployment:

### 6.1 Security Hardening
- Use strong, unique passwords
- Enable HTTPS with SSL certificates
- Restrict API keys to production domains
- Set up firewall rules

### 6.2 Monitoring Setup
- Configure Grafana alerts
- Set up log aggregation
- Monitor API usage and costs
- Set up backup procedures

### 6.3 Scaling Considerations
- Use Docker Swarm or Kubernetes
- Set up load balancing
- Configure Redis clustering
- Implement CDN for static assets

## 🎉 Success!

Once everything is running, you'll have:
- ✅ Local LLM (Llama 3) running privately
- ✅ Google Maps integration with interactive maps
- ✅ Real-time chat interface
- ✅ Monitoring and metrics
- ✅ Production-ready architecture

The system demonstrates enterprise-level implementation with proper security, monitoring, and scalability considerations.

---

**Need help?** Check the logs with `docker-compose logs -f` or create an issue with your specific error message.
