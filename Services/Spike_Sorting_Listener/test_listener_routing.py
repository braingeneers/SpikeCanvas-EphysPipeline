#!/usr/bin/env python3
"""Focused tests for listener routing without runtime cluster dependencies."""

import io
import json
import logging
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


SRC_DIR = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, SRC_DIR)


def install_runtime_mocks():
    braingeneers = types.ModuleType("braingeneers")
    braingeneers.iot = types.ModuleType("braingeneers.iot")
    braingeneers.iot.messaging = types.ModuleType("braingeneers.iot.messaging")
    braingeneers.iot.messaging.MessageBroker = type("MessageBroker", (), {})
    braingeneers.utils = types.ModuleType("braingeneers.utils")
    braingeneers.utils.s3wrangler = types.ModuleType("braingeneers.utils.s3wrangler")
    braingeneers.utils.smart_open_braingeneers = types.ModuleType(
        "braingeneers.utils.smart_open_braingeneers"
    )

    kubernetes = types.ModuleType("kubernetes")
    kubernetes.client = types.ModuleType("kubernetes.client")
    kubernetes.config = types.ModuleType("kubernetes.config")

    modules = {
        "braingeneers": braingeneers,
        "braingeneers.iot": braingeneers.iot,
        "braingeneers.iot.messaging": braingeneers.iot.messaging,
        "braingeneers.utils": braingeneers.utils,
        "braingeneers.utils.s3wrangler": braingeneers.utils.s3wrangler,
        "braingeneers.utils.smart_open_braingeneers": braingeneers.utils.smart_open_braingeneers,
        "kubernetes": kubernetes,
        "kubernetes.client": kubernetes.client,
        "kubernetes.config": kubernetes.config,
        "k8s_kilosort2": MagicMock(),
    }
    sys.modules.update(modules)


install_runtime_mocks()
with patch.object(logging, "FileHandler", lambda *args, **kwargs: logging.NullHandler()):
    import mqtt_listener
    import splitter_fanout


class FakeOpen:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return io.StringIO(json.dumps(self.payload))

    def __exit__(self, *args):
        return False


class MetadataDetectionTests(unittest.TestCase):
    def test_dict_metadata_detects_max2_as_maxtwo(self):
        metadata = {
            "ephys_experiments": {
                "rec": {
                    "data_format": "max2",
                    "blocks": [{"path": "original/data/recording.raw.h5"}],
                }
            }
        }
        with patch.object(mqtt_listener.smart_open, "open", lambda *args, **kwargs: FakeOpen(metadata)):
            result = mqtt_listener.get_data_format_for_file(
                "s3://braingeneers/ephys/test-uuid/original/data/recording.raw.h5"
            )
        self.assertEqual(result, "maxtwo")

    def test_list_metadata_detects_maxtwo(self):
        metadata = {
            "ephys_experiments": [
                {
                    "data_format": "maxtwo",
                    "blocks": [{"path": "original/data/recording.raw.h5"}],
                }
            ]
        }
        with patch.object(mqtt_listener.smart_open, "open", lambda *args, **kwargs: FakeOpen(metadata)):
            result = mqtt_listener.get_data_format_for_file(
                "s3://braingeneers/ephys/test-uuid/original/data/recording.raw.h5"
            )
        self.assertEqual(result, "maxtwo")

    def test_cache_split_path_matches_original_metadata_block(self):
        metadata = {
            "ephys_experiments": {
                "rec": {
                    "data_format": "maxtwo",
                    "blocks": [{"path": "original/data/recording.raw.h5"}],
                }
            }
        }
        with patch.object(mqtt_listener.smart_open, "open", lambda *args, **kwargs: FakeOpen(metadata)):
            result = mqtt_listener.get_data_format_for_file(
                "s3://braingeneersdev/cache/ephys/test-uuid/original/data/recording_well001.raw.h5"
            )
        self.assertEqual(result, "maxtwo")

    def test_unmatched_metadata_returns_unknown(self):
        metadata = {
            "ephys_experiments": {
                "rec": {
                    "data_format": "maxone",
                    "blocks": [{"path": "original/data/other.raw.h5"}],
                }
            }
        }
        with patch.object(mqtt_listener.smart_open, "open", lambda *args, **kwargs: FakeOpen(metadata)):
            result = mqtt_listener.get_data_format_for_file(
                "s3://braingeneers/ephys/test-uuid/original/data/recording.raw.h5"
            )
        self.assertEqual(result, "")


