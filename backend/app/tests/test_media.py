"""Media endpoint tests — with the per-user isolation (404) and SQLi cases."""
import pytest

from app.tests.conftest import upload_data, txt_bytes


def _upload(client, headers, filename, data, **meta):
    return client.post("/media", data=upload_data(filename, data, **meta), headers=headers)


def _new_version(client, headers, media_id):
    # Manual "+ New version" clones the current version's content (no file).
    return client.post(f"/media/{media_id}/versions", headers=headers)


# --- Upload validation --------------------------------------------------------

@pytest.mark.parametrize("key", ["png", "jpg", "pdf", "txt"])
def test_upload_each_valid_type_201(client, auth_headers, samples, key):
    filename, data = samples[key]
    resp = _upload(client, auth_headers, filename, data)
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["original_name"] == filename
    assert body["size_bytes"] == len(data)
    # Images get a thumbnail; pdf/txt do not.
    assert body["has_thumbnail"] is (key in ("png", "jpg"))


def test_same_name_upload_becomes_new_version(client, auth_headers, samples):
    fname, data = samples["png"]
    first = _upload(client, auth_headers, fname, data).get_json()
    second = _upload(client, auth_headers, fname, data).get_json()
    # Same item (not a new file), now with two versions.
    assert second["id"] == first["id"]
    versions = client.get(f"/media/{first['id']}/versions", headers=auth_headers).get_json()
    assert [v["version_no"] for v in versions] == [2, 1]
    # The list still shows a single item.
    assert len(client.get("/media", headers=auth_headers).get_json()) == 1


def test_upload_forged_type_400(client, auth_headers, samples):
    # Text bytes wearing a .png name -> content check rejects it.
    resp = _upload(client, auth_headers, *samples["forged_png"])
    assert resp.status_code == 400


def test_upload_disallowed_extension_400(client, auth_headers):
    resp = _upload(client, auth_headers, "shell.exe", b"MZ\x90\x00binary")
    assert resp.status_code == 400


def test_upload_over_10mb_413(client, auth_headers):
    big = b"a" * (10 * 1024 * 1024 + 1)  # valid text, but over the limit
    resp = _upload(client, auth_headers, "big.txt", big)
    assert resp.status_code == 413


def test_thumbnail_sets_cache_headers_and_304(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["png"]).get_json()

    r1 = client.get(f"/media/{up['id']}/thumbnail", headers=auth_headers)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag
    assert "max-age" in r1.headers.get("Cache-Control", "")

    # Re-request with the same validator -> 304 Not Modified, empty body.
    r2 = client.get(
        f"/media/{up['id']}/thumbnail",
        headers={**auth_headers, "If-None-Match": etag},
    )
    assert r2.status_code == 304
    assert r2.data == b""


# --- Listing & isolation ------------------------------------------------------

def test_list_returns_only_callers_media(client, make_user, samples):
    alice, bob = make_user(), make_user()
    _upload(client, alice, *samples["png"])
    _upload(client, bob, *samples["pdf"])

    a_list = client.get("/media", headers=alice).get_json()
    b_list = client.get("/media", headers=bob).get_json()
    assert len(a_list) == 1 and len(b_list) == 1
    assert a_list[0]["original_name"] == "photo.png"
    assert b_list[0]["original_name"] == "doc.pdf"


# --- Search -------------------------------------------------------------------

def test_search_returns_only_my_matching_rows(client, make_user, samples):
    alice, bob = make_user(), make_user()
    _upload(client, alice, "a.png", samples["png"][1], title="Vacation Photos")
    _upload(client, bob, "b.pdf", samples["pdf"][1], title="Vacation Plans")

    res = client.get("/media", query_string={"q": "vacation"}, headers=alice).get_json()
    assert len(res) == 1
    assert res[0]["original_name"] == "a.png"  # never bob's row


def test_search_sqli_or_obfuscated_payload_is_safe(client, auth_headers, samples):
    _upload(client, auth_headers, *samples["png"], title="Holiday")

    for payload in ["' OR '1'='1", "'; DROP TABLE media;--", "%", "_", "1' OR '1'='1"]:
        resp = client.get("/media", query_string={"q": payload}, headers=auth_headers)
        assert resp.status_code == 200          # no 500
        assert resp.get_json() == []            # treated as a literal term -> no match

    # DB intact: the row (and table) survived every payload.
    assert len(client.get("/media", headers=auth_headers).get_json()) == 1


# --- Download -----------------------------------------------------------------

