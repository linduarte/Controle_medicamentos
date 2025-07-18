import streamlit as st
from logic.database import (
    fetch_all_medications,
    connect_db,
    create_user,
    get_user_by_email,
    validate_user,
    insert_medication,
    update_stock,
)
from logic.config import get_refill_day, load_config, get_application_version
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile

from pathlib import Path
import json


def calculate_days_left(stock, dosage):
    if dosage == 0:
        return float("inf")
    return stock / dosage


def get_status_labels(med, days_until_refill):
    alerts = []
    days_left = calculate_days_left(med["stock_in_units"], med["dosage_per_intake"])
    if days_left < days_until_refill:
        alerts.append("⚠ Estoque")
    expiry = datetime.strptime(med["prescription_expiry"], "%Y-%m-%d").date()
    days_to_expiry = (expiry - datetime.today().date()).days
    # Alerta se a receita está para vencer em menos de 15 dias
    if 0 <= days_to_expiry < 15:
        alerts.append(f"⚠ Receita vence em {days_to_expiry} dia(s)")
    # Alerta se a receita já venceu
    if days_to_expiry < 0:
        alerts.append("❌ Receita médica vencida! Não é possível comprar.")
    return ", ".join(alerts) if alerts else "OK"


def generate_pdf_report(alerts, config_data):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        path = Path(tmp.name)
    _, height = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "Relatório de Medicamentos com Alerta")
    c.setFont("Helvetica", 10)
    c.drawString(
        50, height - 65, f"Data de geração: {datetime.today().strftime('%d/%m/%Y')}"
    )
    y = height - 100
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Nome")
    c.drawString(250, y, "Estoque (dias)")
    c.drawString(400, y, "Receita vence em")
    c.setFont("Helvetica", 11)
    for row in alerts:
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50, y, row[0])
        c.drawString(250, y, row[1])
        c.drawString(400, y, row[2])
    y -= 40
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, f"Total de alertas: {len(alerts)} medicamento(s)")
    y -= 20
    c.drawString(
        50, y, f"Data inicial do controle: {config_data.get('initial_date', '-')}"
    )
    c.save()
    return path


# --- Autenticação de Usuário ---
st.title("Controle de Medicamentos")
st.write(f"Versão: {get_application_version()}")

if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
    st.session_state["email"] = None


def login_form():
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        if submit:
            user = validate_user(email, password)
            if user:
                st.session_state["user_id"] = user["id"]
                st.session_state["email"] = user["email"]
                st.success(f"Bem-vindo, {email}!")
                st.rerun()
            else:
                st.error("E-mail ou senha inválidos.")


def register_form():
    st.subheader("Cadastrar novo usuário")
    import re

    with st.form("register_form"):
        email = st.text_input("E-mail")
        password = st.text_input("Nova senha", type="password")
        submit = st.form_submit_button("Cadastrar")
        if submit:
            email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not re.match(email_regex, email):
                st.error("E-mail inválido. Informe um e-mail válido.")
            elif get_user_by_email(email):
                st.error("E-mail já cadastrado.")
            else:
                create_user(email, password)
                st.success("Usuário cadastrado! Faça login.")


if not st.session_state["user_id"]:
    login_form()
    st.info("Ou cadastre-se abaixo:")
    register_form()
    st.stop()

st.success(f"Usuário logado: {st.session_state['email']}")
if st.button("Sair"):
    st.session_state["user_id"] = None
    st.session_state["email"] = None
    st.rerun()

# Guia rápido de uso
with st.expander("ℹ️ Como usar o Controle de Medicamentos?", expanded=True):
    st.markdown("""
**Passos básicos para o controle de estoque:**

1. **Adicione seus medicamentos** usando o botão "➕ Adicionar Medicamento". Informe nome, dosagem, estoque e validade da receita.
2. **Defina um medicamento de referência** (marque como referência ao cadastrar ou editar) para que o sistema calcule o ciclo de compra automática (30 dias).
3. **Acompanhe o estoque**: O sistema calcula automaticamente quanto tempo o estoque dura e alerta quando for necessário comprar.
4. **Receitas**: O sistema alerta quando a receita médica está próxima do vencimento ou vencida. Não é possível reabastecer medicamentos com receita vencida ou com mais de 6 meses.
5. **Reabastecimento automático**: No dia base de compra, o medicamento de referência é reabastecido automaticamente se a receita estiver válida.
6. **Promoções**: Se comprar mais unidades, basta editar o estoque manualmente.

> Dúvidas? Consulte o README ou entre em contato com o suporte.
    """)

user_id = st.session_state["user_id"]


config_data = load_config()
refill_base = get_refill_day()
next_refill = refill_base
while next_refill < datetime.today().date():
    next_refill += timedelta(days=30)
days_until_refill = (next_refill - datetime.today().date()).days


