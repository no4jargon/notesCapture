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
        (data_dir / "inbox").mkdir(parents=True, exist_ok=True)
        (data_dir / "ingress" / "dropbox").mkdir(parents=True, exist_ok=True)
        (data_dir / "ingress" / "local").mkdir(parents=True, exist_ok=True)
        (data_dir / "legacy").mkdir(parents=True, exist_ok=True)
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

    def test_process_inbox_imports_legacy_inbox_files_archives_originals_and_updates_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            inbox = data_dir / "inbox"

            txt_file = inbox / "iphone-note.txt"
            md_file = inbox / "android-note.md"
            txt_file.write_text("Hello from iPhone\nsecond line\n", encoding="utf-8")
            md_file.write_text("Hello from Android\n", encoding="utf-8")

            self.run_cmd("touch", "-t", "202603131724.25", str(txt_file))
            self.run_cmd("touch", "-t", "202603131725.30", str(md_file))

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(len(imported_entries), 2)
            self.assertTrue(
                any(path.name.startswith("2026-03-13_17-24-25--mobile-capture--dropbox-inbox--") for path in imported_entries)
            )
            self.assertTrue(
                any(path.name.startswith("2026-03-13_17-25-30--mobile-capture--dropbox-inbox--") for path in imported_entries)
            )

            archived = sorted((inbox / "archive").iterdir())
            archived_names = [path.name for path in archived]
            self.assertEqual(
                archived_names,
                ["android-note.md.imported", "iphone-note.txt.imported"],
            )

            notes = (data_dir / "notes.txt").read_text(encoding="utf-8")
            self.assertIn("[2026-03-13 17:24:25]\nHello from iPhone\nsecond line\n", notes)
            self.assertIn("[2026-03-13 17:25:30]\nHello from Android\n", notes)

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

    def test_process_inbox_moves_empty_files_to_archive_without_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = self.make_data_dir(Path(tmp))
            inbox = data_dir / "inbox"
            empty_file = inbox / "blank.txt"
            empty_file.write_text("  \n\n\t", encoding="utf-8")

            self.run_cmd("bash", str(PROCESS_INBOX), str(data_dir))

            imported_entries = list((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(imported_entries, [])
            self.assertFalse(empty_file.exists())
            self.assertTrue((inbox / "archive" / "blank.txt.empty").exists())

    def test_import_legacy_notes_creates_entries_archive_and_materialized_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data_dir = self.make_data_dir(tmp_path)
            legacy_file = tmp_path / "notes.txt"
            legacy_file.write_text(
                "[2026-03-12 03:51:59]\n"
                "hello world 3\n\n\n"
                "[2026-03-12 03:54:51]\n"
                "hello world 4\n",
                encoding="utf-8",
            )

            result = self.run_cmd("python3", str(IMPORT_LEGACY), str(legacy_file), str(data_dir))
            self.assertIn("Imported 2 entries", result.stdout)

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(len(imported_entries), 2)
            self.assertEqual(
                [path.name for path in imported_entries],
                [
                    "2026-03-12_03-51-59--legacy-import--migrated-0001.txt",
                    "2026-03-12_03-54-51--legacy-import--migrated-0002.txt",
                ],
            )
            self.assertTrue((data_dir / "legacy" / "notes-imported-source.txt").exists())

            notes = (data_dir / "notes.txt").read_text(encoding="utf-8")
            self.assertEqual(
                notes,
                "[2026-03-12 03:51:59]\n"
                "hello world 3\n\n"
                "[2026-03-12 03:54:51]\n"
                "hello world 4\n\n",
            )

    def test_import_legacy_notes_is_idempotent_for_existing_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data_dir = self.make_data_dir(tmp_path)
            legacy_file = tmp_path / "notes.txt"
            legacy_file.write_text(
                "[2026-03-12 03:51:59]\n"
                "hello world 3\n",
                encoding="utf-8",
            )

            self.run_cmd("python3", str(IMPORT_LEGACY), str(legacy_file), str(data_dir))
            second = self.run_cmd("python3", str(IMPORT_LEGACY), str(legacy_file), str(data_dir))

            imported_entries = sorted((data_dir / "entries").rglob("*.txt"))
            self.assertEqual(len(imported_entries), 1)
            self.assertIn("Imported 0 entries", second.stdout)

    @unittest.skipUnless(shutil.which("swiftc"), "swiftc not available")
    def test_quicknote_swift_typechecks(self):
        self.run_cmd("swiftc", "-typecheck", str(QUICKNOTE))


if __name__ == "__main__":
    unittest.main()
