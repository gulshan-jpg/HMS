import sqlite3

def export():
    conn = sqlite3.connect('hotel_pms.db')
    cursor = conn.cursor()

    tables = [
        'organizations',
        'users',
        'user_org_memberships',
        'room_types',
        'cancellation_policies',
        'tax_rates',
        'rate_plans',
        'rooms',
        'business_dates',
        'booking_groups',
        'group_blocks',
        'guests',
        'reservations',
        'folios',
        'folio_items',
        'payments',
        'housekeeping_tasks',
        'rate_overrides',
        'daily_snapshots',
        'email_templates',
        'activity_logs'
    ]

    sql_statements = []

    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns_info = cursor.fetchall()
        col_names = [col[1] for col in columns_info]
        col_types = {col[1]: col[2].upper() for col in columns_info}
        
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        if not rows:
            continue
            
        for row in rows:
            vals = []
            for val, col in zip(row, col_names):
                if val is None:
                    vals.append("NULL")
                elif isinstance(val, (int, float)):
                    if "BOOLEAN" in col_types[col]:
                        vals.append("TRUE" if val else "FALSE")
                    else:
                        vals.append(str(val))
                elif isinstance(val, bool):
                    vals.append("TRUE" if val else "FALSE")
                else:
                    s = str(val).replace("'", "''")
                    vals.append(f"'{s}'")
            
            cols_str = ', '.join([f'"{c}"' for c in col_names])
            vals_str = ', '.join(vals)
            sql_statements.append(f'INSERT INTO public."{table}" ({cols_str}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;')

    with open('seed_supabase.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_statements))

    print(f"Generated {len(sql_statements)} statements in seed_supabase.sql")
    conn.close()

if __name__ == '__main__':
    export()
