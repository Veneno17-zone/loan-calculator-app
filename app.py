import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
from jinja2 import Template

# --- Amortization Schedule Calculation ---
def calculate_amortization_schedule(principal, annual_rate, years, extra_payment=0.0, start_date="2025-07-01", fees=0.0, balloon_payment=0.0):
    monthly_rate = annual_rate / 12 / 100
    months = years * 12
    principal += fees
    monthly_payment = (principal - balloon_payment) * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1) if monthly_rate else (principal - balloon_payment) / months
    monthly_payment += extra_payment

    balance = principal
    schedule = []
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    total_interest = 0.0

    for month in range(1, months + 1):
        interest = balance * monthly_rate
        principal_paid = min(monthly_payment - interest, balance)
        balance -= principal_paid
        total_interest += interest
        payment_date = start_date + timedelta(days=30 * (month - 1))

        schedule.append([
            month,
            payment_date.strftime("%Y-%m-%d"),
            round(monthly_payment, 2),
            round(principal_paid, 2),
            round(interest, 2),
            round(balance, 2)
        ])

        if balance <= 0:
            break

    if balloon_payment > 0 and balance > 0:
        balance -= balloon_payment
        final_payment_date = start_date + timedelta(days=30 * month)
        schedule.append([
            month + 1,
            final_payment_date.strftime("%Y-%m-%d"),
            round(balloon_payment, 2),
            round(balloon_payment, 2),
            0.0,
            round(balance, 2)
        ])
        month += 1

    df = pd.DataFrame(schedule, columns=["Month", "Date", "Payment", "Principal Paid", "Interest Paid", "Remaining Balance"])
    total_paid = df["Payment"].sum()
    return df, total_interest, total_paid, month

# --- Car Depreciation Calculation ---
def calculate_car_value_over_time(initial_value, annual_depreciation, months):
    values = []
    value = initial_value
    monthly_depreciation = (1 - annual_depreciation / 100) ** (1 / 12)
    for month in range(1, months + 1):
        value *= monthly_depreciation
        values.append(round(value, 2))
    return values

# --- Chart: Loan vs Car Value ---
def plot_loan_vs_car_value_chart(df, show_car_value=False):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Remaining Balance"],
        mode='lines+markers',
        name='Remaining Loan Balance',
        line=dict(color='royalblue', width=3),
        marker=dict(size=6),
        hovertemplate='Month %{x}<br>Loan Balance: $%{y:,.2f}<extra></extra>'
    ))

    if show_car_value and "Estimated Car Value" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Month"],
            y=df["Estimated Car Value"],
            mode='lines+markers',
            name='Estimated Car Value',
            line=dict(color='green', width=3, dash='dash'),
            marker=dict(size=6),
            hovertemplate='Month %{x}<br>Car Value: $%{y:,.2f}<extra></extra>'
        ))

    fig.update_layout(
        title='📉 Loan vs. Car Value Chart',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        hovermode='x unified',
        template='plotly_white',
        margin=dict(t=50, l=50, r=50, b=50)
    )
    return fig

# --- Chart: Loan Breakdown Pie ---
def plot_pie_chart_interactive(principal, interest):
    fig = go.Figure(data=[go.Pie(
        labels=['Principal', 'Interest'],
        values=[principal, interest],
        hole=0.4,
        marker=dict(colors=['#4CAF50', '#FF7043']),
        hoverinfo='label+percent+value',
        textinfo='label+percent'
    )])
    fig.update_layout(
        title='💰 Loan Payment Breakdown',
        annotations=[dict(text='Loan', x=0.5, y=0.5, font_size=20, showarrow=False)],
        template='plotly_white'
    )
    return fig

# --- UI Setup ---
st.set_page_config(page_title="Loan Calculator", layout="centered")
st.sidebar.title("⚙️ Settings")
theme = st.sidebar.selectbox("Theme", ["Light", "Dark"])
if theme == "Dark":
    st.markdown("<style>body { background-color: #0e1117; color: white; }</style>", unsafe_allow_html=True)

st.title("🚗🏠 Loan Payment Calculator")