class CsvLaunchRoutingTests(unittest.TestCase):
    def base_row(self):
        return {
            "index": "1",
            "uuid": "2026-01-01-e-test",
            "experiment": "recording.raw.h5",
            "args": "./run.sh",
        }

    def test_csv_maxtwo_launches_splitter_only(self):
        with patch.object(mqtt_listener, "get_data_format_for_file", return_value="maxtwo"), \
             patch.object(mqtt_listener, "get_splitter_config", return_value={"split": "cfg"}), \
             patch.object(mqtt_listener, "get_sorter_template", return_value={"sorter": "tpl"}), \
             patch.object(mqtt_listener, "spawn_splitter_fanout") as spawn_splitter, \
             patch.object(mqtt_listener, "create_kube_job") as create_kube:
            launched = mqtt_listener.launch_job_csv("jobs.csv", self.base_row())

        self.assertTrue(launched)
        spawn_splitter.assert_called_once()
        create_kube.assert_not_called()

    def test_csv_known_non_maxtwo_launches_sorter_directly(self):
        with patch.object(mqtt_listener, "get_data_format_for_file", return_value="maxone"), \
             patch.object(mqtt_listener, "spawn_splitter_fanout") as spawn_splitter, \
             patch.object(mqtt_listener, "create_kube_job", return_value=0) as create_kube:
            launched = mqtt_listener.launch_job_csv("jobs.csv", self.base_row())

        self.assertTrue(launched)
        spawn_splitter.assert_not_called()
        create_kube.assert_called_once()

    def test_csv_unknown_h5_fails_closed(self):
        with patch.object(mqtt_listener, "get_data_format_for_file", return_value=""), \
             patch.object(mqtt_listener, "spawn_splitter_fanout") as spawn_splitter, \
             patch.object(mqtt_listener, "create_kube_job") as create_kube:
            launched = mqtt_listener.launch_job_csv("jobs.csv", self.base_row())

        self.assertFalse(launched)
        spawn_splitter.assert_not_called()
        create_kube.assert_not_called()

    def test_csv_unknown_nwb_launches_sorter_directly(self):
        row = self.base_row()
        row["experiment"] = "recording.nwb"
        with patch.object(mqtt_listener, "get_data_format_for_file", return_value=""), \
             patch.object(mqtt_listener, "spawn_splitter_fanout") as spawn_splitter, \
             patch.object(mqtt_listener, "create_kube_job", return_value=0) as create_kube:
            launched = mqtt_listener.launch_job_csv("jobs.csv", row)

        self.assertTrue(launched)
        spawn_splitter.assert_not_called()
        create_kube.assert_called_once()


class JobNameTests(unittest.TestCase):
    def test_splitter_job_names_include_recording_context_and_fit_k8s_limit(self):
        first = splitter_fanout._build_splitter_job_name(
            "2026-01-01-e-long-dataset-name",
            "recording-alpha.raw",
        )
        second = splitter_fanout._build_splitter_job_name(
            "2026-01-01-e-long-dataset-name",
            "recording-beta.raw",
        )
        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first), 63)
        self.assertRegex(first, r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

    def test_well_job_names_include_well_and_fit_k8s_limit(self):
        name = splitter_fanout._build_well_job_name(
            "2026-01-01-e-long-dataset-name",
            "recording-alpha.raw",
            "well001",
        )
        self.assertIn("well001", name)
        self.assertLessEqual(len(name), 63)
        self.assertRegex(name, r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


if __name__ == "__main__":
    unittest.main()
