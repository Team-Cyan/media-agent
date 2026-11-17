"""CLI, Web and scheduler share one media execution boundary."""

import json
from pathlib import Path

from media_agent.config import resolve_runtime_secret_path
from media_agent.config_views import MediaConfigGuard, load_view
from media_agent.media_import.engine import Engine
from media_agent.media_import.metadata import Tmdb
from media_agent.media_import.store import MediaStore
from media_agent.media_import.subtitles.jobs import SubtitleJobs
from media_agent.media_import.subtitles.provider import OpenSubtitles


def media_state_path(view):
    root = view.workspace
    options = view.config.media_import
    path = Path(options.state_path)
    if not path.is_absolute():
        path = root / path
    if path.resolve() == (root / ".seed-agent" / "state.db").resolve():
        raise ValueError("media state must be independent from seed state")
    for profile in options.profiles:
        if path.resolve().is_relative_to(
            Path(profile.source_root).resolve()
        ) or path.resolve().is_relative_to(Path(profile.target_root).resolve()):
            raise ValueError("media state must be outside source/library roots")
    mixed_roots = [s.root for s in options.sources]
    if options.destinations:
        mixed_roots.extend(options.destinations.exclusion_roots())
    if any(path.resolve().is_relative_to(Path(value).resolve()) for value in mixed_roots):
        raise ValueError("media state must be outside source/library roots")
    return path


def build_engine(config_path: Path, *, read_only=False, initialize=False):
    view = load_view(config_path, "media")
    root = view.workspace
    options = view.config.media_import
    metadata = None
    if options.tmdb_secret_ref and not read_only:
        secret_path = resolve_runtime_secret_path(options.tmdb_secret_ref, root)
        if secret_path.is_file():
            secret = json.loads(secret_path.read_text())
            metadata = Tmdb(secret["token"])
    path = media_state_path(view)
    store = MediaStore(path, initialize=initialize, read_only=read_only)
    engine = Engine(store, options, metadata=metadata, config_guard=MediaConfigGuard(view))
    engine.config_view = view
    return engine, root


def run(config_path: Path, *, profile=None, force=False, subtitles=True, refresh=False):
    from media_agent.media_import.commands import submit

    return submit(config_path, "subtitles" if refresh else "scan", {"profile": profile})


