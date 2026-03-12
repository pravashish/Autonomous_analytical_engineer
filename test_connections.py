"""
test_connections.py — run this once to verify both connections work.
Delete after testing.

Usage:
    .venv/Scripts/python test_connections.py
"""

print("=" * 50)
print("Testing connections...")
print("=" * 50)

# ── Test 1: Ollama ─────────────────────────────────
print("\n[1/2] Ollama...")
try:
    from openai import OpenAI
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    resp = client.chat.completions.create(
        model      = "qwen2.5-coder:7b",
        max_tokens = 20,
        messages   = [{"role": "user", "content": "Say OK"}],
    )
    print(f"  ✅ Ollama OK — model replied: {resp.choices[0].message.content.strip()}")
except Exception as e:
    print(f"  ❌ Ollama FAILED: {e}")
    print("     → Is Ollama running? Try: ollama serve")

# ── Test 2: Snowflake ──────────────────────────────
print("\n[2/2] Snowflake...")
try:
    from dotenv import load_dotenv
    import os, snowflake.connector
    load_dotenv()

    conn = snowflake.connector.connect(
        account   = os.getenv("SNOWFLAKE_ACCOUNT"),
        user      = os.getenv("SNOWFLAKE_USER"),
        password  = os.getenv("SNOWFLAKE_PASSWORD"),
        role      = os.getenv("SNOWFLAKE_ROLE",      "ACCOUNTADMIN"),
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database  = os.getenv("SNOWFLAKE_DATABASE",  "ANALYTICS_DEMO"),
        schema    = os.getenv("SNOWFLAKE_SCHEMA",    "MARTS"),
    )
    cur = conn.cursor()
    cur.execute("SELECT CURRENT_USER(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
    user, db, schema = cur.fetchone()
    print(f"  ✅ Snowflake OK")
    print(f"     User:     {user}")
    print(f"     Database: {db}")
    print(f"     Schema:   {schema}")

    cur.execute("SELECT COUNT(*) FROM ARR_PROGRAM_FACT")
    count = cur.fetchone()[0]
    print(f"     ARR rows: {count}")
    conn.close()
except Exception as e:
    print(f"  ❌ Snowflake FAILED: {e}")
    print("     → Check your .env file values")

print("\n" + "=" * 50)
print("Done. Fix any ❌ before running the app.")
print("=" * 50)
