#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Update byte-for-byte contract/fixture copies from an immutable Zairenkai-Sdk dev head.

This helper only copies paths declared by contracts/sources.json. It rejects path traversal,
requires full git SHAs, records each copied file's SHA-256, and does not change tool semantics.
The generated grammar and complete CI must pass in the PR before the new pin is merged.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, urllib.error, urllib.request
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
SDK_REPO='ZairenkaiPrjctX/Zairenkai-Sdk'
SHA1=re.compile(r'^[0-9a-f]{40}$')

def latest_dev_commit() -> str:
    url=f'https://api.github.com/repos/{SDK_REPO}/commits/dev'
    headers={'Accept':'application/vnd.github+json','User-Agent':'Zairenkai-Engine-SDK-Sync/1.0','X-GitHub-Api-Version':'2022-11-28'}
    token=os.environ.get('GITHUB_TOKEN')
    if token: headers['Authorization']='Bearer '+token
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as r: data=json.loads(r.read())
    except (urllib.error.URLError,TimeoutError,ValueError) as e: raise SystemExit(f'cannot resolve {SDK_REPO}/dev: {e}') from e
    commit=data.get('sha','')
    if not SHA1.fullmatch(commit): raise SystemExit('SDK API returned a malformed commit SHA')
    return commit

def git_show(repo_dir: Path, commit: str, path: str) -> bytes:
    p=PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or '\\' in path or not path or not path.startswith(('contracts/','fixtures/')):
        raise SystemExit(f'refusing unsafe SDK path: {path!r}')
    try: return subprocess.run(['git','-C',str(repo_dir),'show',f'{commit}:{path}'],check=True,capture_output=True,timeout=60).stdout
    except subprocess.CalledProcessError as e: raise SystemExit(f'SDK commit {commit} lacks declared file {path}: {e.stderr.decode(errors="replace")}') from e

def sync(commit: str|None=None) -> bool:
    commit=commit or latest_dev_commit()
    if not SHA1.fullmatch(commit): raise SystemExit('SDK commit must be a full lowercase SHA-1')
    lock_path=ROOT/'contracts/sources.json'; doc=json.loads(lock_path.read_text(encoding='utf-8'))
    sdk_dir=ROOT/'build/sdk-contract-source'
    if not (sdk_dir/'.git').is_dir():
        sdk_dir.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','init','-q',str(sdk_dir)],check=True)
        subprocess.run(['git','-C',str(sdk_dir),'remote','add','origin',f'https://github.com/{SDK_REPO}.git'],check=True)
    subprocess.run(['git','-C',str(sdk_dir),'fetch','-q','--depth','1','origin',commit],check=True,timeout=180)
    resolved=subprocess.run(['git','-C',str(sdk_dir),'rev-parse','FETCH_HEAD'],check=True,capture_output=True,text=True).stdout.strip()
    if resolved!=commit: raise SystemExit(f'SDK checkout resolved {resolved}, expected {commit}')
    changed=False
    for entry in doc.get('files',[]):
        if not isinstance(entry,dict) or not isinstance(entry.get('sdk_path'),str) or not isinstance(entry.get('copy'),str):
            raise SystemExit('sources.json has a malformed file entry')
        data=git_show(sdk_dir,commit,entry['sdk_path'])
        digest=hashlib.sha256(data).hexdigest()
        target=(ROOT/entry['copy']).resolve()
        if ROOT not in target.parents: raise SystemExit(f'refusing SDK destination outside repo: {entry["copy"]}')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.is_file() or target.read_bytes()!=data:
            target.write_bytes(data); changed=True
        if entry.get('sha256')!=digest: entry['sha256']=digest; changed=True
    if doc.get('sdk',{}).get('repository')!=SDK_REPO: raise SystemExit('sources.json names an unexpected SDK repository')
    if doc['sdk'].get('commit')!=commit: doc['sdk']['commit']=commit; changed=True
    if changed: lock_path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'SDK source pinned at {commit}; {len(doc.get("files",[]))} byte-exact contract/fixture copies verified.')
    return changed

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--commit',help='test-only/maintainer override: exact full SDK commit'); ns=p.parse_args()
    sync(ns.commit)