def run_engine(
    engine,
    config_path,
    *,
    profile=None,
    force=False,
    subtitles=True,
    refresh=False,
    scan=True,
    drain_pending=None,
    lifecycle=None,
    enrichment=True,
    enrichment_limit=None,
    should_yield=None,
    inventory_should_yield=None,
    inventory_only=False,
    reconcile_pending=False,
    posters=True,
):
    root = engine.config_view.workspace
    if not engine.config.enabled:
        return {"status": "disabled", "scans": []}
    if profile is not None and profile not in {p.name for p in engine.profiles()}:
        raise ValueError("unknown media profile")
    scans = []
    profiles = [p for p in engine.profiles() if profile is None or p.name == profile]
    # Inventory is independent of the background window: finish its profiles
    # before allowing the window deadline to stop pending/provider work.
    if scan and inventory_only:
        for index, p in enumerate(profiles):
            if inventory_should_yield and inventory_should_yield():
                return {"status": "yielded", "scans": scans}
            if lifecycle:
                lifecycle.phase(
                    "inventory",
                    deadline_seconds=engine.config.inventory_timeout_seconds + 120,
                    completed=index,
                    total=len(profiles),
                )
            result = engine.scan(p.name, force=force, inventory_only=True)
            scans.append(result)
            if result["status"] == "yielded":
                return {"status": "yielded", "scans": scans}
            if lifecycle:
                lifecycle.progress(completed=index + 1, total=len(profiles))
        scan = False
    for index, p in enumerate(profiles):
        if not scan and should_yield and should_yield():
            return {"status": "yielded", "scans": scans}
        if lifecycle:
            lifecycle.phase(
                "inventory-import",
                deadline_seconds=(
                    engine.config.inventory_timeout_seconds
                    + engine.config.work_batch_size * 180
                    + 120
                ),
                completed=index,
                total=len(profiles),
            )
        options = {}
        if should_yield:
            options["should_yield"] = should_yield
            if lifecycle:
                options["on_item"] = lambda done, total: lifecycle.progress(
                    completed=done, total=total
                )
        result = None
        if scan:
            if inventory_only:
                options["inventory_only"] = True
            result = engine.scan(p.name, force=force, **options)
            options.pop("inventory_only", None)
            scans.append(result)
            if result["status"] == "yielded":
                return {"status": "yielded", "scans": scans}
        # A scan already performs recovery and one pending batch. Between
        # inventories the worker continues those jobs without a fresh scan.
        pending_cycle = drain_pending is True and (
            not scan or inventory_only or (result and result["status"] == "not_due")
        )
        legacy_pending = drain_pending is None and result and result["status"] == "not_due"
        if pending_cycle or legacy_pending:
            if should_yield and should_yield():
                return {"status": "yielded", "scans": scans}
            needs_reconcile = reconcile_pending and has_unreconciled_scan(engine, p)
            if pending_cycle and not has_pending_work(engine, p) and not needs_reconcile:
                continue
            with engine.lease():
                if should_yield and should_yield():
                    return {"status": "yielded", "scans": scans}
                if pending_cycle:
                    try:
                        engine.health(p)
                    except OSError, ValueError:
                        continue
                    if engine.recover(p, should_yield=should_yield):
                        return {"status": "yielded", "scans": scans}
                    from media_agent.media_import.extras import recover as recover_extras
                    from media_agent.media_import.variants import recover as recover_variants

                    if recover_extras(engine, p, should_yield=should_yield):
                        return {"status": "yielded", "scans": scans}
                    if recover_variants(engine, should_yield=should_yield):
                        return {"status": "yielded", "scans": scans}
                yielded = engine.process_pending(p, **options)
                if not yielded and needs_reconcile and not (should_yield and should_yield()):
                    engine.reconcile(p)
                    mark_reconciled(engine, p)
            if yielded:
                return {"status": "yielded", "scans": scans}
        if lifecycle:
            lifecycle.progress(completed=index + 1, total=len(profiles))
    if should_yield and should_yield():
        return {"status": "yielded", "scans": scans}
    if not enrichment:
        return {
            "status": "complete",
            "scans": scans,
            "posters": [],
            "subtitles": [],
            "enrichment_deferred": True,
        }
    limit = engine.config.work_batch_size
    if enrichment_limit is not None:
        limit = min(limit, max(0, enrichment_limit))
    from media_agent.media_import.artwork import PosterJobs, TmdbPosters

    token = getattr(engine.metadata, "token", None)
    if lifecycle:
        lifecycle.phase("poster-batch", deadline_seconds=limit * 180 + 60)
    poster_results = (
        PosterJobs(engine, TmdbPosters(token) if token else None).run(profile=profile, limit=limit)
        if posters
        else []
    )
    if should_yield and should_yield():
        return {"status": "yielded", "scans": scans, "posters": poster_results}
    provider = build_subtitle_provider(engine.config, root) if subtitles else None
    subtitle_results = (
        SubtitleJobs(engine, provider).run(
            refresh=refresh,
            profile=profile,
            limit=limit,
            on_job=(lambda: lifecycle.phase("subtitle-file", deadline_seconds=900))
            if lifecycle
            else None,
        )
        if subtitles
        else []
    )
    return {
        "status": "complete",
        "scans": scans,
        "posters": poster_results,
        "subtitles": subtitle_results,
    }


def has_unreconciled_scan(engine, profile):
    with engine.store._connect() as conn:
        return bool(
            conn.execute(
                "SELECT 1 FROM media_scan_runs WHERE profile=? AND status='complete' "
                "AND id>COALESCE((SELECT CAST(json_extract(payload_json,'$.run_id') AS INTEGER) "
                "FROM media_events WHERE event='background_reconcile_checkpoint' "
                "AND json_extract(payload_json,'$.profile')=? ORDER BY id DESC LIMIT 1),0) LIMIT 1",
                (profile.name, profile.name),
            ).fetchone()
        )


