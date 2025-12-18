# Database Folder

The `databases/` folder contains all database migrations, schema definitions, and related database artifacts.

## Purpose

This folder serves as the central repository for:

- **Schema Definitions**: Table structures, column definitions, and constraints
- **Migrations**: Version-controlled database changes using Flyway or similar tools
- **Views**: SQL views for data aggregation and simplified querying
- **Stored Procedures**: Reusable database logic and business rules
- **Functions**: Custom SQL functions for data transformation
- **Streams**: Change Data Capture (CDC) streams for tracking data modifications
- **Stages**: External storage stages (S3, Azure Blob, GCS) for data loading/unloading
- **Sequences**: Auto-increment sequences and ID generators
- **Indexes**: Performance optimization indexes and keys
- **Policies**: Row-level security and access control policies
- **Initial Data**: Seed data and reference data scripts

## Organization

```
databases/
├── README.md                           # This file
├── migrations/
│   ├── V001__initial_schema.sql        # Versioned migrations (V prefix)
│   ├── V002__create_tables.sql
│   ├── V003__add_indexes.sql
│   └── R__refresh_views.sql            # Repeatable migrations (R prefix)
├── schemas/
│   ├── main/
│   │   ├── tables.sql
│   │   ├── views.sql
│   │   └── procedures.sql
│   └── staging/
│       ├── tables.sql
│       └── streams.sql
├── stages/
│   └── external_stages.sql
├── seed_data/
│   └── reference_data.sql
└── docs/
    └── schema_diagram.md
```

## Migration Naming Convention

- **Versioned**: `V###__description.sql` (executed once in order)
  - Example: `V001__create_users_table.sql`
- **Repeatable**: `R__description.sql` (re-executed on every run if changed)
  - Example: `R__refresh_materialized_views.sql`

## Best Practices

- **One logical change per file**: Keep migrations focused and atomic
- **Idempotent scripts**: Use `CREATE IF NOT EXISTS`, `DROP IF EXISTS` where appropriate
- **Documentation**: Add comments explaining complex schema changes
- **Version control**: Commit all migrations; never modify committed files
- **Testing**: Test migrations in lower environments (DEV, QA) before PROD
- **Rollback strategy**: Design migrations to be reversible when possible
- **Naming clarity**: Use descriptive names that indicate the change purpose
- **No manual changes**: All database changes must go through migrations

## Running Migrations

### Using Flyway with Docker

```bash
# Dev environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Prod environment
docker compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### Manual Execution

```sql
-- Connect to your database and execute migration files in order
-- Ensure version tracking table is created first (usually handled by migration tool)
```

## Example Migration Files

### Create Table
```sql
-- V001__create_users_table.sql
CREATE TABLE IF NOT EXISTS users (
  user_id INT PRIMARY KEY AUTO_INCREMENT,
  username STRING UNIQUE NOT NULL,
  email STRING NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Create View
```sql
-- R__user_summary_view.sql
CREATE OR REPLACE VIEW user_summary AS
SELECT user_id, username, email, created_at
FROM users
WHERE deleted_at IS NULL;
```

### Create Stream (CDC)
```sql
-- V002__create_user_changes_stream.sql
CREATE STREAM IF NOT EXISTS user_changes ON TABLE users;
```

### Create Stage (External)
```sql
-- V003__create_s3_stage.sql
CREATE STAGE IF NOT EXISTS s3_data_stage
  URL = 's3://my-bucket/data/'
  CREDENTIALS = (AWS_KEY_ID = '***' AWS_SECRET_KEY = '***');
```

## Common Operations

### View Migration History
Most migration tools provide a history table. Query it to see applied migrations:

```sql
SELECT * FROM flyway_schema_history ORDER BY installed_rank DESC;
```

### Validate Migrations
Always validate schema after migrations:

```sql
SHOW TABLES;
DESCRIBE table_name;
SHOW VIEWS;
```

## Troubleshooting

- **Migration failed**: Check logs for SQL syntax errors; fix and re-run
- **Version mismatch**: Ensure migration files are in correct order and named properly
- **Permission issues**: Verify database user has CREATE/ALTER/DROP privileges
- **Rollback needed**: Use repeatable migrations (`R__`) or create explicit rollback scripts

## References

- [Flyway Documentation](https://flywaydb.org/documentation/)
- [Database Best Practices](../docs/DATABASE.md)
- [Schema Diagram](./docs/schema_diagram.md)