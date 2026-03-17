import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MATERIALIZE = REPO_ROOT / "scripts" / "materialize_notes.sh"
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

    def test_materialize_notes_creates_timeline_from_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            day_dir = data_dir / "entries" / "2026" / "03" / "13"
            day_dir.mkdir(parents=True, exist_ok=True)

            (day_dir / "2026-03-13_09-30-00--mac-hotkey--mba--aaaa1111.txt").write_text(
                "First note\n", encoding="utf-8"
            )
            (day_dir / "2026-03-13_09-31-00--mac-hotkey--mba--bbbb2222.txt").write_text(
                "\n\n", encoding="utf-8"
            )
            (day_dir / "2026-03-13_09-32-00--mobile-capture--iphone--cccc3333.txt").write_text(
                "Second note\nwith two lines\n", encoding="utf-8"
            )

            self.run_cmd("bash", str(MATERIALIZE), str(data_dir))

            notes = (data_dir / "notes.txt").read_text(encoding="utf-8")
            self.assertEqual(
                notes,
                "[2026-03-13 09:30:00]\n"
                "First note\n\n"
                "[2026-03-13 09:32:00]\n"
                "Second note\n"
                "with two lines\n\n",
            )

    def test_materialize_notes_creates_empty_notes_file_when_no_entries_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))

            self.run_cmd("bash", str(MATERIALIZE), str(data_dir))

            notes_file = data_dir / "notes.txt"
            self.assertTrue(notes_file.exists())
            self.assertEqual(notes_file.read_text(encoding="utf-8"), "")

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
            self.assertEqual(len(imported_entries), 1)
            self.assertTrue(
                imported_entries[0].name.startswith("2026-03-13_17-26-45--mobile-capture--dropbox-ingress--")
            )
            self.assertEqual(imported_entries[0].read_text(encoding="utf-8"), "Hello from ingress\n")

            self.assertTrue((ingress / "archive" / "iphone-capture.txt.imported").exists())
            notes = (data_dir / "notes.txt").read_text(encoding="utf-8")
            self.assertEqual(notes, "[2026-03-13 17:26:45]\nHello from ingress\n\n")

    def test_process_inbox_imports_local_ingress_files_for_mac_capture_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "local"

            note_file = ingress / "mac-capture.txt"
            note_file.write_text("Hello from Mac ingress\n", encoding="utf-8")
            self.run_cmd("touch", "-t", "202603131730.10", str(note_file))

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(len(imported_entries), 1)
            self.assertTrue(
                imported_entries[0].name.startswith("2026-03-13_17-30-10--mac-hotkey--local-ingress--")
            )
            self.assertEqual(imported_entries[0].read_text(encoding="utf-8"), "Hello from Mac ingress\n")
            self.assertTrue((ingress / "archive" / "mac-capture.txt.imported").exists())

            notes = (data_dir / "notes.txt").read_text(encoding="utf-8")
            self.assertEqual(notes, "[2026-03-13 17:30:10]\nHello from Mac ingress\n\n")

    def test_process_inbox_moves_empty_dropbox_ingress_files_to_archive_without_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            ingress = data_dir / "ingress" / "dropbox"
            empty_file = ingress / "blank.txt"
            empty_file.write_text("  \n\n\t", encoding="utf-8")

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = list((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(imported_entries, [])
            self.assertFalse(empty_file.exists())
            self.assertTrue((ingress / "archive" / "blank.txt.empty").exists())

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
