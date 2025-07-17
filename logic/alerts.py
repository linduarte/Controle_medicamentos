from datetime import datetime

def check_stock_alerts(med):
    daily_dose = med['dosage_per_intake']
    stock_days = med['stock_in_units'] / daily_dose
    if stock_days <= 10:
        return True
    return False

def check_prescription_alert(expiry_date_str):
    expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
    return (expiry_date - datetime.today()).days < 15
