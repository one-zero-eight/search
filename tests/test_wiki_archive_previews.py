"""Preview identity comes from shipped metadata, not retained binaries or a rebuild."""

import hashlib
import json
import socket

import httpx
import pytest
import yaml

from catix.settings import settings
from catix.wiki import previews
from catix.wiki.search_index import fingerprint

URL = "https://innopolis.university/programmes.zip"
MEMBER = "first/Б1.О.01_Algebra.pdf"
SHA = hashlib.sha256(b"original PDF bytes not installed in the checkout").hexdigest()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "wiki_root", tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("describing metadata must not download, unpack, crawl or compile")

    from catix.wiki.sources import archive_documents, archives, regulations, rpd, sites

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden)
    for module, name in [(archive_documents, "download"), (archives, "unpack"),
                         (regulations, "all_docs"), (regulations, "compile_all"),
                         (rpd, "archives"), (rpd, "compile_all"), (sites, "docs")]:
        monkeypatch.setattr(module, name, forbidden)
    return tmp_path


def write_json(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_page(root, key, *, folder="course-programmes", member=None, source_id=SHA[:12], **extra):
    meta = {"type": "course-programme" if folder == "course-programmes" else "regulation",
            "title": "Same title", "resource": URL,
            "sources": [{"resource": URL, "id": source_id}], **extra}
    if member is not None:
        meta["archive_member"] = member
    text = "---\n" + yaml.safe_dump(meta, allow_unicode=True) + "---\n\n# Same title\n\nOriginal evidence.\n"
    page = f"/raw/{folder}/{key}.md"
    target = root / "wiki" / page.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return page, fingerprint(text), URL


def rpd_key(member=MEMBER):
    return "rpd-" + hashlib.sha1(f"{URL}/{member}".encode()).hexdigest()[:8] + "-same-title"


def rpd_metadata(root, *, member=MEMBER, sha=SHA):
    key = rpd_key(member)
    entry = {"archive": URL, "member": member, "sha256": sha}
    path = write_json(root, "raw/rpd/index.json", {key: entry})
    return key, path, entry


@pytest.mark.parametrize("source_id", [SHA[:12], SHA])
def test_rpd_existing_page_needs_only_shipped_index(bundle, source_id):
    key, _, entry = rpd_metadata(bundle)
    args = write_page(bundle, key, source_id=source_id)
    before = {p: p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
    assert previews.describe(*args) == {"page": args[0], "revision": args[1], "member": MEMBER}
    meta = previews._metadata(*args)
    assert meta is not None
    assert meta["archive_member"] == entry["member"]
    assert meta["sha256"] == SHA
    assert before == {p: p.read_bytes() for p in bundle.rglob("*") if p.is_file()}


def general_metadata(root, *, location="raw/sites/university/docs", member=MEMBER, sha=SHA):
    base = "site-university-programmes"
    key = base + "-member-" + hashlib.sha256(f"{URL}\n{member}".encode()).hexdigest()[:20]
    entry = {"key": key, "status": "ready", "ext": "pdf", "member": member, "sha256": sha}
    path = write_json(root, f"{location}/{base}.archive.json", {"url": URL, "status": "ready", "members": [entry]})
    return key, path, entry


@pytest.mark.parametrize("location", ["raw/sites/university/docs", "raw/regulations"])
def test_general_manifest_selects_exact_member_without_binaries(bundle, location):
    key, path, entry = general_metadata(bundle, location=location)
    other = {**entry, "key": key + "-other", "member": "other/Algebra.pdf", "sha256": "1" * 64}
    write_json(bundle, path.relative_to(bundle), {"url": URL, "status": "ready", "members": [other, entry]})
    args = write_page(bundle, key, folder="regulations", member=MEMBER)
    assert previews.describe(*args) == {"page": args[0], "revision": args[1], "member": MEMBER}
    meta = previews._metadata(*args)
    assert meta is not None
    assert meta["sha256"] == SHA


def existing(root, kind, **page_fields):
    key, path, entry = rpd_metadata(root) if kind == "rpd" else general_metadata(root)
    args = write_page(root, key, folder="course-programmes" if kind == "rpd" else "regulations",
                      member=MEMBER if kind == "general" else None, **page_fields)
    assert previews.describe(*args) is not None
    return args, path, entry


@pytest.mark.parametrize("kind", ["rpd", "general"])
@pytest.mark.parametrize("change", ["sha256", "short-sha", "member", "url", "missing", "invalid", "wrong-shape"])
def test_refreshed_or_broken_source_metadata_is_not_an_old_page_revision(bundle, kind, change):
    args, path, _ = existing(bundle, kind)
    raw = json.loads(path.read_text())
    record = raw[rpd_key()] if kind == "rpd" else raw["members"][0]
    if change == "sha256":
        record["sha256"] = "f" * 64
    elif change == "short-sha":
        record["sha256"] = SHA[:12]
    elif change == "member":
        record["member"] = "different/Algebra.pdf"
    elif change == "url":
        (record if kind == "rpd" else raw)["archive" if kind == "rpd" else "url"] = URL + "?changed"
    elif change == "missing":
        raw = {}
    elif change == "wrong-shape":
        raw = []
    path.write_text("invalid json" if change == "invalid" else json.dumps(raw))
    assert previews.describe(*args) is None


@pytest.mark.parametrize("kind", ["rpd", "general"])
@pytest.mark.parametrize("change", ["member", "source-id", "source-url", "resource", "no-sources", "bad-sources"])
def test_compiled_identity_must_agree_with_raw_metadata(bundle, kind, change):
    args, _, _ = existing(bundle, kind)
    path = bundle / "wiki" / args[0].lstrip("/")
    front = yaml.safe_load(path.read_text().split("---", 2)[1])
    if change == "member":
        front["archive_member"] = "wrong/Algebra.pdf"
    elif change == "source-id":
        front["sources"][0]["id"] = "0" * 12
    elif change == "source-url":
        front["sources"][0]["resource"] = URL + "?different"
    elif change == "resource":
        front["resource"] = URL + "?different"
    elif change == "no-sources":
        front.pop("sources")
    else:
        front["sources"] = None
    text = "---\n" + yaml.safe_dump(front) + "---\n\nEvidence\n"
    path.write_text(text)
    assert previews.describe(args[0], fingerprint(text), URL) is None


@pytest.mark.parametrize("kind", ["rpd", "general"])
def test_compiled_page_must_match_indexed_fingerprint(bundle, kind):
    args, _, _ = existing(bundle, kind)
    path = bundle / "wiki" / args[0].lstrip("/")
    path.write_text(path.read_text() + "\nChanged evidence\n")
    assert previews.describe(*args) is None


@pytest.mark.parametrize("member", ["../original.pdf", "/original.pdf", "a/../original.pdf", "a\\original.pdf",
                                    "C:/original.pdf", "a//original.pdf", "a/./original.pdf", "a/\x00original.pdf",
                                    "a/\noriginal.pdf", "original.doc"])
def test_unsafe_or_non_pdf_member_is_refused_even_with_matching_metadata(bundle, member):
    key, _, _ = rpd_metadata(bundle, member=member)
    args = write_page(bundle, key, member=member)
    assert previews.describe(*args) is None


@pytest.mark.parametrize("part", ["page", "wiki-root", "raw-root", "index", "sites-root", "manifest"])
def test_symlinks_cannot_escape_wiki_root(bundle, tmp_path_factory, part):
    kind = "general" if part in {"sites-root", "manifest"} else "rpd"
    args, metadata, _ = existing(bundle, kind)
    outside = tmp_path_factory.mktemp("outside-preview-root") / "moved"
    target = {"page": bundle / "wiki" / args[0].lstrip("/"), "wiki-root": bundle / "wiki",
              "raw-root": bundle / "raw", "index": metadata, "sites-root": bundle / "raw/sites",
              "manifest": metadata}[part]
    target.rename(outside)
    target.symlink_to(outside, target_is_directory=outside.is_dir())
    assert previews.describe(*args) is None


@pytest.mark.parametrize("kind", ["rpd", "general"])
def test_same_archive_same_title_siblings_keep_distinct_exact_identities(bundle, kind):
    args, path, entry = existing(bundle, kind)
    member, digest = "second/Б1.О.01_Algebra.pdf", hashlib.sha256(b"second PDF").hexdigest()
    if kind == "rpd":
        key = rpd_key(member)
        raw = {rpd_key(): entry, key: {"archive": URL, "member": member, "sha256": digest}}
    else:
        key = entry["key"].rpartition("-member-")[0] + "-member-" + hashlib.sha256(f"{URL}\n{member}".encode()).hexdigest()[:20]
        raw = {"url": URL, "status": "ready", "members": [entry, {**entry, "key": key, "member": member, "sha256": digest}]}
    path.write_text(json.dumps(raw))
    other = write_page(bundle, key, folder="course-programmes" if kind == "rpd" else "regulations",
                       member=member if kind == "general" else None, source_id=digest[:12])
    assert previews.describe(*args) == {"page": args[0], "revision": args[1], "member": MEMBER}
    assert previews.describe(*other) == {"page": other[0], "revision": other[1], "member": member}
    original_meta, other_meta = previews._metadata(*args), previews._metadata(*other)
    assert original_meta is not None and other_meta is not None
    assert (original_meta["sha256"], other_meta["sha256"]) == (SHA, digest)


@pytest.mark.parametrize("change", ["duplicate-entry", "duplicate-manifest", "wrong-key", "wrong-ext", "not-ready",
                                    "wrong-basename", "wrong-root", "members-null", "manifest-not-ready"])
def test_general_lookup_never_guesses_or_uses_an_ambiguous_manifest(bundle, change):
    args, path, entry = existing(bundle, "general")
    data = json.loads(path.read_text())
    if change == "duplicate-entry":
        data["members"].append(entry)
    elif change == "duplicate-manifest":
        write_json(bundle, f"raw/sites/other/docs/{path.name}", data)
    elif change == "wrong-key":
        data["members"][0]["key"] += "-other"
    elif change == "wrong-ext":
        data["members"][0]["ext"] = "doc"
    elif change == "not-ready":
        data["members"][0]["status"] = "unsafe"
    elif change == "manifest-not-ready":
        data["status"] = "invalid"
    elif change == "members-null":
        data["members"] = None
    elif change == "wrong-basename":
        path.rename(path.with_name("unrelated.archive.json"))
        assert previews.describe(*args) is None
        return
    elif change == "wrong-root":
        elsewhere = write_json(bundle, f"raw/sveden/{path.name}", data)
        assert elsewhere.is_file()
        path.unlink()
        assert previews.describe(*args) is None
        return
    path.write_text(json.dumps(data))
    assert previews.describe(*args) is None


@pytest.mark.parametrize("page", ["/raw/course-programmes/../page.md", "/raw/course-programmes//page.md",
                                  "/raw/course-programmes/./page.md", "/raw/course-programmes/page.md/extra",
                                  "/raw/other/page.md", "raw/course-programmes/page.md", "/raw/course-programmes/a\\b.md"])
def test_unsafe_or_wrong_page_paths_are_refused(bundle, page):
    args, _, _ = existing(bundle, "rpd")
    assert previews.describe(page, args[1], URL) is None


@pytest.mark.parametrize("kind", ["rpd", "general"])
def test_mismatched_resource_or_revision_is_refused(bundle, kind):
    args, _, _ = existing(bundle, kind)
    assert previews.describe(args[0], args[1], URL + "?other") is None
    assert previews.describe(args[0], "0" * 16, URL) is None
    assert previews.describe(args[0], "unknown", URL) is None


@pytest.mark.parametrize("which", ["metadata", "page"])
def test_oversized_metadata_is_refused(bundle, which, monkeypatch):
    args, path, _ = existing(bundle, "rpd")
    if which == "page":
        path = bundle / "wiki" / args[0].lstrip("/")
    path.write_text(path.read_text() + " " * 4096)
    monkeypatch.setattr(previews, "MAX_PAGE_BYTES", 4096)
    assert previews.describe(*args) is None


def test_general_generated_member_key_is_validated_before_metadata_lookup(bundle):
    args, path, entry = existing(bundle, "general")
    wrong_key = entry["key"].rpartition("-member-")[0] + "-member-" + "0" * 20
    entry["key"] = wrong_key
    path.write_text(json.dumps({"url": URL, "status": "ready", "members": [entry]}))
    wrong_args = write_page(bundle, wrong_key, folder="regulations", member=MEMBER)
    assert previews.describe(*wrong_args) is None


def test_rpd_lookup_uses_requested_page_stem_not_a_symlink_targets_stem(bundle):
    args, _, _ = existing(bundle, "rpd")
    original = bundle / "wiki" / args[0].lstrip("/")
    alias = original.with_name("rpd-00000000-alias.md")
    alias.symlink_to(original)
    assert previews.describe("/raw/course-programmes/" + alias.name, args[1], URL) is None
