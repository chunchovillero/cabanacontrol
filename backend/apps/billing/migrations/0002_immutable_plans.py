from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]
    operations = [
        migrations.RunSQL(
            sql="""
        CREATE FUNCTION billing_protect_plan_version() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Las versiones de planes son inmutables'
                USING ERRCODE = '23514';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER billing_plan_immutable
        BEFORE UPDATE OR DELETE ON billing_subscriptionplan
        FOR EACH ROW EXECUTE FUNCTION billing_protect_plan_version();
        """,
            reverse_sql="""
        DROP TRIGGER billing_plan_immutable ON billing_subscriptionplan;
        DROP FUNCTION billing_protect_plan_version();
        """,
        )
    ]
