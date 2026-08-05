# [AGC:FILE] tool=Cc author=fangkun date=2026-08-05
"""
事实数据初始化

创建 fact_account_receivable 表并插入示例数据。
"""

# [AGC:START] tool=Cc author=fangkun
import sqlite3
import logging

logger = logging.getLogger(__name__)


def init_fact_db(db_path: str = "chatbi.db") -> None:
    """
    初始化事实数据表（应收款数据）。

    参数:
        db_path: 数据库路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fact_account_receivable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            city_code TEXT NOT NULL,
            date TEXT NOT NULL,
            balance REAL NOT NULL
        )
    ''')

    cursor.execute("DELETE FROM fact_account_receivable")

    sample_data = [
        ("CUST_SH_001", "021", "2026-07-15", 18234500.00),
        ("CUST_SH_001", "021", "2026-07-20", 12456700.00),
        ("CUST_BJ_002", "010", "2026-07-10", 15678900.00),
        ("CUST_BJ_002", "010", "2026-07-25", 18765400.00),
        ("CUST_GZ_003", "020", "2026-07-05", 12456000.00),
        ("CUST_GZ_003", "020", "2026-07-18", 14567000.00),
        ("CUST_SZ_004", "0755", "2026-07-12", 16789000.00),
        ("CUST_SZ_004", "0755", "2026-07-22", 18923000.00),
        ("CUST_HZ_005", "0571", "2026-07-08", 13456000.00),
        ("CUST_HZ_005", "0571", "2026-07-19", 15678000.00),
    ]

    cursor.executemany(
        "INSERT INTO fact_account_receivable (customer_id, city_code, date, balance) VALUES (?,?,?,?)",
        sample_data
    )

    conn.commit()
    conn.close()
    logger.info(f"事实数据表初始化完成: {db_path}，共 {len(sample_data)} 条记录")
    print("✅ 事实数据表初始化完成。")
# [AGC:END]
