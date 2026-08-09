from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any
import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile

from .config import Settings
from .database import Database
from .util import now_iso


class BackupService:
    def __init__(self,settings: Settings,db: Database): self.settings=settings; self.db=db

    def create(self,name: str | None=None) -> Path:
        stamp=now_iso().replace(":","").replace("+00:00","Z")
        target=self.settings.backups_dir/(name or f"cinenode-{stamp}.zip")
        if target.suffix.lower() != ".zip": target=target.with_suffix(".zip")
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cinenode-backup-") as tmp:
            db_copy=Path(tmp)/"cinenode.sqlite3"
            with self.db.connect() as source, sqlite3.connect(db_copy) as destination: source.backup(destination)
            files=[("database/cinenode.sqlite3",db_copy)]
            with self.db.connect() as con:
                rows=con.execute("SELECT relative_path FROM assets").fetchall()
            for row in rows:
                path=(self.settings.home/row[0]).resolve()
                if self.settings.home not in path.parents or not path.is_file(): continue
                files.append((f"files/{row[0]}",path))
            manifest={"schema_version":1,"created_at":now_iso(),"files":[]}
            with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
                for arc,path in files:
                    data=path.read_bytes(); archive.writestr(arc,data)
                    manifest["files"].append({"path":arc,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
                archive.writestr("manifest.json",json.dumps(manifest,indent=2))
        return target

    @staticmethod
    def restore(archive_path: Path,target_home: Path) -> dict[str,Any]:
        target_home=target_home.resolve(); target_home.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            manifest=json.loads(archive.read("manifest.json"))
            members={item.filename:item for item in archive.infolist()}
            for item in manifest["files"]:
                name=item["path"]; pure=PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts or name not in members: raise ValueError("unsafe backup member")
                data=archive.read(name)
                if len(data)!=item["bytes"] or hashlib.sha256(data).hexdigest()!=item["sha256"]: raise ValueError("backup checksum mismatch")
                if name=="database/cinenode.sqlite3": destination=target_home/"data"/"cinenode.sqlite3"
                elif name.startswith("files/"): destination=target_home/name.removeprefix("files/")
                else: continue
                destination.resolve().relative_to(target_home); destination.parent.mkdir(parents=True,exist_ok=True); destination.write_bytes(data)
        db=Database(target_home/"data"/"cinenode.sqlite3"); db.initialize()
        return db.integrity_report()
