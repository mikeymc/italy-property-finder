# ABOUTME: Core financial model for Italian rental property investment analysis.
# ABOUTME: Calculates ROI, cash flow, cap rate, and break-even for a given property.

from dataclasses import dataclass, field


@dataclass
class AcquisitionCosts:
    """One-time costs at purchase."""
    registro_pct: float          # Imposta di registro (9% second home, 2% first home)
    notary_fee: float            # Notary flat fee
    agency_fee_pct: float        # Real estate agent fee as % of purchase price


@dataclass
class AnnualCosts:
    """Recurring annual costs of ownership."""
    imu: float                   # Property tax (based on cadastral value)
    tari: float                  # Waste tax
    maintenance_pct: float       # Annual maintenance as % of purchase price
    insurance: float             # Annual insurance
    condo_fees_monthly: float    # Monthly condominium fees
    utilities_monthly: float     # Monthly utilities when property is vacant


@dataclass
class RentalIncome:
    """Short-term rental income parameters."""
    nightly_rate: float          # Average nightly rate
    occupancy_rate: float        # Expected occupancy (0-1)
    cleaning_fee: float          # Per-turnover cleaning fee charged to guests
    management_fee_pct: float    # Property manager cut of gross revenue
    platform_fee_pct: float      # Airbnb/Booking host fee
    avg_stay_nights: int = 4     # Average guest stay length


