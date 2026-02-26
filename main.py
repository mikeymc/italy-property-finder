from src.financial_model import (
    PropertyInvestment,
    AcquisitionCosts,
    AnnualCosts,
    RentalIncome,
)


def main():
    print("--- 🏡 Italy Real Estate Financial Model ---")

    # Example property in Italy
    invest = PropertyInvestment(
        purchase_price=150_000.0,
        square_meters=60.0,
        down_payment_pct=0.20,
        mutuo_rate_annual=0.04,  # 4%
        mutuo_term_years=20,
        acquisition=AcquisitionCosts(
            registro_pct=0.09,  # 9% second home tax
            notary_fee=2_500.0,
            agency_fee_pct=0.03,  # 3% agency fee
        ),
        annual_costs=AnnualCosts(
            imu=1_200.0,
            tari=300.0,
            maintenance_pct=0.01,  # 1% maintenance
            insurance=400.0,
            condo_fees_monthly=50.0,
            utilities_monthly=150.0,
        ),
        rental_income=RentalIncome(
            nightly_rate=120.0,
            occupancy_rate=0.60,  # 60% occupancy
            cleaning_fee=50.0,
            management_fee_pct=0.20,
            platform_fee_pct=0.15,
            avg_stay_nights=4,
        ),
        cedolare_secca_rate=0.21,  # 21% flat tax rate
    )

    print(f"Purchase Price:      €{invest.purchase_price:,.2f}")
    print(
        f"Down Payment:        €{invest.down_payment:,.2f} ({invest.down_payment_pct*100:.0f}%)"
    )
    print(f"Total Cash Outlay:   €{invest.total_cash_outlay:,.2f}")

    print("\n--- 💰 Annual Cash Flow ---")
    print(f"Gross Rental Income: €{invest.gross_rental_income_annual:,.2f}")
    print(f"Net Rental Income:   €{invest.net_rental_income_annual:,.2f}")
    print(f"Annual Expenses:     €{invest.annual_expenses:,.2f}")
    print(f"Rental Tax (21%):    €{invest.rental_income_tax:,.2f}")
    print(f"Mortgage Payment:    €{invest.monthly_mutuo_payment * 12:,.2f}")
    print(f"Net Cash Flow:       €{invest.annual_cash_flow:,.2f}")

    print("\n--- 📈 Returns ---")
    print(f"Cap Rate:            {invest.cap_rate * 100:.2f}%")
    print(f"Cash-on-Cash Return: {invest.cash_on_cash_return * 100:.2f}%")
    print(f"Break-Even Occupancy:{invest.break_even_occupancy * 100:.2f}%")

    # Target 10% cash-on-cash return
    target = 0.10
    required_rate = invest.required_nightly_rate_for_target(target)
    print(
        f"\nTo hit {target*100:.0f}% return, nightly rate must be: €{required_rate:.2f}"
    )


if __name__ == "__main__":
    main()
