"""Rerun the locked 500-PDF VPUB set with current extraction and resolution.

Checkpoints are pinned to input bytes and backend/directory/policy versions.
No Google credentials are used; connector upload is a separate reviewed step.
"""
import argparse
import asyncio
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys
from time import perf_counter

import httpx

from ai_document_sender.config import Settings
from ai_document_sender.contracts import DocumentMetadata
from ai_document_sender.extraction import extract_document
from ai_document_sender.jobs import processing_version
from ai_document_sender.learning import bind_targets
from ai_document_sender.provider import OpenRouterProvider, ProviderError
from ai_document_sender.registry import Registry, normalize, digest
from ai_document_sender.resolver import resolve_mentions
from ai_document_sender.tenants import TenantManager
from tools.learn_recipient_sheet import sheet_rows, target_spec


class AuditedProvider(OpenRouterProvider):
    def __init__(self, settings, client):
        super().__init__(settings, client=client)
        self.failures = []
        self.calls = 0

    async def _request(self, body, deadline):
        self.calls += 1
        try:
            return await super()._request(body, deadline)
        except ProviderError as error:
            self.failures.append({'code': error.code, 'message': str(error),
                                  'schema': body['response_format']['json_schema']['name']})
            raise


def read_source(parts):
    source = json.loads(parts[0].read_text(encoding='utf-8'))
    blocks = source['sheets'][0]['data']
    for part in parts[1:]:
        other = json.loads(part.read_text(encoding='utf-8'))
        assert other['spreadsheetId'] == source['spreadsheetId']
        blocks.extend(other['sheets'][0]['data'])
    return source


def metadata_for(doc):
    path = Path(doc['pdf_path']).parent / 'view.cpx'
    ed = json.loads(path.read_text(encoding='utf-8')).get('ed', {}) if path.exists() else {}
    return DocumentMetadata(document_id=str(ed.get('id') or doc['folder_name']),
                            sign_number=ed.get('signNumber') or doc['so_hieu'],
                            subject=ed.get('subject') or doc['trich_yeu'], issuer='UBND tỉnh Gia Lai')


