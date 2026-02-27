# ABOUTME: Flask JSON API for browsing OMI zones, running financial analysis, and managing Airbnb scrapes.
# ABOUTME: Single-user tool with background scrape threads and SQLite-backed caching.

import threading
import uuid

from flask import Flask, jsonify, request

from src.airbnb_scraper import search_area
from src.database import (
    create_job,
    get_job,
    get_listings,
    init_db,
    save_listings,
    update_job,
)
from src.financial_model import (
    AcquisitionCosts,
    AnnualCosts,
    PropertyInvestment,
    RentalIncome,
)
from src.omi_data import get_provinces, get_regions, query_zones
from src.str_metrics import init_str_metrics_table, update_zone_str_metrics
from src.zone_sampler import (
    get_zones_to_sample,
    init_sampling_tables,
    sample_zone,
)

# State for the background zone sampling job
_sampling_active = False
_sampling_job_id: str | None = None


def create_app(db_path: str) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path
    init_db(db_path)
    init_sampling_tables(db_path)
    init_str_metrics_table(db_path)

    @app.route("/api/zones")
    def zones():
        import sqlite3 as _sqlite3

        region = request.args.get("region")
        province = request.args.get("province")
        max_price = request.args.get("max_price", type=float)
        min_rent = request.args.get("min_rent", type=float)

        results = query_zones(
            db_path,
            region=region,
            province=province,
            max_buy_price_sqm=max_price,
            min_rent_sqm=min_rent,
        )

        # Attach STR data availability flag
        conn = _sqlite3.connect(db_path)
        sampled = {
            row[0]
            for row in conn.execute("SELECT link_zona FROM zone_str_metrics").fetchall()
        }
        conn.close()

        for zone in results:
            zone["has_str_data"] = zone.get("link_zona") in sampled

        return jsonify(results)

    @app.route("/api/zones/regions")
    def regions():
        return jsonify(get_regions(db_path))

    @app.route("/api/zones/provinces")
    def provinces():
        region = request.args.get("region")
        if not region:
            return jsonify({"error": "region parameter required"}), 400
        return jsonify(get_provinces(db_path, region))

    @app.route("/api/analysis")
    def analysis():
        try:
            purchase_price = float(request.args["purchase_price"])
            square_meters = float(request.args["square_meters"])
            nightly_rate = float(request.args["nightly_rate"])
            occupancy_rate = float(request.args["occupancy_rate"])
        except (KeyError, ValueError):
            return jsonify({"error": "Required: purchase_price, square_meters, nightly_rate, occupancy_rate"}), 400

        # Optional params with defaults
        down_payment_pct = float(request.args.get("down_payment_pct", 0.20))
        mutuo_rate = float(request.args.get("mutuo_rate", 0.04))
        mutuo_term = int(request.args.get("mutuo_term", 20))
        cleaning_fee = float(request.args.get("cleaning_fee", 50))
        management_fee_pct = float(request.args.get("management_fee_pct", 0.20))
        platform_fee_pct = float(request.args.get("platform_fee_pct", 0.15))
        avg_stay_nights = int(request.args.get("avg_stay_nights", 4))
        cedolare_secca_rate = float(request.args.get("cedolare_secca_rate", 0.21))

        invest = PropertyInvestment(
            purchase_price=purchase_price,
            square_meters=square_meters,
            down_payment_pct=down_payment_pct,
            mutuo_rate_annual=mutuo_rate,
            mutuo_term_years=mutuo_term,
            acquisition=AcquisitionCosts(
                registro_pct=0.09,
                notary_fee=2500.0,
                agency_fee_pct=0.03,
            ),
            annual_costs=AnnualCosts(
                imu=1200.0,
                tari=300.0,
                maintenance_pct=0.01,
                insurance=400.0,
                condo_fees_monthly=50.0,
                utilities_monthly=150.0,
            ),
            rental_income=RentalIncome(
                nightly_rate=nightly_rate,
                occupancy_rate=occupancy_rate,
                cleaning_fee=cleaning_fee,
                management_fee_pct=management_fee_pct,
                platform_fee_pct=platform_fee_pct,
                avg_stay_nights=avg_stay_nights,
            ),
            cedolare_secca_rate=cedolare_secca_rate,
        )

        return jsonify({
            "purchase_price": invest.purchase_price,
            "total_cash_outlay": invest.total_cash_outlay,
            "gross_rental_income": invest.gross_rental_income_annual,
            "net_rental_income": invest.net_rental_income_annual,
            "annual_expenses": invest.annual_expenses,
            "rental_income_tax": invest.rental_income_tax,
            "annual_cash_flow": invest.annual_cash_flow,
            "cap_rate": invest.cap_rate,
            "cash_on_cash_return": invest.cash_on_cash_return,
            "break_even_occupancy": invest.break_even_occupancy,
            "monthly": invest.monthly_summary(),
        })

    @app.route("/api/scrape/airbnb", methods=["POST"])
    def start_scrape():
        data = request.get_json() or {}
        query = data.get("query")
        checkin = data.get("checkin")
        checkout = data.get("checkout")
        if not all([query, checkin, checkout]):
            return jsonify({"error": "Required: query, checkin, checkout"}), 400

        job_id = create_job(db_path, query, checkin, checkout)

        def run_scrape():
            update_job(db_path, job_id, status="running")
            try:
                listings = search_area(query, checkin, checkout)
                save_listings(db_path, query, listings)
                update_job(db_path, job_id, status="completed", result_count=len(listings))
            except Exception as e:
                update_job(db_path, job_id, status="failed", error=str(e))

        thread = threading.Thread(target=run_scrape, daemon=True)
        thread.start()

        return jsonify({"job_id": job_id})

    @app.route("/api/scrape/airbnb/<job_id>")
    def scrape_status(job_id):
        job = get_job(db_path, job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job)

    @app.route("/api/airbnb-listings")
    def airbnb_listings():
        query = request.args.get("query")
        if not query:
            return jsonify({"error": "query parameter required"}), 400
        return jsonify(get_listings(db_path, query))

    @app.route("/api/sample/start", methods=["POST"])
    def sample_start():
        global _sampling_active, _sampling_job_id

        data = request.get_json() or {}
        province = data.get("province")
        region = data.get("region")

        if not province and not region:
            return jsonify({"error": "Required: province or region"}), 400

        zones = get_zones_to_sample(db_path, province=province, region=region)
        if not zones:
            return jsonify({"job_id": None, "zones_queued": 0, "message": "No unsampled zones with bounding box found"})

        job_id = uuid.uuid4().hex[:12]
        _sampling_job_id = job_id
        _sampling_active = True

        def run_sampling():
            global _sampling_active
            for zone in zones:
                if not _sampling_active:
                    break
                sample_zone(db_path, zone)
                update_zone_str_metrics(db_path, zone["link_zona"])
            _sampling_active = False

        thread = threading.Thread(target=run_sampling, daemon=True)
        thread.start()

        return jsonify({"job_id": job_id, "zones_queued": len(zones)})

    @app.route("/api/sample/status")
    def sample_status():
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(db_path)
        sampled = conn.execute("SELECT COUNT(*) FROM zone_sampling_status").fetchone()[0]
        # Count zones with bounding boxes (column added by load_zone_bboxes; may not exist yet)
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM omi_zones WHERE ne_lat IS NOT NULL"
            ).fetchone()[0]
        except Exception:
            total = conn.execute("SELECT COUNT(*) FROM omi_zones").fetchone()[0]
        conn.close()
        return jsonify({
            "active": _sampling_active,
            "job_id": _sampling_job_id,
            "sampled": sampled,
            "total": total,
        })

    @app.route("/api/sample/stop", methods=["POST"])
    def sample_stop():
        global _sampling_active
        _sampling_active = False
        return jsonify({"stopped": True})

    return app
