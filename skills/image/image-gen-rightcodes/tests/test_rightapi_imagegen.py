import base64
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import rightapi_imagegen as adapter


class FakeResponse:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def close(self):
        pass


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.submitted = []
        self.downloaded = []

    def submit(self, payload):
        self.submitted.append(payload)
        return "task_test"

    def get_task(self, task_id):
        return self.responses.pop(0)

    def download(self, url):
        self.downloaded.append(url)
        return b"downloaded-image"


class RightAPIImagegenTests(unittest.TestCase):
    def test_endpoint_urls_strip_draw_for_task_polling(self):
        submit, task_prefix = adapter._endpoint_urls("https://www.rightapi.ai/draw")
        self.assertEqual(
            submit,
            "https://www.rightapi.ai/draw/v1/images/generations",
        )
        self.assertEqual(task_prefix, "https://www.rightapi.ai/v1/tasks")

    def test_payload_is_async_and_keeps_reference_data_urls(self):
        payload = adapter._build_payload(
            prompt="a red kite",
            model="gpt-image-2",
            n=1,
            size="16:9",
            image_size=None,
            image_data=["data:image/png;base64,abc"],
        )
        self.assertTrue(payload["async"])
        self.assertEqual(payload["image"], ["data:image/png;base64,abc"])
        self.assertEqual(payload["size"], "16:9")

    def test_poll_accepts_final_response_without_status(self):
        client = FakeClient([{"data": [{"url": "https://signed.example/image.png"}]}])
        images = adapter._poll_task(
            client,
            "task_test",
            expected_count=1,
            poll_interval=0,
            poll_timeout=1,
            sleep_fn=lambda _: None,
        )
        self.assertEqual(images, [("url", "https://signed.example/image.png")])

    def test_poll_transitions_from_processing_to_completed_base64(self):
        encoded = base64.b64encode(b"image-bytes").decode("ascii")
        client = FakeClient(
            [
                {"status": "processing"},
                {"status": "completed", "data": [{"b64_json": encoded}]},
            ]
        )
        images = adapter._poll_task(
            client,
            "task_test",
            expected_count=1,
            poll_interval=0,
            poll_timeout=1,
            sleep_fn=lambda _: None,
        )
        self.assertEqual(images, [("b64", encoded)])

    def test_poll_retries_transient_network_error(self):
        class RetryingClient(FakeClient):
            def get_task(self, task_id):
                if not self.responses:
                    raise adapter.RightAPIError("RightAPI request failed: transient TLS error")
                return self.responses.pop(0)

        client = RetryingClient([{"data": [{"url": "https://signed.example/image.png"}]}])
        original_get_task = client.get_task
        calls = 0

        def get_task_with_one_error(task_id):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise adapter.RightAPIError("RightAPI request failed: transient TLS error")
            return original_get_task(task_id)

        client.get_task = get_task_with_one_error
        images = adapter._poll_task(
            client,
            "task_test",
            expected_count=1,
            poll_interval=0,
            poll_timeout=1,
            sleep_fn=lambda _: None,
        )
        self.assertEqual(images[0][0], "url")
        self.assertEqual(calls, 2)

    def test_missing_status_and_result_is_actionable(self):
        client = FakeClient([{"task_id": "task_test"}])
        with self.assertRaisesRegex(adapter.RightAPIError, "no supported status"):
            adapter._poll_task(
                client,
                "task_test",
                expected_count=1,
                poll_interval=0,
                poll_timeout=1,
                sleep_fn=lambda _: None,
            )

    def test_write_images_supports_url_and_base64(self):
        encoded = base64.b64encode(b"base64-image").decode("ascii")
        client = FakeClient([])
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / "url.png", Path(directory) / "b64.png"]
            adapter._write_images(
                client,
                [("url", "https://signed.example/image.png"), ("b64", encoded)],
                paths,
                force=False,
            )
            self.assertEqual(paths[0].read_bytes(), b"downloaded-image")
            self.assertEqual(paths[1].read_bytes(), b"base64-image")
            self.assertEqual(client.downloaded, ["https://signed.example/image.png"])

    def test_dry_run_does_not_require_api_key(self):
        with patch.dict(
            os.environ,
            {
                "OPENAI_SUB_BASE_URL": "",
                "OPENAI_SUB_KEY": "",
                "OPENAI_SUB_IMAGE_MODEL": "",
            },
            clear=False,
        ), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            result = adapter.main(
                [
                    "generate",
                    "--prompt",
                    "a small blue house",
                    "--model",
                    "gpt-image-2",
                    "--dry-run",
                ]
            )
        self.assertEqual(result, 0)
        output = json.loads(stdout.getvalue())
        self.assertTrue(output["async"])
        self.assertEqual(output["endpoint"], "/v1/images/generations")

    def test_batch_dry_run_reads_prompt_file_without_top_level_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs = Path(directory) / "prompts.jsonl"
            jobs.write_text(
                json.dumps({"prompt": "a quiet lake at dawn"}) + "\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "OPENAI_SUB_BASE_URL": "",
                    "OPENAI_SUB_KEY": "",
                    "OPENAI_SUB_IMAGE_MODEL": "",
                },
                clear=False,
            ), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                result = adapter.main(
                    [
                        "generate-batch",
                        "--input",
                        str(jobs),
                        "--out-dir",
                        str(Path(directory) / "out"),
                        "--dry-run",
                    ]
                )
        self.assertEqual(result, 0)
        self.assertIn('"async": true', stdout.getvalue())
        self.assertIn("image_1.png", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
