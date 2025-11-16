# Quick Fix: ChromaDB "Cannot Open Header File"

**Problem:** Knowledge base uploads failing with "Cannot open header file"
**Cause:** Embedding dimension mismatch after database migration
**Status:** Fix ready to deploy

---

## Quick Deploy (AWS Lightsail)

```bash
# 1. SSH to AWS
ssh ubuntu@35.175.156.231
cd /home/ubuntu/presgen/sales-agent-labs

# 2. Copy files from local (run on your Mac)
scp fix_chromadb_dimensions.py run_chromadb_fix.sh \
    ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/

scp presgen-assess/src/service/chromadb_schema.py \
    ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/presgen-assess/src/service/

scp presgen-assess/src/models/certification.py \
    ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/presgen-assess/src/models/

scp presgen-assess/alembic/versions/add_embedding_dimension.py \
    ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/presgen-assess/alembic/versions/

# 3. Run automated fix (back on AWS)
chmod +x run_chromadb_fix.sh
bash run_chromadb_fix.sh
```

---

## Manual Steps (if automated script fails)

```bash
# On AWS server
cd /home/ubuntu/presgen/sales-agent-labs

# 1. Copy script to container
docker cp fix_chromadb_dimensions.py presgen-assess:/app/

# 2. Run diagnostic
docker exec presgen-assess python3 /app/fix_chromadb_dimensions.py

# 3. Check OpenAI API key
docker exec presgen-assess printenv OPENAI_API_KEY

# If missing, add to .env:
nano presgen-assess/.env
# Add: OPENAI_API_KEY=sk-proj-...
docker-compose restart presgen-assess

# 4. Run database migration
docker exec presgen-assess alembic upgrade head

# 5. Run automated fix
docker exec -it presgen-assess python3 /app/fix_chromadb_dimensions.py --auto-fix

# 6. Rebuild and restart
docker-compose build presgen-assess
docker-compose up -d
```

---

## Verify Fix

```bash
# 1. Check container health
docker-compose ps

# 2. Test upload via UI
open http://35.175.156.231

# 3. Monitor logs
docker-compose logs -f presgen-assess | grep -E "✅|❌"

# 4. Check database
docker exec presgen-assess python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/presgen_assess.db')
cursor = conn.execute('''
    SELECT original_filename, processing_status, chunk_count, embedding_dimension
    FROM knowledge_base_documents
    ORDER BY created_at DESC
    LIMIT 5
''')
print('Recent uploads:')
for row in cursor:
    print(f'{row[0]:<40} {row[1]:<15} chunks={row[2]:<5} dim={row[3]}')
"
```

**Expected:** Status = `completed`, chunks > 0, dimension = `1536`

---

## What This Fix Does

1. ✅ Validates OpenAI API key is configured
2. ✅ Backs up database (timestamped - rollback safety)
3. ✅ Resets ChromaDB vector data (clean slate with correct dimensions)
4. ✅ **PRESERVES document records** - keeps all metadata, files on disk
5. ✅ Resets status to 'pending' - triggers automatic re-processing
6. ✅ Adds embedding dimension tracking to schema
7. ✅ Enhances error messages for future issues

**Your data is safe:** All document files and database records are preserved. Only the vector embeddings are reset to be regenerated with the correct dimensions.

---

## Files Modified

- `fix_chromadb_dimensions.py` - Diagnostic & fix script
- `run_chromadb_fix.sh` - Automated deployment
- `chromadb_schema.py` - Enhanced error handling
- `certification.py` - Added embedding_dimension column
- `add_embedding_dimension.py` - Database migration

Full documentation: [CHROMADB_DIMENSION_FIX_SUMMARY.md](CHROMADB_DIMENSION_FIX_SUMMARY.md)

---

## Troubleshooting

**Issue:** "OPENAI_API_KEY not set"
**Fix:** Add to `presgen-assess/.env`, restart container

**Issue:** "Database file does not exist"
**Fix:** Run script inside container: `docker exec -it presgen-assess python3 /app/fix_chromadb_dimensions.py`

**Issue:** Still getting "Cannot open header file"
**Fix:** Run full diagnostic, check logs for dimension values

**Issue:** Migration fails
**Fix:** May be already applied, safe to ignore

---

## Support

For detailed technical explanation and MLOps best practices, see:
[CHROMADB_DIMENSION_FIX_SUMMARY.md](CHROMADB_DIMENSION_FIX_SUMMARY.md)
