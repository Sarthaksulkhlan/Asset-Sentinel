# Setup

1. Configure `.env` from `.env.example`.
2. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

3. Apply database schema and migrations:

```powershell
psql -d asset_sentinel -f database/schemas/schema.sql
psql -d asset_sentinel -f database/migrations/enterprise_migration.sql
psql -d asset_sentinel -f database/migrations/auth_login_activity_migration.sql
psql -d asset_sentinel -f database/migrations/enterprise_registration_migration.sql
```

4. Start the backend:

```powershell
python backend/main.py
```

5. Start the frontend:

```powershell
cd frontend
npm run dev
```

