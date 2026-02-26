// ABOUTME: Displays computed financial metrics from the analysis API.
// ABOUTME: Shows annual cash flow, cap rate, break-even, and monthly breakdown.

export function FinancialSummary({ analysis }) {
  if (!analysis) return null;

  const fmt = (v) => `€${v.toLocaleString('en', { maximumFractionDigits: 0 })}`;
  const pct = (v) => `${(v * 100).toFixed(2)}%`;

  return (
    <div className="financial-summary">
      <h3>Financial Summary</h3>

      <div className="metrics-grid">
        <div className="metric">
          <span className="metric-label">Total Cash Outlay</span>
          <span className="metric-value">{fmt(analysis.total_cash_outlay)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Annual Cash Flow</span>
          <span className={`metric-value ${analysis.annual_cash_flow >= 0 ? 'positive' : 'negative'}`}>
            {fmt(analysis.annual_cash_flow)}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Cap Rate</span>
          <span className="metric-value">{pct(analysis.cap_rate)}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Cash-on-Cash Return</span>
          <span className={`metric-value ${analysis.cash_on_cash_return >= 0 ? 'positive' : 'negative'}`}>
            {pct(analysis.cash_on_cash_return)}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Break-Even Occupancy</span>
          <span className="metric-value">{pct(analysis.break_even_occupancy)}</span>
        </div>
      </div>

      <h4>Monthly Breakdown</h4>
      <table className="monthly-table">
        <tbody>
          <tr><td>Gross Rental</td><td>{fmt(analysis.monthly.gross_rental)}</td></tr>
          <tr><td>Net Rental</td><td>{fmt(analysis.monthly.net_rental)}</td></tr>
          <tr><td>Expenses</td><td className="negative">-{fmt(analysis.monthly.expenses)}</td></tr>
          <tr><td>Tax</td><td className="negative">-{fmt(analysis.monthly.rental_tax)}</td></tr>
          <tr><td>Mortgage</td><td className="negative">-{fmt(analysis.monthly.mutuo_payment)}</td></tr>
          <tr className="total-row">
            <td>Net Cash Flow</td>
            <td className={analysis.monthly.net_cash_flow >= 0 ? 'positive' : 'negative'}>
              {fmt(analysis.monthly.net_cash_flow)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
