from pathlib import Path
import sqlite3

from cinenode.database import Database, SCHEMA_VERSION
from cinenode.store import Store


def test_database_initialization_is_idempotent(settings):
    settings.prepare(); db=Database(settings.database_path); db.initialize(); db.initialize()
    report=db.integrity_report(); assert report["ok"] is True; assert report["schema_version"]==SCHEMA_VERSION


def test_project_workflow_and_secret_redaction(settings):
    settings.prepare(); db=Database(settings.database_path); db.initialize(); store=Store(db,settings.home)
    project=store.create_project("Film"); workflow=store.create_workflow(project["id"],"Scene",{"nodes":[{"id":"a","type":"input.text","params":{"text":"hi"}}]})
    assert store.get_workflow(workflow["id"])["definition"]["nodes"][0]["id"]=="a"
    with db.transaction() as con:
        con.execute("INSERT INTO settings(key,value_json,secret,updated_at) VALUES('visible','1',0,'now')")
        con.execute("INSERT INTO settings(key,value_json,secret,updated_at) VALUES('token','\"secret\"',1,'now')")
    assert store.public_settings()=={"visible":1}


def test_asset_job_link_survives_initialize(settings):
    settings.prepare(); db=Database(settings.database_path); db.initialize(); store=Store(db,settings.home)
    project=store.create_project("P"); workflow=store.create_workflow(project["id"],"W",{"nodes":[{"id":"a","type":"input.text"}]}); job=store.create_job(workflow["id"],{})
    path=settings.assets_dir/"proof.txt"; path.write_text("proof",encoding="utf-8")
    asset=store.register_asset(path,project_id=project["id"],job_id=job["id"],kind="text",original_name="proof.txt")
    db.initialize()
    with db.connect() as con:
        row=con.execute("SELECT job_id FROM assets WHERE id=?",(asset["id"],)).fetchone()
    assert row[0]==job["id"]
