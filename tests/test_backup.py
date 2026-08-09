from pathlib import Path
import shutil

from cinenode.backup import BackupService
from cinenode.database import Database
from cinenode.store import Store


def test_backup_restores_after_source_is_deleted(tmp_path: Path):
    source=tmp_path/"source"; source.mkdir(); db=Database(source/"data/cinenode.sqlite3"); db.initialize(); store=Store(db,source)
    project=store.create_project("P"); path=source/"assets/proof.txt"; path.parent.mkdir(); path.write_text("portable")
    store.register_asset(path,project_id=project["id"],job_id=None,kind="text",original_name="proof.txt")
    class S: home=source; backups_dir=source/"backups"
    archive=BackupService(S,db).create(); copy=tmp_path/"backup.zip"; shutil.copy2(archive,copy); shutil.rmtree(source)
    target=tmp_path/"target"; report=BackupService.restore(copy,target); assert report["ok"] is True; assert (target/"assets/proof.txt").read_text()=="portable"
