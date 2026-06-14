import tempfile
import unittest
from pathlib import Path

from scripts.build_context_pack import build_context_pack
from scripts.portfolio_snapshot import build_snapshot
from scripts.portfolio_utils import load_portfolio_context, read_simple_yaml
from scripts.update_asset_bundle import determine_asset_route


def write_project_files(root: Path) -> None:
    companies = root / "companies"
    companies.mkdir()
    (companies / "portfolio_profile.yaml").write_text(
        """
as_of: 2026-06-02
timezone: Asia/Seoul
total_assets_krw: 100000000
cash:
  total_cash_krw: 25000000
portfolio_policy:
  cash_is_valid_position: true
  refresh_market_data_before_current_judgment: true
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (companies / "holdings.yaml").write_text(
        """
- ticker: EXAMPLEUS
  market: US
  name: Example US Company
  asset_type: stock
  account: US_brokerage
  shares: 2
  avg_price: 100
  currency: USD
  thesis: Example US stock thesis.

- ticker: 069500.KS
  market: KR
  name: KODEX 200
  asset_type: ETF
  account: ISA
  shares: 10
  avg_price: 30000
  currency: KRW
  thesis: Example ETF accumulation thesis.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (companies / "watchlist.yaml").write_text(
        """
- ticker: EXAMPLEWATCH
  market: US
  name: Example Watchlist Company
  reason: cash flow quality watch
  status: watch
""".strip()
        + "\n",
        encoding="utf-8",
    )


class PortfolioWorkflowTest(unittest.TestCase):
    def test_simple_yaml_reads_repo_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.yaml"
            path.write_text(
                """
cash:
  total_cash_krw: 25000000
flags:
  enabled: true
holdings:
  - EXAMPLEUS
  - EXAMPLEWATCH
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = read_simple_yaml(path)

        self.assertEqual(result["cash"]["total_cash_krw"], 25000000)
        self.assertTrue(result["flags"]["enabled"])
        self.assertEqual(result["holdings"], ["EXAMPLEUS", "EXAMPLEWATCH"])

    def test_loads_portfolio_context_from_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_project_files(root)

            context = load_portfolio_context(root)

        self.assertEqual(context["profile"]["total_assets_krw"], 100000000)
        self.assertEqual([holding["ticker"] for holding in context["holdings"]], ["EXAMPLEUS", "069500.KS"])
        self.assertEqual(context["watchlist"][0]["ticker"], "EXAMPLEWATCH")

    def test_context_pack_routes_holding_stock_question_with_portfolio_awareness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_project_files(root)

            pack = build_context_pack("EXAMPLEUS 더 살까?", root=root)

        self.assertTrue(pack["portfolio_aware"])
        self.assertEqual(pack["matched_security"]["ticker"], "EXAMPLEUS")
        self.assertEqual(pack["route"]["primary_skill"], "us-stock-decision-workflow")
        self.assertIn("scripts/update_asset_bundle.py EXAMPLEUS --market US --asset-type stock", pack["route"]["local_scripts"][0])
        self.assertEqual(pack["public_equity_investing"]["role"], "supplemental")

    def test_context_pack_routes_etf_and_price_move_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_project_files(root)

            etf_pack = build_context_pack("069500.KS 추가 매수?", root=root)
            move_pack = build_context_pack("EXAMPLEUS 왜 올랐어?", root=root)

        self.assertEqual(etf_pack["route"]["primary_skill"], "etf-analysis-review")
        self.assertEqual(move_pack["route"]["primary_skill"], "market-move-explainer")

    def test_portfolio_snapshot_computes_values_weights_and_pnl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_project_files(root)

            snapshot = build_snapshot(
                root=root,
                prices={
                    "EXAMPLEUS": {"price": 125, "currency": "USD"},
                    "069500.KS": {"price": 33000, "currency": "KRW"},
                },
                usd_krw=1300,
            )

        us_stock = snapshot["positions"][0]
        korea_etf = snapshot["positions"][1]
        self.assertEqual(us_stock["current_value_krw"], 325000)
        self.assertAlmostEqual(us_stock["pnl_pct"], 25.0)
        self.assertEqual(korea_etf["current_value_krw"], 330000)
        self.assertAlmostEqual(snapshot["known_positions_value_krw"], 655000)
        self.assertAlmostEqual(us_stock["known_positions_weight_pct"], 49.62)

    def test_unified_asset_route_distinguishes_us_kr_and_etf(self):
        self.assertEqual(determine_asset_route("AAPL", "US", "stock")["pipeline"], "us_stock")
        self.assertEqual(determine_asset_route("005930.KS", "KR", "stock")["pipeline"], "kr_stock")
        self.assertEqual(determine_asset_route("069500.KS", "KR", "ETF")["pipeline"], "etf")


if __name__ == "__main__":
    unittest.main()
