from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import install_skill  # noqa: E402
import package_release  # noqa: E402
import run  # noqa: E402
from organize_script import (  # noqa: E402
    content_without_whitespace,
    create_calibrated_spoken_script,
    create_spoken_script,
    load_calibration_glossary,
    replacement_only,
)


class CoreTests(unittest.TestCase):
    def test_safe_defaults_require_consent(self) -> None:
        args = run.build_parser().parse_args(["sample.srt"])
        self.assertEqual(args.cookies, "none")
        self.assertEqual(args.install, "ask")
        self.assertEqual(args.model_download, "ask")
        self.assertFalse(args.no_resume)
        cookie_action = next(action for action in run.build_parser()._actions if action.dest == "cookies")
        self.assertNotIn("auto", cookie_action.choices)

    def test_browser_cookie_choice_never_enumerates_other_browsers(self) -> None:
        self.assertEqual(run.browser_candidates("chrome"), ["chrome"])
        self.assertEqual(run.browser_candidates("none"), [None])

    def test_prepared_runtime_is_reused_without_install_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_dir = Path(temp) / "runtime"
            python = run.runtime_python(runtime_dir)
            python.parent.mkdir(parents=True)
            python.touch()
            args = run.build_parser().parse_args(["sample.wav", "--runtime-dir", str(runtime_dir)])
            completed = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch.object(run, "module_available", return_value=False), mock.patch.object(
                run.subprocess, "run", side_effect=[completed, completed]
            ) as execute:
                with self.assertRaises(SystemExit) as stopped:
                    run.ensure_modules(["yt_dlp"], args)
            self.assertEqual(stopped.exception.code, 0)
            self.assertEqual(execute.call_count, 2)

    def test_cookie_file_is_filtered_to_target_platform(self) -> None:
        content = """# Netscape HTTP Cookie File
.xiaohongshu.com\tTRUE\t/\tTRUE\t0\ta1\tvalue1
#HttpOnly_.xhslink.com\tTRUE\t/\tTRUE\t0\ta3\tvalue3
"""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "cookies.txt"
            source.write_text(content, encoding="utf-8")
            scoped, report = run.create_scoped_cookie_file(
                source, "https://www.xiaohongshu.com/explore/123", root / "out"
            )
            scoped_text = scoped.read_text(encoding="utf-8")
            self.assertIn("value1", scoped_text)
            self.assertIn("value3", scoped_text)
            self.assertEqual(scoped, source)
            self.assertEqual(report["included_cookie_count"], 2)
            self.assertEqual(report["excluded_cookie_count"], 0)
            self.assertTrue(report["user_managed_cookie_file"])
            run.cleanup_scoped_cookie_file(scoped)
            self.assertTrue(scoped.exists())

    def test_mixed_cookie_file_is_rejected_instead_of_copied(self) -> None:
        content = """# Netscape HTTP Cookie File
.xiaohongshu.com\tTRUE\t/\tTRUE\t0\ta1\tvalue1
.google.com\tTRUE\t/\tTRUE\t0\ta2\tvalue2
"""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "cookies.txt"
            source.write_text(content, encoding="utf-8")
            with self.assertRaises(run.WorkflowError) as raised:
                run.create_scoped_cookie_file(source, "https://www.xiaohongshu.com/explore/123", root / "out")
            self.assertEqual(raised.exception.code, "COOKIE_SCOPE_MIXED")

    def test_download_errors_have_terminal_routes(self) -> None:
        auth = run.classify_download_failure("HTTP Error 403: login required; use fresh cookies")
        unsupported = run.classify_download_failure("Unsupported URL")
        self.assertEqual(auth.code, "AUTH_REQUIRED")
        self.assertEqual(auth.next_action, "provide_local_media_exported_from_an_authorized_browser_session")
        self.assertEqual(unsupported.code, "UNSUPPORTED_URL")
        self.assertEqual(unsupported.next_action, "provide_local_media_exported_from_an_authorized_browser_session")

    def test_subtitle_url_skips_media_download_by_default(self) -> None:
        args = run.build_parser().parse_args(["https://example.com/video"])
        self.assertFalse(run.media_download_required(Path("source.srt"), args))
        self.assertTrue(run.media_download_required(None, args))

        mp3_args = run.build_parser().parse_args(["https://example.com/video", "--extract-mp3"])
        self.assertTrue(run.media_download_required(Path("source.srt"), mp3_args))

        video_args = run.build_parser().parse_args(["https://example.com/video", "--download-mode", "video"])
        self.assertTrue(run.media_download_required(Path("source.srt"), video_args))

    def test_share_text_url_normalization(self) -> None:
        value, is_url = run.normalize_input("复制链接 https://bilibili.com/video/BV123?token=abc 打开")
        self.assertTrue(is_url)
        self.assertEqual(value, "https://www.bilibili.com/video/BV123?token=abc")

    def test_existing_relative_media_name_is_not_mistaken_for_a_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            previous = Path.cwd()
            try:
                os.chdir(temp)
                Path("sample.srt").write_text("", encoding="utf-8")
                value, is_url = run.normalize_input("sample.srt")
            finally:
                os.chdir(previous)
        self.assertFalse(is_url)
        self.assertEqual(Path(value).name, "sample.srt")

    def test_redacts_sensitive_and_long_random_query_values(self) -> None:
        value = run.redact_url(
            "https://example.com/watch?id=7&xsec_token=secret&ref=abcdefghijklmnopqrstuvwxyz1234567890"
        )
        self.assertIn("id=7", value)
        self.assertNotIn("secret", value)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890", value)

    def test_blocks_loopback_url(self) -> None:
        with self.assertRaises(RuntimeError):
            run.validate_public_url("http://127.0.0.1/private")

    def test_bilibili_ai_track_is_automatic_even_when_listed_as_subtitle(self) -> None:
        language, kind, source_key = run.choose_subtitle(
            {"subtitles": {"ai-zh": [{"ext": "srt"}]}}, "auto"
        )
        self.assertEqual((language, kind, source_key), ("ai-zh", "automatic", "subtitles"))

    def test_spoken_script_preserves_every_non_whitespace_character(self) -> None:
        segments = [
            {"start": 0, "end": 1, "text": "大家好， 我是小王。"},
            {"start": 1, "end": 2, "text": "嗯……再说一遍！"},
            {"start": 2, "end": 3, "text": "记得点赞、关注。"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "spoken.txt"
            report_path = Path(temp) / "faithfulness.json"
            report = create_spoken_script(segments, output, report_path, 2)
            source = "".join(segment["text"].strip() for segment in segments)
            self.assertTrue(report["exact_match_ignoring_whitespace"])
            self.assertEqual(
                content_without_whitespace(source),
                content_without_whitespace(output.read_text(encoding="utf-8")),
            )

    def test_calibrated_script_only_allows_substitutions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "spoken.txt"
            source.write_text("這個視頻講蘇格拉蒂。\n", encoding="utf-8")
            glossary = root / "glossary.json"
            glossary.write_text(json.dumps({"苏格拉蒂": "苏格拉底"}, ensure_ascii=False), encoding="utf-8")
            output = root / "calibrated.txt"
            report_path = root / "calibration.json"

            report = create_calibrated_spoken_script(source, output, report_path, "zh-hans", glossary)

            self.assertEqual(output.read_text(encoding="utf-8"), "这个视频讲苏格拉底。\n")
            self.assertTrue(report["replacement_only_ignoring_whitespace"])
            self.assertGreater(report["changed_character_count"], 0)
            self.assertEqual(
                len(content_without_whitespace(source.read_text(encoding="utf-8"))),
                len(content_without_whitespace(output.read_text(encoding="utf-8"))),
            )

    def test_calibration_glossary_rejects_insertions_and_deletions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            glossary = Path(temp) / "glossary.json"
            glossary.write_text(json.dumps({"罗翔": "罗翔老师"}, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_calibration_glossary(glossary)

    def test_replacement_guard_rejects_insertions(self) -> None:
        self.assertTrue(replacement_only("苏格拉蒂", "苏格拉底"))
        self.assertFalse(replacement_only("罗翔", "罗翔老师"))

    def test_local_srt_end_to_end_needs_no_third_party_dependency(self) -> None:
        srt = """1
00:00:00,000 --> 00:00:01,000
你好，世界。

2
00:00:01,000 --> 00:00:02,000
你好，世界。请关注。
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "sample.srt"
            source.write_text(srt, encoding="utf-8")
            output = temp_path / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "run.py"),
                    str(source),
                    "--output-dir",
                    str(output),
                    "--min-free-space-mb",
                    "0",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((output / "faithfulness.json").read_text(encoding="utf-8"))
            self.assertTrue(report["exact_match_ignoring_whitespace"])
            metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["input"], "sample.srt")
            self.assertEqual(metadata["normalized_input"], "sample.srt")
            spoken = content_without_whitespace((output / "spoken-script.txt").read_text(encoding="utf-8"))
            self.assertEqual(spoken, "你好，世界。你好，世界。请关注。")
            resumed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "run.py"),
                    str(source),
                    "--output-dir",
                    str(output),
                    "--min-free-space-mb",
                    "0",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn('"resumed": true', resumed.stdout)

    def test_installer_copies_only_skill_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = install_skill.install_one(Path(temp) / "skills", force=False)
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertTrue((destination / "scripts" / "run.py").is_file())
            self.assertTrue((destination / "scripts" / "setup.py").is_file())
            self.assertFalse((destination / "README.md").exists())
            self.assertFalse((destination / "tests").exists())

    def test_installer_updates_in_place_without_deleting_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = install_skill.install_one(Path(temp) / "skills", force=False)
            user_file = destination / "user-note.txt"
            user_file.write_text("keep me", encoding="utf-8")
            destination_again = install_skill.install_one(Path(temp) / "skills", force=True)
            self.assertEqual(destination_again, destination)
            self.assertEqual(user_file.read_text(encoding="utf-8"), "keep me")
            self.assertTrue((destination / "SKILL.md").is_file())

    def test_auto_install_selects_one_preferred_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            roots = {
                "agents": base / ".agents" / "skills",
                "codex": base / ".codex" / "skills",
                "workbuddy": base / ".workbuddy" / "skills",
            }
            for root in roots.values():
                root.parent.mkdir(parents=True)
            with mock.patch.object(install_skill, "host_roots", return_value=roots):
                self.assertEqual(install_skill.select_roots("auto"), [roots["workbuddy"]])

    def test_release_package_has_root_folder_and_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "release.zip"
            archive_path, checksum_path = package_release.build(archive)
            self.assertTrue(archive_path.is_file())
            self.assertTrue(checksum_path.is_file())
            import zipfile

            with zipfile.ZipFile(archive_path) as bundle:
                names = set(bundle.namelist())
            self.assertIn("video-audio-transcribe/SKILL.md", names)
            self.assertIn("video-audio-transcribe/scripts/setup.py", names)
            self.assertNotIn("video-audio-transcribe/tests/test_core.py", names)


if __name__ == "__main__":
    unittest.main()