def mark_reconciled(engine, profile):
    with engine.store._connect() as conn:
        row = conn.execute(
            "SELECT MAX(id) FROM media_scan_runs WHERE profile=? AND status='complete'",
            (profile.name,),
        ).fetchone()
        if row[0] is not None:
            conn.execute(
                "INSERT INTO media_events(source_id,event,created,payload_json) "
                "VALUES(NULL,'background_reconcile_checkpoint',?,?)",
                (engine.clock(), json.dumps({"profile": profile.name, "run_id": row[0]})),
            )


def has_pending_work(engine, profile):
    """Check durable state without touching source or library filesystems."""
    execute = engine.config.import_policy == "execute"
    with engine.store._connect() as conn:
        source = conn.execute(
            "SELECT 1 FROM media_source_files s "
            "LEFT JOIN media_import_jobs j ON j.source_id=s.id "
            "WHERE s.profile=? AND s.missing_count=0 AND s.status!='removed' "
            "AND s.stable_count>=2 AND COALESCE(s.readiness,'')!='completion_unverified' "
            "AND (s.status!='review_required' OR j.status IN ('reviewed','retrying')) "
            "AND (j.source_id IS NULL OR j.status IN ('retrying','reviewed','blocked_destination') "
            "OR (j.status='planned' AND ?)) "
            "AND NOT EXISTS (SELECT 1 FROM media_extra_attachments e WHERE e.source_id=s.id) "
            "LIMIT 1",
            (profile.name, execute),
        ).fetchone()
        if source:
            return True
        publication = conn.execute(
            "SELECT 1 FROM media_publications u JOIN media_artifacts a ON a.id=u.artifact_id "
            "WHERE a.profile=? AND u.status='pending' AND "
            "((a.kind IN ('video','poster') AND ?) OR "
            "(a.kind NOT IN ('video','poster') AND ?)) LIMIT 1",
            (profile.name, execute, engine.config.subtitle_policy == "execute"),
        ).fetchone()
        if publication:
            return True
        if not execute:
            return False
        return bool(
            conn.execute(
                "SELECT 1 FROM media_extra_attachments WHERE "
                "status IN ('pending','temporary','linked','cleanup') "
                "AND json_extract(baseline_json,'$.source_profile')=? LIMIT 1",
                (profile.name,),
            ).fetchone()
            or conn.execute(
                "SELECT 1 FROM media_variant_switches "
                "WHERE status IN ('pending','temporary','linked','retire') LIMIT 1"
            ).fetchone()
        )


def build_subtitle_provider(options, root):
    from media_agent.media_import.subtitles.assrt import Assrt
    from media_agent.media_import.subtitles.pool import ProviderPool, Unavailable
    from media_agent.media_import.subtitles.provider import ProviderError
    from media_agent.media_import.subtitles.subdl import Subdl
    from media_agent.media_import.subtitles.zimuku import Zimuku

    factories = {
        "opensubtitlescom": OpenSubtitles,
        "assrt": Assrt,
        "subdl": Subdl,
        "zimuku": Zimuku,
    }
    configured = [(p.name, p.secret_ref) for p in options.subtitle_providers if p.enabled]
    if not options.subtitle_providers:
        if not options.opensubtitles_secret_ref:
            return None
        configured = [("opensubtitlescom", options.opensubtitles_secret_ref)]
    providers = []
    for name, ref in configured:
        try:
            path = resolve_runtime_secret_path(ref, root) if ref else None
            credentials = json.loads(path.read_text()) if path and path.is_file() else {}
            if not isinstance(credentials, dict):
                raise ValueError("invalid credentials")
            providers.append(factories[name](credentials))
        except OSError, ValueError, KeyError, ProviderError:
            providers.append(Unavailable(name))
    return ProviderPool(providers) if providers else None