async def rerun(args):
    settings = Settings.from_env()
    settings = replace(settings, lookup_db=TenantManager(settings).get_db_path('vpub'))
    registry = Registry(settings)
    # Per-run files are isolated; directory/policy and provider settings stay current.
    settings = replace(settings, runtime_dir=args.output / 'runtime')
    version = processing_version(settings)
    docs = json.loads(args.dataset.read_text(encoding='utf-8'))
    assert len(docs) == 500 and len({d['folder_name'] for d in docs}) == 500
    source = read_source(args.source_parts)
    old_rows = list(sheet_rows(source))
    signs = {r['document'] for r in old_rows}
    assert {d['so_hieu'] for d in docs} == signs, 'PDF set differs from the reviewed source sheet'
    old_hashes = {}
    for block in source['sheets'][0]['data']:
        for row in block.get('rowData', []):
            cells = row.get('values', []) + [{}] * 6
            sign = cells[1].get('formattedValue')
            sha = re.search(r'SHA256: ([a-f0-9]{64})', cells[0].get('note', ''))
            if sign and sha:
                old_hashes[sign] = sha[1]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'documents').mkdir(exist_ok=True)
    run_info = {'started_at': datetime.now(timezone(timedelta(hours=7))).isoformat(),
                'dataset_count': len(docs), 'provider_mode': settings.provider_mode,
                'text_model': settings.openrouter_text_model, 'vision_model': settings.openrouter_vision_model,
                'ocr_backend': settings.ocr_backend, 'processing_version': version,
                'registry_version': registry.registry_version, 'alias_policy_version': registry.alias_policy_version,
                'concurrency': args.concurrency}
    run_file = args.output / 'run.json'
    source_file = args.output / 'source.json'
    snapshot_file = args.output / 'registry-snapshot.json'
    if run_file.exists():
        previous = json.loads(run_file.read_text(encoding='utf-8'))
        assert all(previous[k] == run_info[k] for k in ('processing_version', 'registry_version', 'alias_policy_version')), 'Run versions changed; use a fresh output directory'
        assert digest(json.loads(source_file.read_text(encoding='utf-8'))) == digest(source), 'Reviewed source changed; use a fresh output directory'
        run_info['started_at'] = previous['started_at']
    else:
        source_file.write_text(json.dumps(source, ensure_ascii=False), encoding='utf-8')
        snapshot_file.write_text(json.dumps(registry.snapshot(), ensure_ascii=False), encoding='utf-8')
        run_file.write_text(json.dumps(run_info, ensure_ascii=False, indent=2), encoding='utf-8')
    semaphore = asyncio.Semaphore(args.concurrency)
    completed = 0
    started = perf_counter()
    statuses = Counter()

    async def one(doc, client):
        nonlocal completed
        async with semaphore:
            path = Path(doc['pdf_path'])
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if doc['so_hieu'] in old_hashes:
                assert sha == old_hashes[doc['so_hieu']], f'Input bytes changed: {doc["folder_name"]}'
            pinned = {'input_sha256': sha, 'processing_version': version,
                      'registry_version': registry.registry_version, 'alias_policy_version': registry.alias_policy_version}
            target = args.output / 'documents' / f'{doc["stt"]:04}.json'
            if target.exists():
                saved = json.loads(target.read_text(encoding='utf-8'))
                assert all(saved[k] == v for k, v in pinned.items()), 'Checkpoint versions changed; use a fresh output directory'
                completed += 1
                return saved
            provider = AuditedProvider(settings, client)
            record = {'stt': doc['stt'], 'folder_name': doc['folder_name'], 'pdf_path': str(path),
                      'sign_number': doc['so_hieu'], **pinned}
            begin = perf_counter()
            try:
                metadata = metadata_for(doc)
                extraction = await extract_document(path, provider, metadata, settings)
                result = await resolve_mentions(extraction, registry, metadata, f'regression-{doc["stt"]:04}', sha,
                                                provider=provider if provider.available else None)
                record.update(status='completed', metadata=metadata.model_dump(mode='json'),
                              extraction=extraction.model_dump(mode='json'), result=result.model_dump(mode='json'))
                statuses.update(extraction.review_reasons)
            except Exception as error:
                record.update(status='failed', error={'type': type(error).__name__, 'code': getattr(error, 'code', 'unexpected_error')})
                statuses['failed'] += 1
            record.update(duration_seconds=round(perf_counter()-begin, 3), provider_calls=provider.calls,
                          provider_failures=provider.failures)
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
            temporary.replace(target)
            completed += 1
            print(json.dumps({'completed': completed, 'total': min(args.limit, len(docs)), 'stt': doc['stt'],
                              'status': record['status'], 'seconds': record['duration_seconds'],
                              'cloud_used': record.get('extraction', {}).get('audit', {}).get('provider_used'),
                              'review_reasons': record.get('result', {}).get('review_reasons', []),
                              'elapsed': round(perf_counter()-started, 1)}, ensure_ascii=False), flush=True)
            return record

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=args.concurrency * 2)) as client:
        records = await asyncio.gather(*(one(doc, client) for doc in docs[:args.limit]))
    summary = {'processed': len(records), 'completed': sum(r['status'] == 'completed' for r in records),
               'failed': sum(r['status'] != 'completed' for r in records),
               'cloud_extraction_used': sum(r.get('extraction', {}).get('audit', {}).get('provider_used', False) for r in records),
               'review_reason_documents': dict(Counter(reason for r in records for reason in set(r.get('result', {}).get('review_reasons', [])))),
               'wall_seconds': round(perf_counter()-started, 2)}
    (args.output / 'execution-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=Path('.tmp/prepared_500_documents.json'))
    parser.add_argument('--source-parts', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=500)
    parser.add_argument('--concurrency', type=int, default=4)
    args = parser.parse_args()
    assert 1 <= args.limit <= 500 and 1 <= args.concurrency <= 8
    asyncio.run(rerun(args))


if __name__ == '__main__':
    main()