# --- Lógica de reabastecimento automático do medicamento de referência ---
REFERENCE_DAYS = 30
today = datetime.today().date()
last_update = config_data.get("last_stock_update")
if last_update:
    last_update = datetime.strptime(last_update, "%Y-%m-%d").date()
else:
    last_update = None

# Só executa se for o dia da compra e ainda não foi feito hoje
if today == next_refill and (not last_update or last_update < today):
    meds_ref = [
        dict(m) for m in fetch_all_medications(user_id=user_id) if m["is_reference"]
    ]
    for med in meds_ref:
        # Verifica validade da receita (6 meses = 180 dias)
        expiry = datetime.strptime(med["prescription_expiry"], "%Y-%m-%d").date()
        days_to_expiry = (expiry - today).days
        if days_to_expiry < 0:
            st.warning(
                f"❌ Não foi possível reabastecer '{med['name']}' porque a receita está vencida desde {expiry.strftime('%d/%m/%Y')}."
            )
            continue
        if (expiry - timedelta(days=180)) < today:
            st.warning(
                f"⚠ Não foi possível reabastecer '{med['name']}' porque a receita tem mais de 6 meses. Atualize a receita para continuar comprando."
            )
            continue
        novo_estoque = med["stock_in_units"] + REFERENCE_DAYS * med["dosage_per_intake"]
        update_stock(med["id"], novo_estoque)
    # Atualiza o campo last_stock_update no config.json
    config_data["last_stock_update"] = today.strftime("%Y-%m-%d")
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

st.info(
    f"🗓️ Próxima compra: {next_refill.strftime('%d/%m/%Y')} (em {days_until_refill} dias)"
)

meds = [dict(m) for m in fetch_all_medications(user_id=user_id)]
for m in meds:
    m["status"] = get_status_labels(m, days_until_refill)

st.subheader("Lista de Medicamentos")
st.dataframe(meds)

# Alertas
alerts = []
for med in meds:
    dosage = float(med["dosage_per_intake"])
    days_left = med["stock_in_units"] / dosage if dosage else float("inf")
    expiry = datetime.strptime(med["prescription_expiry"], "%Y-%m-%d").date()
    days_to_expiry = (expiry - datetime.today().date()).days
    if days_left < days_until_refill or days_to_expiry < 15:
        alerts.append([med["name"], f"{days_left:.1f} dias", f"{days_to_expiry} dias"])

if alerts:
    st.warning(f"{len(alerts)} medicamento(s) requer(em) atenção!")
    if st.button("Gerar PDF de Alertas"):
        pdf_path = generate_pdf_report(alerts, config_data)
        with open(pdf_path, "rb") as f:
            st.download_button("Baixar PDF", f, file_name="alertas.pdf")
        pdf_path.unlink()
else:
    st.success("Nenhum medicamento requer atenção no momento.")

# Adicionar medicamento
with st.expander("➕ Adicionar Medicamento"):
    with st.form("add_med"):
        name = st.text_input("Nome do Medicamento")
        dose = st.number_input("Dosagem por Uso", min_value=0.0)
        stock = st.number_input("Estoque em Unidades", min_value=0)
        validity = st.date_input("Validade da Receita")
        submitted = st.form_submit_button("Salvar")
        if submitted:
            try:
                insert_medication(
                    user_id,
                    name,
                    dose,
                    "Tablet",
                    "daily",
                    "box",
                    30,
                    stock,
                    "Active",
                    0,
                    validity.strftime("%Y-%m-%d"),
                )
                st.success("Medicamento adicionado!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao adicionar: {e}")

# Editar medicamento
with st.expander("✏️ Editar Medicamento"):
    med_ids = [m["id"] for m in meds]
    if med_ids:
        edit_id = st.selectbox("Selecione o ID do medicamento para editar", med_ids)
        med = next((m for m in meds if m["id"] == edit_id), None)
        if med:
            with st.form("edit_med"):
                new_name = st.text_input("Nome", value=med["name"])
                new_dose = st.number_input("Dosagem", value=med["dosage_per_intake"])
                new_stock = st.number_input("Estoque", value=med["stock_in_units"])
                new_validity = st.date_input(
                    "Validade",
                    value=datetime.strptime(med["prescription_expiry"], "%Y-%m-%d"),
                )
                submitted = st.form_submit_button("Salvar alterações")
                if submitted:
                    try:
                        conn = connect_db()
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            UPDATE medications
                            SET name=?, dosage_per_intake=?, stock_in_units=?, prescription_expiry=?
                            WHERE id=? AND user_id=?
                        """,
                            (
                                new_name,
                                new_dose,
                                new_stock,
                                new_validity.strftime("%Y-%m-%d"),
                                edit_id,
                                user_id,
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Medicamento atualizado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")
    else:
        st.info("Nenhum medicamento para editar.")
