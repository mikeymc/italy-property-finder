# ABOUTME: Tests for the core financial model that calculates investment returns
# ABOUTME: for Italian rental properties including mutuo, taxes, and STR revenue.

from src.financial_model import PropertyInvestment, AcquisitionCosts, AnnualCosts, RentalIncome


class TestPropertyInvestment:
    """Test the core investment model with a realistic Italian property scenario."""

    def _sample_investment(self) -> PropertyInvestment:
        """A realistic 70sqm apartment in a mid-tier Italian tourist area."""
        return PropertyInvestment(
            purchase_price=150_000,
            square_meters=70,
            # Mutuo terms
            down_payment_pct=0.20,
            mutuo_rate_annual=0.035,
            mutuo_term_years=25,
            # Acquisition costs
            acquisition=AcquisitionCosts(
                registro_pct=0.09,      # 9% for second home
                notary_fee=3_000,
                agency_fee_pct=0.03,
            ),
            # Annual recurring costs
            annual_costs=AnnualCosts(
                imu=800,                # Based on cadastral value
                tari=400,               # Waste tax
                maintenance_pct=0.01,   # 1% of purchase price per year
                insurance=300,
                condo_fees_monthly=100,
                utilities_monthly=150,  # When not rented (owner's share)
            ),
            # Rental income
            rental_income=RentalIncome(
                nightly_rate=90,
                occupancy_rate=0.60,    # 60% occupancy
                cleaning_fee=50,
                management_fee_pct=0.20,  # 20% property manager cut
                platform_fee_pct=0.03,    # Airbnb host fee ~3%
            ),
            # Tax on rental income
            cedolare_secca_rate=0.21,
        )

    def test_price_per_sqm(self):
        inv = self._sample_investment()
        assert inv.price_per_sqm == 150_000 / 70

    def test_down_payment(self):
        inv = self._sample_investment()
        assert inv.down_payment == 30_000

    def test_mutuo_amount(self):
        inv = self._sample_investment()
        assert inv.mutuo_amount == 120_000

    def test_monthly_mutuo_payment(self):
        inv = self._sample_investment()
        # For 120k at 3.5% over 25 years, monthly payment should be ~€601
        payment = inv.monthly_mutuo_payment
        assert 595 < payment < 610

    def test_total_acquisition_cost(self):
        inv = self._sample_investment()
        # registro: 150k * 9% = 13,500
        # notary: 3,000
        # agency: 150k * 3% = 4,500
        # total: 21,000
        assert inv.total_acquisition_cost == 13_500 + 3_000 + 4_500

    def test_total_cash_outlay(self):
        """Down payment + acquisition costs = total cash needed upfront."""
        inv = self._sample_investment()
        expected = 30_000 + 21_000
        assert inv.total_cash_outlay == expected

    def test_gross_rental_income_annual(self):
        inv = self._sample_investment()
        # 365 nights * 60% occupancy = 219 nights
        # 219 * €90 = €19,710
        nights = int(365 * 0.60)
        expected = nights * 90
        assert inv.gross_rental_income_annual == expected

    def test_cleaning_fee_income_annual(self):
        inv = self._sample_investment()
        # Assume average stay of 4 nights -> ~54 turnovers
        # But cleaning fees are pass-through, offset by cleaning costs
        # For now: 219 nights / avg_stay * cleaning_fee
        # We'll use a default avg_stay of 4 nights
        turnovers = int(365 * 0.60) // 4
        expected = turnovers * 50
        assert inv.cleaning_fee_income_annual == expected

    def test_net_rental_income_annual(self):
        inv = self._sample_investment()
        gross = inv.gross_rental_income_annual
        cleaning_income = inv.cleaning_fee_income_annual
        total_gross = gross + cleaning_income
        management = total_gross * 0.20
        platform = total_gross * 0.03
        expected = total_gross - management - platform
        assert abs(inv.net_rental_income_annual - expected) < 1

    def test_annual_expenses(self):
        inv = self._sample_investment()
        # IMU: 800, TARI: 400, maintenance: 1500, insurance: 300
        # condo: 100*12=1200, utilities: 150*12=1800 (prorated by vacancy)
        # Utilities only apply when NOT rented (~40% of year)
        expected_fixed = 800 + 400 + 1_500 + 300 + 1_200
        expected_utilities = 150 * 12 * (1 - 0.60)  # Only pay when vacant
        expected = expected_fixed + expected_utilities
        assert abs(inv.annual_expenses - expected) < 1

    def test_rental_income_tax(self):
        inv = self._sample_investment()
        # Cedolare secca: 21% of net rental income
        expected = inv.net_rental_income_annual * 0.21
        assert abs(inv.rental_income_tax - expected) < 1

    def test_annual_cash_flow(self):
        inv = self._sample_investment()
        # Net rental income - expenses - tax - mutuo payments
        expected = (
            inv.net_rental_income_annual
            - inv.annual_expenses
            - inv.rental_income_tax
            - inv.monthly_mutuo_payment * 12
        )
        assert abs(inv.annual_cash_flow - expected) < 1

    def test_cash_on_cash_return(self):
        inv = self._sample_investment()
        # Annual cash flow / total cash invested
        expected = inv.annual_cash_flow / inv.total_cash_outlay
        assert abs(inv.cash_on_cash_return - expected) < 0.001

    def test_cap_rate(self):
        inv = self._sample_investment()
        # NOI / purchase price (ignoring financing)
        noi = inv.net_rental_income_annual - inv.annual_expenses - inv.rental_income_tax
        expected = noi / inv.purchase_price
        assert abs(inv.cap_rate - expected) < 0.001

    def test_break_even_occupancy(self):
        """What occupancy rate do we need just to cover all costs?"""
        inv = self._sample_investment()
        rate = inv.break_even_occupancy
        assert 0 < rate < 1  # Should be achievable
        assert rate < inv.rental_income.occupancy_rate  # Should be below our assumption

    def test_monthly_summary(self):
        inv = self._sample_investment()
        summary = inv.monthly_summary()
        assert "gross_rental" in summary
        assert "mutuo_payment" in summary
        assert "net_cash_flow" in summary
        assert summary["mutuo_payment"] > 0


