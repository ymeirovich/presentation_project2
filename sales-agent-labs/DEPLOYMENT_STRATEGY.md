# PresGen Deployment Strategy - Updated

**Date:** October 29, 2025
**Status:** Modified due to UI build issues

---

## 🎯 Situation

**What's Working:**
- ✅ AWS configured and ready
- ✅ Google auth files prepared
- ✅ Docker Desktop installed
- ✅ presgen-core Dockerfile ready
- ✅ presgen-assess Dockerfile ready
- ✅ Deployment scripts created

**Current Issue:**
- ❌ presgen-ui build fails with:
  - lightningcss architecture mismatch (linux-arm64-musl)
  - Missing @/lib/mock-file-storage module

---

## 📋 Three Deployment Options

### Option 1: Deploy Backend Only (RECOMMENDED)

Deploy just the Core and Assess APIs to AWS. Skip the UI for now.

**Pros:**
- ✅ Deploy immediately (no UI build issues)
- ✅ Core functionality working (API endpoints)
- ✅ Can test with curl/Postman
- ✅ Fix UI issues separately

**Cons:**
- ⚠️ No web interface (API only)
- ⚠️ Need alternative way to test (curl commands)

**Time:** 30 minutes

**Command:**
```bash
# Modify docker-compose to skip UI
docker-compose up -d presgen-core presgen-assess redis

# Or deploy to AWS without UI
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0
# Then SSH in and comment out presgen-ui and nginx from docker-compose
```

---

### Option 2: Fix UI Issues Then Deploy (THOROUGH)

Fix the Next.js build issues before deploying.

**Required Fixes:**

1. **Create missing mock file:**
```bash
# Create presgen-ui/src/lib/mock-file-storage.ts
cat > presgen-ui/src/lib/mock-file-storage.ts << 'EOF'
// Mock file storage for testing
export class MockFileStorage {
  async upload(file: File) {
    return { url: '/mock/file.txt', id: 'mock-id' };
  }
}
EOF
```

2. **Fix lightningcss issue:**
```bash
# Option A: Add platform-specific build
# In presgen-ui/Dockerfile, add before npm ci:
RUN apk add --no-cache python3 make g++

# Option B: Use different CSS processor
# In presgen-ui/package.json, remove lightningcss dependency
```

3. **Rebuild:**
```bash
docker-compose build presgen-ui
```

**Time:** 1-2 hours (debugging and testing)

---

### Option 3: Use Existing Running UI (FASTEST)

If you have the UI running locally on your Mac, keep using that for demos.

**Setup:**
1. Deploy backend to AWS
2. Keep UI running on your Mac
3. Configure UI to point to AWS backend APIs

**Changes needed in presgen-ui/.env:**
```bash
NEXT_PUBLIC_PRESGEN_ASSESS_URL=http://YOUR_AWS_IP:8000
NEXT_PUBLIC_PRESGEN_CORE_URL=http://YOUR_AWS_IP:8080
```

**Pros:**
- ✅ No Docker build issues
- ✅ Can use Mac's development UI
- ✅ Backend scales on AWS
- ✅ Deploy today

**Cons:**
- ⚠️ UI only works from your Mac
- ⚠️ Can't share URL with others

**Time:** 20 minutes

---

## 🚀 My Recommendation: Option 1 + Fix UI Later

**Phase 1: Deploy Backend Now (30 minutes)**

```bash
# 1. Temporarily disable UI in docker-compose
# Comment out presgen-ui and nginx sections

# 2. Deploy to AWS
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0

# 3. Test APIs directly
curl http://YOUR_IP:8080/health
curl http://YOUR_IP:8000/health
```

**Phase 2: Fix UI Issues (Later)**

```bash
# 1. Create missing mock file
mkdir -p presgen-ui/src/lib
cat > presgen-ui/src/lib/mock-file-storage.ts << 'EOF'
export class MockFileStorage {
  async upload(file: File) {
    return { url: '/mock/file.txt', id: 'mock-id' };
  }
  async delete(id: string) {
    return true;
  }
  async get(id: string) {
    return null;
  }
}
EOF

# 2. Update Dockerfile to install build dependencies
# Already done - npm ci instead of npm ci --only=production

# 3. Try building again
docker-compose build presgen-ui

# 4. If successful, redeploy
ssh -i lightsail-key.pem ubuntu@YOUR_IP
cd /home/ubuntu/presgen
git pull  # or scp updated files
docker-compose up -d presgen-ui nginx
```

---

## 🔧 Quick Fixes to Try Now

### Fix 1: Create Mock File

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

mkdir -p presgen-ui/src/lib

cat > presgen-ui/src/lib/mock-file-storage.ts << 'EOF'
/**
 * Mock file storage for testing
 * This is a placeholder for the test route
 */

export interface FileUploadResult {
  url: string;
  id: string;
  name?: string;
  size?: number;
}

export class MockFileStorage {
  private files: Map<string, FileUploadResult> = new Map();

  async upload(file: File): Promise<FileUploadResult> {
    const id = `mock-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const result: FileUploadResult = {
      url: `/mock/files/${id}`,
      id,
      name: file.name,
      size: file.size
    };
    this.files.set(id, result);
    return result;
  }

  async delete(id: string): Promise<boolean> {
    return this.files.delete(id);
  }

  async get(id: string): Promise<FileUploadResult | null> {
    return this.files.get(id) || null;
  }

  async list(): Promise<FileUploadResult[]> {
    return Array.from(this.files.values());
  }
}

// Export singleton instance
export const mockFileStorage = new MockFileStorage();
EOF

echo "✅ Mock file created"
```

### Fix 2: Try Building UI Again

```bash
# Make sure Docker Desktop is running
docker ps

# Build just the UI
docker-compose build presgen-ui

# Check if it works
docker-compose up presgen-ui
```

---

## 🎯 Decision Time

**What do you want to do?**

### A. Deploy Backend Only NOW
- Skip UI issues
- Get backend running on AWS
- Fix UI later
- **Time:** 30 minutes

### B. Fix UI Issues First
- Create mock file
- Rebuild UI
- Deploy complete stack
- **Time:** 1-2 hours

### C. Skip Docker Completely
- Deploy directly without Docker
- Run services as systemd services
- Simpler but less portable
- **Time:** 45 minutes

---

## 📞 Next Steps

**Tell me which option you prefer, and I'll:**

1. Create the necessary files/fixes
2. Provide exact commands to run
3. Guide you through the deployment
4. Help troubleshoot any issues

**My recommendation:**
- **Try Fix 1 (create mock file) first** → takes 30 seconds
- **Try building UI again** → if it works, great!
- **If still fails, go with Option A** → deploy backend only

---

**Ready to proceed? Choose A, B, or C, or let me try the quick fixes first!**