# --- Loan Inputs ---
loan_type = st.selectbox("Choose loan type", ["Car Loan", "Home Loan"])
price_label = "Home Price ($)" if loan_type == "Home Loan" else "Car Price ($)"
total_price = st.number_input(price_label, min_value=1000, step=1000, value=200000)
down_payment = st.number_input("Down Payment ($)", min_value=0, step=1000, value=20000 if loan_type == "Home Loan" else 0)
principal = total_price - down_payment
st.markdown(f"💵 **Loan Amount to Finance:** ${principal:,.2f}")

annual_rate = st.number_input("Annual Interest Rate (APR %)", min_value=0.1, max_value=25.0, value=5.0, step=0.1)
years = st.number_input("Loan Term (Years)", min_value=1, max_value=40, value=5)
extra_payment = st.number_input("Extra Monthly Payment ($)", min_value=0, step=50, value=0)
fees = st.number_input("Additional Fees ($)", min_value=0, step=50, value=0)
balloon_payment = st.number_input("Balloon Payment (Car Loans only) ($)", min_value=0, step=1000, value=0) if loan_type == "Car Loan" else 0
depreciation_rate = st.slider("Estimated Annual Car Depreciation (%)", min_value=5, max_value=30, value=15) if loan_type == "Car Loan" else 0
start_date = st.date_input("Loan Start Date", value=datetime.today())

# --- Calculate Loan ---
if st.button("Calculate Loan"):
    df, total_interest, total_paid, months = calculate_amortization_schedule(
        principal,
        annual_rate,
        years,
        extra_payment,
        start_date.strftime("%Y-%m-%d"),
        fees,
        balloon_payment
    )

    total_paid_including_fees = total_paid + fees
    st.subheader(f"Loan paid off in {months} months")
    st.success(f"💰 Total interest paid: **${total_interest:,.2f}**")
    st.info(f"📦 Total paid (including fees): **${total_paid_including_fees:,.2f}**")

    # --- Car Depreciation & Chart ---
if loan_type == "Car Loan":
        car_values = calculate_car_value_over_time(total_price, depreciation_rate, months)
        df["Estimated Car Value"] = pd.Series(car_values).round(2)

        # 🔔 Negative Equity Detection
        df["Remaining Balance"] = df["Remaining Balance"].round(2)
        df["Negative Equity"] = df["Remaining Balance"] > df["Estimated Car Value"]

        if df["Negative Equity"].any():
            first_neg = df[df["Negative Equity"]].iloc[0]
            st.warning(f"⚠️ You enter **negative equity in Month {first_neg['Month']} ({first_neg['Date']})**.")
        else:
            st.success("✅ No negative equity during loan term.")

        st.plotly_chart(plot_loan_vs_car_value_chart(df, show_car_value=True), use_container_width=True)

else:
        df["Remaining Balance"] = df["Remaining Balance"].round(2)
        st.plotly_chart(plot_loan_vs_car_value_chart(df, show_car_value=False), use_container_width=True)


    # --- Styled Table ---
    styled_df = df.style.background_gradient(cmap='Greens', subset=["Principal Paid"])\
                        .background_gradient(cmap='Oranges', subset=["Interest Paid"])\
                        .background_gradient(cmap='Blues', subset=["Remaining Balance"])
    st.dataframe(styled_df, use_container_width=True)

    # --- Download CSV ---
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button("📥 Download Amortization Schedule (CSV)", csv_buffer.getvalue(), "amortization_schedule.csv", "text/csv")

    # --- Download Summary (HTML Report) ---
    html_template = """
    <h2>Loan Summary</h2>
    <ul>
        <li><strong>Loan Amount:</strong> ${{ principal }}</li>
        <li><strong>Interest Paid:</strong> ${{ interest }}</li>
        <li><strong>Total Paid:</strong> ${{ total }}</li>
        <li><strong>Term:</strong> {{ months }} months</li>
    </ul>
    <p>Report generated from your loan app.</p>
    """
    template = Template(html_template)
    html_report = template.render(
        principal=f"{principal:,.2f}",
        interest=f"{total_interest:,.2f}",
        total=f"{total_paid_including_fees:,.2f}",
        months=months
    )
    html_buffer = BytesIO(html_report.encode("utf-8"))
    st.download_button("📝 Download Loan Summary (HTML)", html_buffer, "loan_summary.html", "text/html")

    # --- Pie Chart ---
    st.plotly_chart(plot_pie_chart_interactive(principal, total_interest), use_container_width=True)
