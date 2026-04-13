import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKFILL_ENTRIES = REPO_ROOT / "scripts" / "backfill_entries_to_journal.py"
COMMIT_INGRESS = REPO_ROOT / "scripts" / "commit_ingress.py"
MATERIALIZE = REPO_ROOT / "scripts" / "materialize_notes.sh"
REPARTITION_JOURNAL = REPO_ROOT / "scripts" / "repartition_journal.py"
PROCESS_INBOX = REPO_ROOT / "scripts" / "process_inbox.sh"
IMPORT_LEGACY = REPO_ROOT / "scripts" / "import_legacy_notes.py"
QUICKNOTE = REPO_ROOT / "quicknote.swift"
SETUP = REPO_ROOT / "setup.sh"
IOS_README = REPO_ROOT / "mobile" / "ios" / "README.md"
README = REPO_ROOT / "README.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
ARCHITECTURE_V2 = REPO_ROOT / "docs" / "architecture-v2.md"


class NotesCaptureTestCase(unittest.TestCase):
    maxDiff = None

    def run_cmd(self, *args, cwd=None, env=None):
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            list(args),
            cwd=cwd or REPO_ROOT,
            env=merged_env,
            text=True,
            capture_output=True,
            check=True,
        )

    def make_data_dir(self, root: Path) -> Path:
        data_dir = root / "data"
        (data_dir / "entries").mkdir(parents=True, exist_ok=True)
        (data_dir / "ingress" / "dropbox").mkdir(parents=True, exist_ok=True)
        (data_dir / "ingress" / "local").mkdir(parents=True, exist_ok=True)
        return data_dir

    def read_journal_events(self, data_dir: Path):
        events = []
        for journal_file in sorted((data_dir / "journal").rglob("*.ndjson")):
            for line in journal_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
        return events

    def test_materialize_notes_creates_timeline_from_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            journal_day = data_dir / "journal" / "2026" / "03"
            journal_day.mkdir(parents=True, exist_ok=True)

            events = [
                {
                    "schema_version": 1,
                    "event_id": "evt-2",
                    "kind": "note.capture",
                    "captured_at": "2026-03-13T09:32:00+05:30",
                    "received_at": "2026-03-13T09:32:01+05:30",
                    "producer": {"type": "mobile-file-drop", "id": "iphone"},
                    "content": {"mime_type": "text/plain", "text": "Second note\nwith two lines"},
                    "metadata": {},
                    "blobs": [],
                    "parents": [],
                    "ingress": {"transport": "dropbox-file-drop", "path": "ingress/dropbox/a.txt"},
                },
                {
                    "schema_version": 1,
                    "event_id": "evt-1",
                    "kind": "note.capture",
                    "captured_at": "2026-03-13T09:30:00+05:30",
                    "received_at": "2026-03-13T09:30:05+05:30",
                    "producer": {"type": "mac-hotkey", "id": "mba"},
                    "content": {"mime_type": "text/plain", "text": "First note"},
                    "metadata": {},
                    "blobs": [],
                    "parents": [],
                    "ingress": {"transport": "local-file-drop", "path": "ingress/local/a.txt"},
                },
                {
                    "schema_version": 1,
                    "event_id": "evt-3",
                    "kind": "link.capture",
                    "captured_at": "2026-03-13T09:31:00+05:30",
                    "received_at": "2026-03-13T09:31:05+05:30",
                    "producer": {"type": "chrome-extension", "id": "chrome"},
                    "content": {"mime_type": "text/uri-list", "url": "https://example.com", "text": "Example"},
                    "metadata": {},
                    "blobs": [],
                    "parents": [],
                    "ingress": {"transport": "manual", "path": "ingress/manual/a.json"},
                },
            ]
            (journal_day / "13.ndjson").write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )

            self.run_cmd("bash", str(MATERIALIZE), str(data_dir))

            expected = (
                "[2026-03-13 09:30:00]\n"
                "First note\n\n"
                "[2026-03-13 09:32:00]\n"
                "Second note\n"
                "with two lines\n\n"
            )
            self.assertEqual((data_dir / "views" / "notes.txt").read_text(encoding="utf-8"), expected)
            self.assertFalse((data_dir / "notes.txt").exists())

    def test_materialize_notes_creates_empty_view_when_no_journal_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))

            self.run_cmd("bash", str(MATERIALIZE), str(data_dir))

            self.assertTrue((data_dir / "views" / "notes.txt").exists())
            self.assertFalse((data_dir / "notes.txt").exists())
            self.assertEqual((data_dir / "views" / "notes.txt").read_text(encoding="utf-8"), "")

    def test_process_inbox_does_not_use_removed_legacy_inbox_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            inbox = data_dir / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)

            txt_file = inbox / "iphone-note.txt"
            txt_file.write_text("Hello from removed legacy inbox\n", encoding="utf-8")
            self.run_cmd("touch", "-t", "202603131724.25", str(txt_file))

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(imported_entries, [])
            self.assertEqual(self.read_journal_events(data_dir), [])
            self.assertTrue(txt_file.exists())
            self.assertFalse((inbox / "archive").exists())

    def test_process_inbox_imports_dropbox_ingress_files_without_using_legacy_inbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "dropbox"

            note_file = ingress / "iphone-capture.txt"
            note_file.write_text("Hello from ingress\n", encoding="utf-8")
            self.run_cmd("touch", "-t", "202603131726.45", str(note_file))

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(imported_entries, [])

            self.assertTrue((ingress / "archive" / "iphone-capture.txt.imported").exists())

            journal_events = self.read_journal_events(data_dir)
            self.assertEqual(len(journal_events), 1)
            self.assertEqual(journal_events[0]["kind"], "note.capture")
            self.assertEqual(journal_events[0]["producer"]["type"], "mobile-file-drop")
            self.assertEqual(journal_events[0]["producer"]["id"], "dropbox-ingress")
            self.assertEqual(journal_events[0]["content"]["mime_type"], "text/plain")
            self.assertEqual(journal_events[0]["content"]["text"], "Hello from ingress")
            self.assertTrue(journal_events[0]["captured_at"].startswith("2026-03-13T17:26:45"))
            self.assertEqual(journal_events[0]["ingress"]["path"], "ingress/dropbox/iphone-capture.txt")
            self.assertIn("event_id", journal_events[0])
            self.assertIn("received_at", journal_events[0])
            self.assertTrue((data_dir / "journal" / "2026" / "03" / "13.ndjson").exists())

            expected = "[2026-03-13 17:26:45]\nHello from ingress\n\n"
            self.assertEqual((data_dir / "views" / "notes.txt").read_text(encoding="utf-8"), expected)
            self.assertFalse((data_dir / "notes.txt").exists())

    def test_process_inbox_imports_local_ingress_files_for_mac_capture_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "local"

            note_file = ingress / "mac-capture.txt"
            note_file.write_text("Hello from Mac ingress\n", encoding="utf-8")
            self.run_cmd("touch", "-t", "202603131730.10", str(note_file))

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(imported_entries, [])
            self.assertTrue((ingress / "archive" / "mac-capture.txt.imported").exists())

            journal_events = self.read_journal_events(data_dir)
            self.assertEqual(len(journal_events), 1)
            self.assertEqual(journal_events[0]["kind"], "note.capture")
            self.assertEqual(journal_events[0]["producer"]["type"], "mac-hotkey")
            self.assertEqual(journal_events[0]["producer"]["id"], "local-ingress")
            self.assertEqual(journal_events[0]["content"]["text"], "Hello from Mac ingress")
            self.assertTrue(journal_events[0]["captured_at"].startswith("2026-03-13T17:30:10"))
            self.assertEqual(journal_events[0]["ingress"]["path"], "ingress/local/mac-capture.txt")

            expected = "[2026-03-13 17:30:10]\nHello from Mac ingress\n\n"
            self.assertEqual((data_dir / "views" / "notes.txt").read_text(encoding="utf-8"), expected)
            self.assertFalse((data_dir / "notes.txt").exists())

    def test_process_inbox_moves_empty_dropbox_ingress_files_to_archive_without_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "dropbox"
            empty_file = ingress / "blank.txt"
            empty_file.write_text("  \n\n\t", encoding="utf-8")

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = list((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(imported_entries, [])
            self.assertEqual(self.read_journal_events(data_dir), [])
            self.assertFalse(empty_file.exists())
            self.assertTrue((ingress / "archive" / "blank.txt.empty").exists())

    def test_commit_ingress_commits_valid_capture_event_v1_json_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "dropbox"

            payload = {
                "schema_version": 1,
                "kind": "note.capture",
                "captured_at": "2026-03-13T17:24:25+05:30",
                "producer": {
                    "type": "ios-shortcut",
                    "id": "anuj-iphone",
                    "version": "1.0",
                },
                "client_event_id": "2026-03-13_17-24-25-iphone",
                "content": {
                    "mime_type": "text/plain",
                    "text": "Quick note from iPhone",
                },
                "metadata": {
                    "tags": ["inbox"],
                },
            }
            (ingress / "capture.json").write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_cmd("python3", str(COMMIT_INGRESS), str(data_dir))
            self.assertIn("COMMITTED_COUNT=1", result.stdout)
            self.assertIn("DUPLICATE_COUNT=0", result.stdout)
            self.assertIn("REJECTED_COUNT=0", result.stdout)

            journal_events = self.read_journal_events(data_dir)
            self.assertEqual(len(journal_events), 1)
            self.assertEqual(journal_events[0]["kind"], "note.capture")
            self.assertEqual(journal_events[0]["producer"]["type"], "ios-shortcut")
            self.assertEqual(journal_events[0]["producer"]["id"], "anuj-iphone")
            self.assertEqual(journal_events[0]["client_event_id"], "2026-03-13_17-24-25-iphone")
            self.assertEqual(journal_events[0]["content"]["text"], "Quick note from iPhone")
            self.assertEqual(journal_events[0]["metadata"], {"tags": ["inbox"]})
            self.assertEqual(journal_events[0]["ingress"]["path"], "ingress/dropbox/capture.json")
            self.assertIn("received_at", journal_events[0])
            self.assertIn("event_id", journal_events[0])

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(imported_entries, [])
            self.assertTrue((ingress / "archive" / "capture.json.imported").exists())

            dedupe_markers = sorted((data_dir / "state" / "dedupe").glob("*.json"))
            self.assertEqual(len(dedupe_markers), 1)

    def test_commit_ingress_rejects_invalid_json_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "dropbox"

            payload = {
                "schema_version": 1,
                "captured_at": "2026-03-13T17:24:25+05:30",
                "producer": {
                    "type": "ios-shortcut",
                    "id": "anuj-iphone",
                },
                "content": {
                    "mime_type": "text/plain",
                    "text": "Missing kind",
                },
            }
            (ingress / "invalid.json").write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_cmd("python3", str(COMMIT_INGRESS), str(data_dir))
            self.assertIn("COMMITTED_COUNT=0", result.stdout)
            self.assertIn("REJECTED_COUNT=1", result.stdout)

            self.assertEqual(self.read_journal_events(data_dir), [])
            self.assertEqual(list((data_dir / "entries").rglob("*.txt")), [])

            rejected_files = sorted((data_dir / "rejects").rglob("invalid.json"))
            self.assertEqual(len(rejected_files), 1)
            reason_files = sorted((data_dir / "rejects").rglob("invalid.json.reason.txt"))
            self.assertEqual(len(reason_files), 1)
            self.assertIn("kind must be a non-empty string", reason_files[0].read_text(encoding="utf-8"))
            self.assertFalse((ingress / "invalid.json").exists())

    def test_commit_ingress_dedupes_json_payloads_by_producer_and_client_event_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "dropbox"

            payload_a = {
                "schema_version": 1,
                "kind": "note.capture",
                "captured_at": "2026-03-13T17:24:25+05:30",
                "producer": {
                    "type": "ios-shortcut",
                    "id": "anuj-iphone",
                },
                "client_event_id": "dedupe-key-1",
                "content": {
                    "mime_type": "text/plain",
                    "text": "First copy",
                },
            }
            payload_b = {
                "schema_version": 1,
                "kind": "note.capture",
                "captured_at": "2026-03-13T17:24:26+05:30",
                "producer": {
                    "type": "ios-shortcut",
                    "id": "anuj-iphone",
                },
                "client_event_id": "dedupe-key-1",
                "content": {
                    "mime_type": "text/plain",
                    "text": "Duplicate copy",
                },
            }

            (ingress / "a.json").write_text(json.dumps(payload_a), encoding="utf-8")
            (ingress / "b.json").write_text(json.dumps(payload_b), encoding="utf-8")

            result = self.run_cmd("python3", str(COMMIT_INGRESS), str(data_dir))
            self.assertIn("COMMITTED_COUNT=1", result.stdout)
            self.assertIn("DUPLICATE_COUNT=1", result.stdout)

            journal_events = self.read_journal_events(data_dir)
            self.assertEqual(len(journal_events), 1)
            self.assertEqual(journal_events[0]["client_event_id"], "dedupe-key-1")
            self.assertEqual(journal_events[0]["content"]["text"], "First copy")

            self.assertTrue((ingress / "archive" / "a.json.imported").exists())
            self.assertTrue((ingress / "archive" / "b.json.duplicate").exists())
            self.assertEqual(sorted((data_dir / "entries").rglob("*.txt")), [])

    def test_repartition_journal_rewrites_files_by_captured_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            wrong_day = data_dir / "journal" / "2026" / "03"
            wrong_day.mkdir(parents=True, exist_ok=True)
            events = [
                {
                    "schema_version": 1,
                    "event_id": "evt-1",
                    "kind": "note.capture",
                    "captured_at": "2026-03-13T09:30:00+05:30",
                    "received_at": "2026-03-30T12:00:00+05:30",
                    "producer": {"type": "mac-hotkey", "id": "mba"},
                    "content": {"mime_type": "text/plain", "text": "March 13 note"},
                    "metadata": {},
                    "blobs": [],
                    "parents": [],
                    "ingress": {"transport": "local-file-drop", "path": "ingress/local/a.txt"},
                },
                {
                    "schema_version": 1,
                    "event_id": "evt-2",
                    "kind": "note.capture",
                    "captured_at": "2026-03-30T09:30:00+05:30",
                    "received_at": "2026-03-30T12:00:01+05:30",
                    "producer": {"type": "mobile-file-drop", "id": "iphone"},
                    "content": {"mime_type": "text/plain", "text": "March 30 note"},
                    "metadata": {},
                    "blobs": [],
                    "parents": [],
                    "ingress": {"transport": "dropbox-file-drop", "path": "ingress/dropbox/a.txt"},
                },
            ]
            (wrong_day / "30.ndjson").write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            result = self.run_cmd("python3", str(REPARTITION_JOURNAL), str(data_dir))
            self.assertIn("EVENT_COUNT=2", result.stdout)
            self.assertTrue((data_dir / "journal" / "2026" / "03" / "13.ndjson").exists())
            self.assertTrue((data_dir / "journal" / "2026" / "03" / "30.ndjson").exists())

            day_13 = (data_dir / "journal" / "2026" / "03" / "13.ndjson").read_text(encoding="utf-8")
            day_30 = (data_dir / "journal" / "2026" / "03" / "30.ndjson").read_text(encoding="utf-8")
            self.assertIn("March 13 note", day_13)
            self.assertNotIn("March 30 note", day_13)
            self.assertIn("March 30 note", day_30)
            self.assertNotIn("March 13 note", day_30)

        
    def test_backfill_entries_to_journal_imports_old_entries_and_skips_existing_journal_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            day_dir = data_dir / "entries" / "2026" / "03" / "13"
            day_dir.mkdir(parents=True, exist_ok=True)

            existing_entry = day_dir / "2026-03-13_09-30-00--mac-hotkey--mba--aaaa1111.txt"
            existing_entry.write_text("Already in journal\n", encoding="utf-8")
            backfill_entry = day_dir / "2026-03-13_09-32-00--legacy-import--migrated-0001--bbbb2222.txt"
            backfill_entry.write_text("Backfill me\n", encoding="utf-8")

            journal_day = data_dir / "journal" / "2026" / "03"
            journal_day.mkdir(parents=True, exist_ok=True)
            existing_event = {
                "schema_version": 1,
                "event_id": "evt-existing",
                "kind": "note.capture",
                "captured_at": "2026-03-13T09:30:00+05:30",
                "received_at": "2026-03-13T09:30:01+05:30",
                "producer": {"type": "mac-hotkey", "id": "mba"},
                "content": {"mime_type": "text/plain", "text": "Already in journal"},
                "metadata": {},
                "blobs": [],
                "parents": [],
                "ingress": {"transport": "local-file-drop", "path": "ingress/local/a.txt"},
            }
            (journal_day / "13.ndjson").write_text(json.dumps(existing_event) + "\n", encoding="utf-8")

            result = self.run_cmd("python3", str(BACKFILL_ENTRIES), str(data_dir))
            self.assertIn("BACKFILLED_COUNT=1", result.stdout)
            self.assertIn("SKIPPED_COUNT=1", result.stdout)

            journal_events = self.read_journal_events(data_dir)
            self.assertEqual(len(journal_events), 2)
            backfilled_events = [
                event
                for event in journal_events
                if event.get("metadata", {}).get("backfilled_from_entry")
                == "entries/2026/03/13/2026-03-13_09-32-00--legacy-import--migrated-0001--bbbb2222.txt"
            ]
            self.assertEqual(len(backfilled_events), 1)
            self.assertEqual(backfilled_events[0]["producer"]["type"], "legacy-import")
            self.assertEqual(backfilled_events[0]["producer"]["id"], "migrated-0001")
            self.assertEqual(backfilled_events[0]["content"]["text"], "Backfill me")
            self.assertEqual(backfilled_events[0]["ingress"]["transport"], "entries-backfill")

    def test_repo_removes_legacy_migration_script_and_storage_dir(self):
        setup_source = SETUP.read_text(encoding="utf-8")
        contributing = CONTRIBUTING.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")

        self.assertFalse(IMPORT_LEGACY.exists())
        self.assertNotIn('"$DATA_DIR/legacy"', setup_source)
        self.assertNotIn('archive_legacy_notes_if_needed', setup_source)
        self.assertNotIn('import_legacy_notes.py', contributing)
        self.assertNotIn('legacy/', readme)

    def test_quicknote_source_targets_local_ingress_not_entries(self):
        source = QUICKNOTE.read_text(encoding="utf-8")
        self.assertIn('appendingPathComponent("ingress", isDirectory: true)', source)
        self.assertIn('appendingPathComponent("local", isDirectory: true)', source)
        self.assertNotIn('try materializeNotes()', source)
        self.assertNotIn('appendingPathComponent("entries", isDirectory: true)', source)

    def test_setup_and_docs_reflect_ingress_only_current_state(self):
        setup_source = SETUP.read_text(encoding="utf-8")
        ios_readme = IOS_README.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        architecture = ARCHITECTURE_V2.read_text(encoding="utf-8")

        self.assertIn('/${dropbox_relative}/ingress/dropbox', setup_source)
        self.assertNotIn('/${dropbox_relative}/inbox', setup_source)
        self.assertNotIn('phone writes plain text files into inbox/', setup_source)
        self.assertNotIn('Mobile inbox:', setup_source)
        self.assertNotIn('inbox/', setup_source)

        self.assertIn('ingress/dropbox/', ios_readme)
        self.assertNotIn('inbox/', ios_readme)

        self.assertIn('ingress/dropbox/', readme)
        self.assertIn('ingress/local/', readme)
        self.assertIn('journal/', readme)
        self.assertIn('views/', readme)
        self.assertNotIn('legacy/', readme)
        self.assertNotIn('Desktop direct-write contract', readme)
        self.assertNotIn('write one plain text file per note into:\n\n```txt\nentries/YYYY/MM/DD/', readme)
        self.assertNotIn('The Mac helper writes a canonical entry file and regenerates `notes.txt`.', readme)

        self.assertIn('all producers write raw capture requests into `ingress/`', architecture)
        self.assertIn('have the Mac helper append a raw capture request into `ingress/local/`', architecture)
        self.assertNotIn('phone writes plain text files into `inbox/`', architecture)
        self.assertNotIn('Mac helper writes canonical text files into `entries/`', architecture)

    @unittest.skipUnless(shutil.which("swiftc"), "swiftc not available")
    def test_quicknote_swift_typechecks(self):
        self.run_cmd("swiftc", "-typecheck", str(QUICKNOTE))


if __name__ == "__main__":
    unittest.main()
