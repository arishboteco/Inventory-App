# Schema Migration Plan - Django Control

## Current State Analysis

- All models have `managed = False`
- 18+ existing migrations (some may be incomplete)
- Supabase schema is the source of truth

## Migration Strategy

### Phase 1: Schema Audit & Documentation

1. **Extract Current Schema**

   ```bash
   pg_dump --schema-only --no-owner DATABASE_URL > current_schema.sql
   ```

2. **Document All Tables**
   - Tables: items, recipes, orders, suppliers, etc.
   - Indexes: Primary keys, foreign keys, unique constraints
   - Data types: Ensure Django field types match exactly

### Phase 2: Django Model Alignment

1. **Update Models** - Change `managed = False` to `managed = True`
2. **Field Verification** - Ensure all fields match DB exactly
3. **Relationship Mapping** - Verify ForeignKey relationships
4. **Custom Field Types** - Handle any Supabase-specific types

### Phase 3: Initial Migration Creation

1. **Clear Migration History** (if needed)
2. **Create Initial Migration** - `python manage.py makemigrations --empty`
3. **Mark as Applied** - `python manage.py migrate --fake-initial`

### Phase 4: Future Changes via Django

1. **Model Changes** - Update models normally
2. **Generate Migrations** - `python manage.py makemigrations`
3. **Apply Migrations** - `python manage.py migrate`

## Benefits

- ✅ Version controlled schema changes
- ✅ Team synchronization
- ✅ Rollback capability
- ✅ Proper constraint management
- ✅ Django admin integration
- ✅ Better testing with test databases

## Risks & Mitigations

- ⚠️ **Data Loss Risk** - Full backup before migration
- ⚠️ **Downtime** - Plan maintenance window
- ⚠️ **Constraint Conflicts** - Audit existing data first
- ⚠️ **Migration Conflicts** - Clean migration history if needed

## Timeline

- **Week 1**: Schema audit and model alignment
- **Week 2**: Test migration in staging environment
- **Week 3**: Production migration with rollback plan