def test_download_own_file_200_with_disposition(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["txt"]).get_json()
    resp = client.get(f"/media/{up['id']}/download", headers=auth_headers)
    assert resp.status_code == 200
    assert 'attachment; filename="note.txt"' in resp.headers["Content-Disposition"]
    assert resp.data == txt_bytes()


def test_download_sets_nosniff_header(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["txt"]).get_json()
    resp = client.get(f"/media/{up['id']}/download", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_download_other_users_file_404(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()
    resp = client.get(f"/media/{up['id']}/download", headers=bob)
    assert resp.status_code == 404  # NOT 403 — don't leak existence


def test_download_link_own_file_returns_url(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    resp = client.get(f"/media/{up['id']}/link", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["url"].startswith("http")
    assert body["expires_in"] > 0


def test_download_link_other_users_file_404(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()
    assert client.get(f"/media/{up['id']}/link", headers=bob).status_code == 404


# --- Delete -------------------------------------------------------------------

def test_delete_other_users_file_404_and_keeps_file(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()

    assert client.delete(f"/media/{up['id']}", headers=bob).status_code == 404
    # Alice's file is untouched.
    assert client.get(f"/media/{up['id']}/download", headers=alice).status_code == 200


def test_delete_own_file_204_and_removes_objects(client, auth_headers, samples, object_store):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    assert len(object_store) == 2  # original + thumbnail

    resp = client.delete(f"/media/{up['id']}", headers=auth_headers)
    assert resp.status_code == 204
    assert object_store == {}  # storage.delete removed both objects
    assert client.get("/media", headers=auth_headers).get_json() == []  # row gone


# --- Versioning ---------------------------------------------------------------

def test_initial_upload_records_version_1(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    versions = client.get(f"/media/{up['id']}/versions", headers=auth_headers).get_json()
    assert len(versions) == 1
    assert versions[0]["version_no"] == 1
    assert versions[0]["is_current"] is True


def test_manual_new_version_clones_current(client, auth_headers):
    up = _upload(client, auth_headers, "f.txt", b"hello\n").get_json()

    r = _new_version(client, auth_headers, up["id"])
    assert r.status_code == 201

    versions = client.get(f"/media/{up['id']}/versions", headers=auth_headers).get_json()
    assert [v["version_no"] for v in versions] == [2, 1]   # newest first
    assert versions[0]["is_current"] is True
    assert versions[1]["is_current"] is False
    # The clone is byte-identical to the version it copied.
    assert client.get(f"/media/{up['id']}/versions/2/download", headers=auth_headers).data == b"hello\n"
    assert client.get(f"/media/{up['id']}/versions/1/download", headers=auth_headers).data == b"hello\n"


def test_download_old_version_returns_original_bytes(client, auth_headers):
    up = _upload(client, auth_headers, "f.txt", b"version one\n").get_json()
    _upload(client, auth_headers, "f.txt", b"version two\n")  # same-name re-upload -> v2

    cur = client.get(f"/media/{up['id']}/download", headers=auth_headers)
    assert cur.data == b"version two\n"                     # current = v2

    old = client.get(f"/media/{up['id']}/versions/1/download", headers=auth_headers)
    assert old.status_code == 200
    assert old.data == b"version one\n"                     # v1 still retrievable


def test_version_routes_reject_other_user(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()
    assert client.get(f"/media/{up['id']}/versions", headers=bob).status_code == 404
    assert _new_version(client, bob, up["id"]).status_code == 404
    assert client.get(f"/media/{up['id']}/versions/1/download", headers=bob).status_code == 404


def test_delete_middle_version_renumbers(client, auth_headers):
    up = _upload(client, auth_headers, "f.txt", b"one\n").get_json()
    _upload(client, auth_headers, "f.txt", b"two\n")        # re-upload same name -> v2
    _upload(client, auth_headers, "f.txt", b"three\n")      # -> v3
    r = client.delete(f"/media/{up['id']}/versions/2", headers=auth_headers)
    assert r.status_code == 200 and r.get_json()["media_deleted"] is False
    assert sorted(v["version_no"] for v in r.get_json()["versions"]) == [1, 2]
    assert client.get(f"/media/{up['id']}/versions/1/download", headers=auth_headers).data == b"one\n"
    assert client.get(f"/media/{up['id']}/versions/2/download", headers=auth_headers).data == b"three\n"


def test_delete_current_version_repoints(client, auth_headers):
    up = _upload(client, auth_headers, "f.txt", b"one\n").get_json()
    _upload(client, auth_headers, "f.txt", b"two\n")        # re-upload same name -> v2
    client.delete(f"/media/{up['id']}/versions/2", headers=auth_headers)
    assert client.get(f"/media/{up['id']}/download", headers=auth_headers).data == b"one\n"


def test_delete_last_version_deletes_media(client, auth_headers, samples, object_store):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    r = client.delete(f"/media/{up['id']}/versions/1", headers=auth_headers)
    assert r.get_json()["media_deleted"] is True
    assert object_store == {}
    assert client.get("/media", headers=auth_headers).get_json() == []


def test_delete_version_other_user_404(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()
    assert client.delete(f"/media/{up['id']}/versions/1", headers=bob).status_code == 404


def test_delete_removes_all_version_objects(client, auth_headers, samples, object_store):
    up = _upload(client, auth_headers, *samples["png"]).get_json()        # v1: 2 objects
    _new_version(client, auth_headers, up["id"])                          # v2 clone: +2
    assert len(object_store) == 4

    assert client.delete(f"/media/{up['id']}", headers=auth_headers).status_code == 204
    assert object_store == {}                               # all versions' objects gone


def test_upload_without_title_defaults_to_no_title(client, auth_headers, samples):
    fname, data = samples["png"]
    resp = client.post("/media", data=upload_data(fname, data, title=""), headers=auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["title"] == "No Title"


def test_reupload_without_title_keeps_old_title(client, auth_headers, samples):
    fname, data = samples["png"]
    first = client.post("/media", data=upload_data(fname, data, title="Original"), headers=auth_headers).get_json()
    assert first["title"] == "Original"
    second = client.post("/media", data=upload_data(fname, data, title=""), headers=auth_headers).get_json()
    assert second["id"] == first["id"]
    assert second["title"] == "Original"  # unchanged when no title given


def test_update_media_title(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    r = client.patch(f"/media/{up['id']}", json={"title": "Renamed"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["title"] == "Renamed"
    # blank title falls back to "No Title"
    r2 = client.patch(f"/media/{up['id']}", json={"title": ""}, headers=auth_headers)
    assert r2.get_json()["title"] == "No Title"


def test_update_media_title_other_user_404(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()
    assert client.patch(f"/media/{up['id']}", json={"title": "x"}, headers=bob).status_code == 404


def test_edit_version_description(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    r = client.patch(f"/media/{up['id']}/versions/1", json={"description": "edited"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["description"] == "edited"
    vs = client.get(f"/media/{up['id']}/versions", headers=auth_headers).get_json()
    assert vs[0]["description"] == "edited"


def test_edit_version_description_other_user_404(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()
    assert client.patch(f"/media/{up['id']}/versions/1",
                        json={"description": "x"}, headers=bob).status_code == 404


def test_version_thumbnail_served_with_cache(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    r = client.get(f"/media/{up['id']}/versions/1/thumbnail", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers.get("ETag")


def test_version_thumbnail_other_user_404(client, make_user, samples):
    alice, bob = make_user(), make_user()
    up = _upload(client, alice, *samples["png"]).get_json()
    assert client.get(f"/media/{up['id']}/versions/1/thumbnail", headers=bob).status_code == 404


def test_media_id_is_opaque_not_sequential(client, auth_headers, samples):
    up = _upload(client, auth_headers, *samples["png"]).get_json()
    # The public id is an opaque random token, not a guessable integer.
    assert isinstance(up["id"], str)
    assert not up["id"].isdigit()
    assert len(up["id"]) >= 16
    # A sequential-integer guess never resolves to a real object.
    assert client.get("/media/1/download", headers=auth_headers).status_code == 404


def test_unexpected_error_returns_json_500(client, auth_headers, samples, monkeypatch):
    from app.services import storage as storage_service

    def boom(*a, **k):
        raise RuntimeError("storage down")

    monkeypatch.setattr(storage_service, "put_object", boom)
    client.application.config["PROPAGATE_EXCEPTIONS"] = False  # let the handler run under TESTING

    fname, data = samples["png"]
    resp = client.post("/media", data=upload_data(fname, data), headers=auth_headers)
    assert resp.status_code == 500
    assert resp.is_json
    assert resp.get_json()["error"] == "server_error"


# --- Auth required ------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("get", "/media"),
    ("post", "/media"),
    ("patch", "/media/1"),
    ("get", "/media/1/download"),
    ("get", "/media/1/link"),
    ("get", "/media/1/thumbnail"),
    ("get", "/media/1/versions"),
    ("post", "/media/1/versions"),
    ("patch", "/media/1/versions/1"),
    ("get", "/media/1/versions/1/download"),
    ("get", "/media/1/versions/1/thumbnail"),
    ("delete", "/media/1/versions/1"),
    ("delete", "/media/1"),
])
def test_media_routes_require_jwt(client, method, path):
    resp = getattr(client, method)(path)
    assert resp.status_code == 401
