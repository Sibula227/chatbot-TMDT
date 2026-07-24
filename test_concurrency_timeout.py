import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import requests
from fastapi.testclient import TestClient

import main
import recommendation


def sample_products():
    return [
        {
            "id": 1,
            "name": "Phone Alpha",
            "category": "phone",
            "brand": "SOPE",
            "price": 10_000_000,
            "status": "ACTIVE",
            "availableQuantity": 5,
            "inStock": True,
        },
        {
            "id": 2,
            "name": "Phone Beta",
            "category": "phone",
            "brand": "SOPE",
            "price": 11_000_000,
            "status": "ACTIVE",
            "availableQuantity": 4,
            "inStock": True,
        },
        {
            "id": 3,
            "name": "Phone Gamma",
            "category": "phone",
            "brand": "Other",
            "price": 12_000_000,
            "status": "ACTIVE",
            "availableQuantity": 3,
            "inStock": True,
        },
    ]


class CbfConcurrencyTests(unittest.TestCase):
    def setUp(self):
        recommendation.invalidate_cbf_cache()

    def tearDown(self):
        recommendation.invalidate_cbf_cache()

    def test_cache_hit_does_not_fetch_or_rebuild(self):
        with (
            patch(
                "recommendation.fetch_all_products",
                return_value=sample_products(),
            ) as fetch,
            patch(
                "recommendation._build_cbf_artifacts",
                wraps=recommendation._build_cbf_artifacts,
            ) as build,
        ):
            first = recommendation.get_content_based_similar_products(1, 2)
            second = recommendation.get_content_based_similar_products(1, 2)

        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(build.call_count, 1)

    def test_two_concurrent_requests_only_build_once(self):
        builder_started = threading.Event()
        allow_builder_to_finish = threading.Event()
        fetch_count = 0
        count_lock = threading.Lock()

        def slow_fetch():
            nonlocal fetch_count
            with count_lock:
                fetch_count += 1
            builder_started.set()
            self.assertTrue(allow_builder_to_finish.wait(timeout=2))
            return sample_products()

        with patch("recommendation.fetch_all_products", side_effect=slow_fetch):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(
                    recommendation.get_content_based_similar_products, 1, 2
                )
                self.assertTrue(builder_started.wait(timeout=1))
                second = executor.submit(
                    recommendation.get_content_based_similar_products, 1, 2
                )
                time.sleep(0.05)
                allow_builder_to_finish.set()
                first_result = first.result(timeout=2)
                second_result = second.result(timeout=2)

        self.assertEqual(fetch_count, 1)
        self.assertEqual(first_result, second_result)
        self.assertFalse(recommendation._cbf_cache["building"])

    def test_lightweight_specification_summary_is_used_by_cbf(self):
        product = sample_products()[0] | {
            "specificationSummary": "Chip xử lý: SOPE X1; RAM: 8 GB"
        }

        description = recommendation.build_product_description(product)

        self.assertIn("chip xu ly: sope x1", description)
        self.assertIn("ram: 8 gb", description)