@dataclass
class PropertyInvestment:
    """Full financial model for an Italian rental property investment."""
    purchase_price: float
    square_meters: float
    down_payment_pct: float
    mutuo_rate_annual: float
    mutuo_term_years: int
    acquisition: AcquisitionCosts
    annual_costs: AnnualCosts
    rental_income: RentalIncome
    cedolare_secca_rate: float

    @property
    def price_per_sqm(self) -> float:
        return self.purchase_price / self.square_meters

    @property
    def down_payment(self) -> float:
        return self.purchase_price * self.down_payment_pct

    @property
    def mutuo_amount(self) -> float:
        return self.purchase_price - self.down_payment

    @property
    def monthly_mutuo_payment(self) -> float:
        """Standard amortizing mortgage payment formula."""
        r = self.mutuo_rate_annual / 12
        n = self.mutuo_term_years * 12
        if r == 0:
            return self.mutuo_amount / n
        return self.mutuo_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    @property
    def total_acquisition_cost(self) -> float:
        registro = self.purchase_price * self.acquisition.registro_pct
        agency = self.purchase_price * self.acquisition.agency_fee_pct
        return registro + self.acquisition.notary_fee + agency

    @property
    def total_cash_outlay(self) -> float:
        """Total cash needed upfront: down payment + acquisition costs."""
        return self.down_payment + self.total_acquisition_cost

    @property
    def _occupied_nights(self) -> int:
        return int(365 * self.rental_income.occupancy_rate)

    @property
    def gross_rental_income_annual(self) -> float:
        return self._occupied_nights * self.rental_income.nightly_rate

    @property
    def cleaning_fee_income_annual(self) -> float:
        turnovers = self._occupied_nights // self.rental_income.avg_stay_nights
        return turnovers * self.rental_income.cleaning_fee

    @property
    def net_rental_income_annual(self) -> float:
        """Gross rental + cleaning income minus management and platform fees."""
        total_gross = self.gross_rental_income_annual + self.cleaning_fee_income_annual
        management = total_gross * self.rental_income.management_fee_pct
        platform = total_gross * self.rental_income.platform_fee_pct
        return total_gross - management - platform

    @property
    def annual_expenses(self) -> float:
        """All annual property expenses (excluding mutuo and income tax)."""
        fixed = (
            self.annual_costs.imu
            + self.annual_costs.tari
            + self.purchase_price * self.annual_costs.maintenance_pct
            + self.annual_costs.insurance
            + self.annual_costs.condo_fees_monthly * 12
        )
        # Utilities only incurred during vacant periods
        vacancy_rate = 1 - self.rental_income.occupancy_rate
        utilities = self.annual_costs.utilities_monthly * 12 * vacancy_rate
        return fixed + utilities

    @property
    def rental_income_tax(self) -> float:
        return self.net_rental_income_annual * self.cedolare_secca_rate

    @property
    def annual_cash_flow(self) -> float:
        return (
            self.net_rental_income_annual
            - self.annual_expenses
            - self.rental_income_tax
            - self.monthly_mutuo_payment * 12
        )

    @property
    def cash_on_cash_return(self) -> float:
        """Annual cash flow as percentage of total cash invested."""
        return self.annual_cash_flow / self.total_cash_outlay

    @property
    def cap_rate(self) -> float:
        """NOI / purchase price. Ignores financing — measures property's raw return."""
        noi = self.net_rental_income_annual - self.annual_expenses - self.rental_income_tax
        return noi / self.purchase_price

    @property
    def break_even_occupancy(self) -> float:
        """Occupancy rate needed to cover all costs (mutuo, expenses, tax).

        Solves for the occupancy rate where annual_cash_flow = 0.
        Uses iterative approach since occupancy affects multiple terms nonlinearly.
        """
        low, high = 0.0, 1.0
        for _ in range(100):
            mid = (low + high) / 2
            test = self._cash_flow_at_occupancy(mid)
            if test < 0:
                low = mid
            else:
                high = mid
        return (low + high) / 2

    def _cash_flow_at_occupancy(self, occupancy: float) -> float:
        """Calculate cash flow at a given occupancy rate."""
        occupied_nights = int(365 * occupancy)
        gross = occupied_nights * self.rental_income.nightly_rate
        turnovers = occupied_nights // self.rental_income.avg_stay_nights
        cleaning = turnovers * self.rental_income.cleaning_fee
        total_gross = gross + cleaning
        management = total_gross * self.rental_income.management_fee_pct
        platform = total_gross * self.rental_income.platform_fee_pct
        net_rental = total_gross - management - platform

        fixed_expenses = (
            self.annual_costs.imu
            + self.annual_costs.tari
            + self.purchase_price * self.annual_costs.maintenance_pct
            + self.annual_costs.insurance
            + self.annual_costs.condo_fees_monthly * 12
        )
        utilities = self.annual_costs.utilities_monthly * 12 * (1 - occupancy)
        expenses = fixed_expenses + utilities

        tax = net_rental * self.cedolare_secca_rate
        mutuo = self.monthly_mutuo_payment * 12

        return net_rental - expenses - tax - mutuo

    def required_nightly_rate_for_target(self, target_return: float) -> float:
        """Find the nightly rate needed to achieve a target cash-on-cash return.

        Uses binary search since the relationship between nightly rate and
        return is monotonic but involves integer rounding (occupied nights).
        """
        from dataclasses import replace
        low, high = 0.0, 1000.0
        for _ in range(100):
            mid = (low + high) / 2
            test_rental = RentalIncome(
                nightly_rate=mid,
                occupancy_rate=self.rental_income.occupancy_rate,
                cleaning_fee=self.rental_income.cleaning_fee,
                management_fee_pct=self.rental_income.management_fee_pct,
                platform_fee_pct=self.rental_income.platform_fee_pct,
                avg_stay_nights=self.rental_income.avg_stay_nights,
            )
            test_inv = replace(self, rental_income=test_rental)
            if test_inv.cash_on_cash_return < target_return:
                low = mid
            else:
                high = mid
        return (low + high) / 2

    def monthly_summary(self) -> dict:
        return {
            "gross_rental": self.gross_rental_income_annual / 12,
            "net_rental": self.net_rental_income_annual / 12,
            "expenses": self.annual_expenses / 12,
            "rental_tax": self.rental_income_tax / 12,
            "mutuo_payment": self.monthly_mutuo_payment,
            "net_cash_flow": self.annual_cash_flow / 12,
        }