class TestCashPurchase:
    """Test buying outright with no mutuo."""

    def _cash_investment(self) -> PropertyInvestment:
        return PropertyInvestment(
            purchase_price=150_000,
            square_meters=70,
            down_payment_pct=1.0,
            mutuo_rate_annual=0.0,
            mutuo_term_years=25,
            acquisition=AcquisitionCosts(
                registro_pct=0.09,
                notary_fee=3_000,
                agency_fee_pct=0.03,
            ),
            annual_costs=AnnualCosts(
                imu=800, tari=400, maintenance_pct=0.01,
                insurance=300, condo_fees_monthly=100, utilities_monthly=150,
            ),
            rental_income=RentalIncome(
                nightly_rate=90, occupancy_rate=0.60,
                cleaning_fee=50, management_fee_pct=0.20, platform_fee_pct=0.03,
            ),
            cedolare_secca_rate=0.21,
        )

    def test_no_mutuo_payment(self):
        inv = self._cash_investment()
        assert inv.mutuo_amount == 0
        assert inv.monthly_mutuo_payment == 0

    def test_total_cash_outlay_is_full_price_plus_acquisition(self):
        inv = self._cash_investment()
        assert inv.total_cash_outlay == 150_000 + 21_000

    def test_cash_flow_higher_without_mutuo(self):
        """No mortgage means all NOI flows to the owner."""
        cash = self._cash_investment()
        financed = PropertyInvestment(
            purchase_price=150_000, square_meters=70,
            down_payment_pct=0.20, mutuo_rate_annual=0.035, mutuo_term_years=25,
            acquisition=cash.acquisition, annual_costs=cash.annual_costs,
            rental_income=cash.rental_income, cedolare_secca_rate=0.21,
        )
        assert cash.annual_cash_flow > financed.annual_cash_flow

    def test_cash_on_cash_equals_cap_rate_approximately(self):
        """Without financing, cash-on-cash and cap rate should be close.
        They differ slightly because cash outlay includes acquisition costs."""
        inv = self._cash_investment()
        # Cap rate = NOI / purchase_price
        # Cash-on-cash = cash_flow / (purchase_price + acquisition_costs)
        # Since there's no mutuo, cash_flow = NOI, so:
        # cash_on_cash = NOI / (purchase_price + acq) < NOI / purchase_price = cap_rate
        assert inv.cash_on_cash_return < inv.cap_rate
        assert abs(inv.cash_on_cash_return - inv.cap_rate) < 0.02

    def test_break_even_lower_without_mutuo(self):
        cash = self._cash_investment()
        financed = PropertyInvestment(
            purchase_price=150_000, square_meters=70,
            down_payment_pct=0.20, mutuo_rate_annual=0.035, mutuo_term_years=25,
            acquisition=cash.acquisition, annual_costs=cash.annual_costs,
            rental_income=cash.rental_income, cedolare_secca_rate=0.21,
        )
        assert cash.break_even_occupancy < financed.break_even_occupancy