class NetworkFallbackTests(unittest.TestCase):
    def fake_gemini_client(self):
        response = SimpleNamespace(text="Đây là phản hồi thử nghiệm.")
        generate_content = AsyncMock(return_value=response)
        return SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(generate_content=generate_content)
            )
        )

    def test_catalog_timeout_returns_empty_without_hanging(self):
        started = time.monotonic()
        with patch(
            "recommendation.requests.get",
            side_effect=requests.exceptions.ReadTimeout(),
        ):
            result = recommendation.fetch_all_products()

        self.assertEqual(result, [])
        self.assertLess(time.monotonic() - started, 0.5)

    def test_chat_catalog_failure_keeps_json_contract(self):
        previous_api_key = main.api_key
        main.api_key = "test-key"
        try:
            with (
                patch("main.load_products_from_backend", return_value=[]),
                TestClient(main.app) as client,
            ):
                response = client.post(
                    "/api/chat",
                    json={"user_id": "test", "message": "Gợi ý điện thoại"},
                )
        finally:
            main.api_key = previous_api_key

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertIsInstance(response.json()["reply"], str)

    def test_two_product_chat_requests_keep_returning_json(self):
        with (
            patch.object(main, "api_key", "test-key"),
            patch.object(main, "gemini_client", self.fake_gemini_client()),
            patch("main.load_products_from_backend", return_value=sample_products()),
            patch("main.save_chat_to_springboot", new_callable=AsyncMock),
            TestClient(main.app) as client,
        ):
            first = client.post(
                "/api/chat",
                json={"user_id": "test", "message": "Tư vấn cho tôi Phone Alpha"},
            )
            second = client.post(
                "/api/chat",
                json={"user_id": "test", "message": "Điện thoại nào có camera tốt?"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["status"], "success")
        self.assertEqual(second.json()["status"], "success")

    def test_recommendation_route_schema(self):
        with (
            patch(
                "recommendation.get_content_based_similar_products",
                return_value=[2, 3],
            ),
            TestClient(main.app) as client,
        ):
            response = client.get("/api/ai/recommend/content-based/1?top_n=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "success", "product_ids": [2, 3]},
        )

    def test_chat_prompt_uses_lightweight_specification_summary(self):
        product = sample_products()[0] | {
            "specificationSummary": "Chip xử lý: SOPE X1; RAM: 8 GB"
        }

        prompt_item = main.product_to_prompt_item(product)

        self.assertEqual(prompt_item["Chip xử lý"], "SOPE X1")
        self.assertIn("RAM: 8 GB", prompt_item["Cấu hình"])

    def test_health_remains_fast_while_cbf_builds(self):
        recommendation.invalidate_cbf_cache()
        builder_started = threading.Event()
        allow_builder_to_finish = threading.Event()

        def slow_fetch():
            builder_started.set()
            self.assertTrue(allow_builder_to_finish.wait(timeout=2))
            return sample_products()

        with (
            patch("recommendation.fetch_all_products", side_effect=slow_fetch),
            TestClient(main.app) as client,
            ThreadPoolExecutor(max_workers=1) as executor,
        ):
            recommendation_request = executor.submit(
                client.get, "/api/ai/recommend/content-based/1"
            )
            self.assertTrue(builder_started.wait(timeout=1))
            started = time.monotonic()
            health_response = client.get("/health")
            elapsed = time.monotonic() - started
            allow_builder_to_finish.set()
            recommendation_response = recommendation_request.result(timeout=2)

        self.assertEqual(health_response.status_code, 200)
        self.assertLess(elapsed, 0.5)
        self.assertEqual(recommendation_response.status_code, 200)

    def test_chat_remains_available_while_cbf_builds(self):
        recommendation.invalidate_cbf_cache()
        builder_started = threading.Event()
        allow_builder_to_finish = threading.Event()

        def slow_fetch():
            builder_started.set()
            self.assertTrue(allow_builder_to_finish.wait(timeout=2))
            return sample_products()

        with (
            patch("recommendation.fetch_all_products", side_effect=slow_fetch),
            patch.object(main, "api_key", "test-key"),
            patch.object(main, "gemini_client", self.fake_gemini_client()),
            patch("main.load_products_from_backend", return_value=sample_products()),
            patch("main.save_chat_to_springboot", new_callable=AsyncMock),
            TestClient(main.app) as client,
            ThreadPoolExecutor(max_workers=1) as executor,
        ):
            recommendation_request = executor.submit(
                client.get, "/api/ai/recommend/content-based/1"
            )
            self.assertTrue(builder_started.wait(timeout=1))
            chat_response = client.post(
                "/api/chat",
                json={"user_id": "test", "message": "Tư vấn cho tôi Phone Alpha"},
            )
            allow_builder_to_finish.set()
            recommendation_response = recommendation_request.result(timeout=2)

        self.assertEqual(chat_response.status_code, 200)
        self.assertEqual(chat_response.json()["status"], "success")
        self.assertEqual(recommendation_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
