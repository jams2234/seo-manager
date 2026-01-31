# Generated manually on 2026-01-27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("CoinGryComm", "0016_backfill_order_source_for_existing_auto_orders"),
    ]

    operations = [
        migrations.DeleteModel(
            name="P2POTCOrder",
        ),
    ]