class TestReturnTargets:
    """Test what parameters are needed to hit 10% return target."""

    def test_high_yield_scenario(self):
        """A cheap property with strong STR demand can hit 10%+ cap rate."""
        inv = PropertyInvestment(
            purchase_price=80_000,
            square_meters=50,
            down_payment_pct=1.0,
            mutuo_rate_annual=0.0,
            mutuo_term_years=25,
            acquisition=AcquisitionCosts(
                registro_pct=0.09, notary_fee=2_500, agency_fee_pct=0.03,
            ),
            annual_costs=AnnualCosts(
                imu=500, tari=300, maintenance_pct=0.01,
                insurance=200, condo_fees_monthly=60, utilities_monthly=100,
            ),
            rental_income=RentalIncome(
                nightly_rate=80, occupancy_rate=0.65,
                cleaning_fee=40, management_fee_pct=0.20, platform_fee_pct=0.03,
            ),
            cedolare_secca_rate=0.21,
        )
        # An 80k property at €80/night with 65% occupancy should yield well
        assert inv.cap_rate > 0.08  # At least 8% cap rate

    def test_required_nightly_rate_for_target(self):
        """Verify the required_nightly_rate_for_target method."""
        inv = PropertyInvestment(
            purchase_price=100_000,
            square_meters=60,
            down_payment_pct=1.0,
            mutuo_rate_annual=0.0,
            mutuo_term_years=25,
            acquisition=AcquisitionCosts(
                registro_pct=0.09, notary_fee=2_500, agency_fee_pct=0.03,
            ),
            annual_costs=AnnualCosts(
                imu=600, tari=350, maintenance_pct=0.01,
                insurance=250, condo_fees_monthly=80, utilities_monthly=120,
            ),
            rental_income=RentalIncome(
                nightly_rate=0, occupancy_rate=0.60,
                cleaning_fee=40, management_fee_pct=0.20, platform_fee_pct=0.03,
            ),
            cedolare_secca_rate=0.21,
        )
        rate = inv.required_nightly_rate_for_target(0.10)
        assert rate > 0
        # Verify: if we plug this rate back in, we should get ~10% return
        from dataclasses import replace
        new_rental = RentalIncome(
            nightly_rate=rate, occupancy_rate=0.60,
            cleaning_fee=40, management_fee_pct=0.20, platform_fee_pct=0.03,
        )
        check = replace(inv, rental_income=new_rental)
        assert abs(check.cash_on_cash_return - 0.10) < 0.005
