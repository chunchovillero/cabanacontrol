from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("billing", "0004_checkoutattempt_saascharge_planprice_and_more")]
    operations = [
        migrations.RunSQL(
            sql="""
        CREATE TRIGGER billing_price_immutable
        BEFORE UPDATE OR DELETE ON billing_planprice
        FOR EACH ROW EXECUTE FUNCTION billing_protect_plan_version();
        """,
            reverse_sql="DROP TRIGGER billing_price_immutable ON billing_planprice;",
        )
    ]
