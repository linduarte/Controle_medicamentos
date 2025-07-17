from logic.database import fetch_all_medications
from logic.config import get_refill_day
from datetime import datetime, timedelta

DB_PATH = "data/meds.db"
DAYS_THRESHOLD = 30
PRESCRIPTION_ALERT_DAYS = 15

def calculate_days_left(stock, dosage_per_intake):
    if dosage_per_intake == 0:
        return float('inf')
    return stock / dosage_per_intake

def prescription_expires_soon(expiry_str, threshold_days=15):
    try:
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        days_left = (expiry - datetime.today().date()).days
        return days_left < threshold_days, days_left
    except ValueError:
        return False, None

def calculate_next_refill_date(refill_base):
    today = datetime.today().date()
    while refill_base < today:
        refill_base += timedelta(days=30)
    return refill_base

def check_medications():
    print("\n=== 💊 Status dos Medicamentos ===\n")

    # Carrega data base de compra
    refill_base = get_refill_day()
    next_refill = calculate_next_refill_date(refill_base)
    days_until_refill = (next_refill - datetime.today().date()).days

    print(f"🗓️  Próxima compra: {next_refill} (em {days_until_refill} dias)\n")

    meds = fetch_all_medications(DB_PATH)

    if not meds:
        print("Nenhum medicamento registrado.")
        return

    for med in meds:
        name = med["name"]
        stock = med["stock_in_units"]
        dosage = med["dosage_per_intake"]
        expiry_str = med["prescription_expiry"]

        print(f"🔹 {name} (Dose: {dosage}, Estoque: {stock})")

        # Estoque
        days_left = calculate_days_left(stock, dosage)
        if days_left < days_until_refill:
            print(f"  ❗ Repor antes do próximo ciclo (dura apenas {days_left:.1f} dias)")  # noqa: E501
        else:
            print(f"  ✅ Estoque cobre até o próximo ciclo ({days_left:.1f} dias restantes)")  # noqa: E501

        # Receita
        expires_soon, days_to_expire = prescription_expires_soon(expiry_str, PRESCRIPTION_ALERT_DAYS)  # noqa: E501
        if expires_soon:
            print(f"  ⚠️ Receita vence em {days_to_expire} dias")
        else:
            print(f"  📅 Receita válida por mais {days_to_expire} dias")

        print()

if __name__ == "__main__":
    check_medications()

