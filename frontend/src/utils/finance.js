export function calculateFinancialMetrics(params) {
    const {
        purchase_price,
        down_payment_pct,
        mutuo_rate,
        mutuo_term,
        registro_pct,
        notary_purchase_fee,
        notary_mutuo_fee,
        agency_fee_pct,
        mutuo_tax_pct,
        bank_origination_fee,
        appraisal_fee,
        technical_report_fee,
        cadastral_and_mortgage_taxes,
        imu,
        tari,
        maintenance_pct,
        insurance,
        condo_fees_monthly,
        electricity_monthly,
        gas_monthly,
        water_monthly,
        internet_monthly,
        accountant_fee_annual,
        nightly_rate,
        occupancy_rate,
        cleaning_fee,
        management_fee_pct,
        platform_fee_pct,
        avg_stay_nights = 4,
        cedolare_secca_rate = 0.21,
    } = params;

    const down_payment = purchase_price * down_payment_pct;
    const mutuo_amount = purchase_price - down_payment;

    let monthly_mutuo_payment = 0;
    const r = mutuo_rate / 12;
    const n = mutuo_term * 12;
    if (r === 0) {
        monthly_mutuo_payment = mutuo_amount / n;
    } else {
        monthly_mutuo_payment = mutuo_amount * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    }

    const registro = purchase_price * registro_pct;
    const agency = purchase_price * agency_fee_pct;
    const mutuo_tax = mutuo_amount * mutuo_tax_pct;
    const fees = notary_purchase_fee + notary_mutuo_fee + bank_origination_fee + appraisal_fee + technical_report_fee + cadastral_and_mortgage_taxes;
    const total_acquisition_cost = registro + agency + mutuo_tax + fees;

    const total_cash_outlay = down_payment + total_acquisition_cost;

    const occupied_nights = Math.floor(365 * occupancy_rate);
    const gross_rental_income_annual = occupied_nights * nightly_rate;

    const turnovers = Math.floor(occupied_nights / avg_stay_nights);
    const cleaning_fee_income_annual = turnovers * cleaning_fee;

    const total_gross = gross_rental_income_annual + cleaning_fee_income_annual;
    const management = total_gross * management_fee_pct;
    const platform = total_gross * platform_fee_pct;
    const net_rental_income_annual = total_gross - management - platform;

    const fixed_expenses = imu + tari + (purchase_price * maintenance_pct) + insurance + accountant_fee_annual + (condo_fees_monthly * 12);
    const utilities = (electricity_monthly + gas_monthly + water_monthly + internet_monthly) * 12;
    const annual_expenses = fixed_expenses + utilities;

    const rental_income_tax = net_rental_income_annual * cedolare_secca_rate;

    const annual_cash_flow = net_rental_income_annual - annual_expenses - rental_income_tax - (monthly_mutuo_payment * 12);

    const cash_on_cash_return = total_cash_outlay === 0 ? 0 : annual_cash_flow / total_cash_outlay;

    const cap_rate = purchase_price === 0 ? 0 : (net_rental_income_annual - annual_expenses - rental_income_tax) / purchase_price;

    const gross_yield = purchase_price === 0 ? 0 : gross_rental_income_annual / purchase_price;

    return {
        cash_on_cash_return: cash_on_cash_return * 100, // as percentage
        cap_rate: cap_rate * 100, // as percentage
        gross_yield: gross_yield * 100, // as percentage
        gross_rental_income_annual,
        net_rental_income_annual,
        annual_expenses,
        annual_cash_flow,
        total_cash_outlay,
        total_acquisition_cost
    };
}

export function calculateZoneMetrics(zone, defaultParams, overrides = {}) {
    const avgBuy = ((zone.buy_min || 0) + (zone.buy_max || 0)) / 2;
    if (avgBuy === 0) return null; // Can't calculate if no price

    const baseSqM = overrides.square_meters ?? defaultParams.square_meters;
    const purchase_price = Math.round(avgBuy * baseSqM);
    const nightly_rate = (zone.has_str_data && zone.median_nightly_rate) ? Math.round(zone.median_nightly_rate) : defaultParams.nightly_rate;

    const params = {
        ...defaultParams,
        purchase_price,
        nightly_rate,
        ...overrides
    };

    return calculateFinancialMetrics(params);
}

export function oldGrossYield(zone) {
    if (!zone.rent_min || !zone.buy_min || zone.buy_min === 0) return null;
    return ((zone.rent_min * 12) / zone.buy_min) * 100;
}
