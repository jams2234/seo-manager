from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seo_analyzer', '0004_alter_pagegroup_options_pagegroup_order_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE seo_page_group_categories
            MODIFY icon VARCHAR(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """,
            reverse_sql="""
            ALTER TABLE seo_page_group_categories
            MODIFY icon VARCHAR(10) CHARACTER SET utf8 COLLATE utf8_general_ci;
            """
        ),
    ]
