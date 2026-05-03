# Railway: My Book Stacks

Postgres is provisioned on the **production** environment. After adding Postgres, GitHub-backed app services may exist on the project but not be attached to **production** yet.

## 1. Attach app services to production (if needed)

Dashboard: **My Book Stacks** → **production** → **Sync** (or add `librarian` + `librarianAPI` to this environment). Deploy staged changes.

## 2. Rename services (dashboard only)

- `librarian` → **MyBookStacks**
- `librarianAPI` → **MyBookStacksBackend**

## 3. CLI link

```powershell
railway project list --json   # copy project / environment / service IDs

cd path\to\librarian
railway link -p <PROJECT_ID> -e <ENVIRONMENT_ID> -s <frontend-service-id>
railway service link MyBookStacks

cd path\to\librarianAPI
railway link -p <PROJECT_ID> -e <ENVIRONMENT_ID> -s <backend-service-id>
railway service link MyBookStacksBackend
```

If `railway add --repo ...` returns **Unauthorized**, reconnect GitHub under **Railway → Account → Connections** and grant the Railway GitHub app access to both repos.

## 4. Variables (reference)

**Backend:** `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (Postgres service must be named **Postgres**.)

**Frontend:** `API_BASE_URL` (HTTPS backend origin, no trailing slash), `CLOUDINARY_NAME`, `CLOUDINARY_UPLOAD_PRESET`. Redeploy frontend after changing `API_BASE_URL`.

## 5. Database copy (Heroku → Railway)

Install PostgreSQL client tools (`pg_dump` / `pg_restore`) on your machine, then from **librarianAPI** with Railway linked to the **Postgres** service:

```powershell
.\scripts\heroku-to-railway-db.ps1 -HerokuApp librarianapi
```

If `heroku pg:backups:*` fails with DNS errors, run the same script from your own network (or retry later). See `C:\Users\ajonz\Coding\docs\heroku-to-railway-migration-playbook.md` §8.

```powershell
railway link -p <PROJECT_ID> -e <ENV_ID> -s Postgres
railway variables --json   # use DATABASE_PUBLIC_URL for pg_restore + ?sslmode=require
```

**Heroku apps are intentionally left running** after cutover; redo a dump/restore if you need to refresh Railway data.
