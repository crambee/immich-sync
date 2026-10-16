import asyncio
import aiohttp
from tqdm import tqdm
from pathlib import Path
from .api import ImmichAPI
from .utils import delete_orphans, compute_checksum


def _file_name(aid: str, desc: str, orig: str, used: set, naming: str) -> str:
    """Name files per `naming`, falling down to the asset id (unique).

    naming: "description" | "original" | "id" — the first name tried, in
    order description > originalFileName > asset id.

    shortcut: 60-char cap on the description; it fits ext4's 255-byte
    limit even for 4-byte chars. Raise if you need longer captions.
    """
    ext = Path(orig).suffix
    line = desc.splitlines()[0].strip().replace("/", "-")[:60].lstrip(".") if desc else ""
    order = []
    if naming == "description" and line:
        order.append(f"{line}{ext}")
    if naming in ("description", "original") and Path(orig).name:
        order.append(Path(orig).name)
    order.append(f"{aid}{ext}")
    for cand in order:
        if cand not in used:
            used.add(cand)
            return cand


async def _run(cfg):
    api = ImmichAPI(cfg.url, cfg.apikey)
    photodir = cfg.photodir
    photodir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(5)

    async with aiohttp.ClientSession() as session:
        # 1. find album
        shared = await api.list_albums(session, shared=True)
        all_albums = shared + await api.list_albums(session, shared=False)
        album = next((a for a in all_albums if a["albumName"] == cfg.album), None)
        if album is None:
            raise ValueError(f"Album '{cfg.album}' not found")
        album_id = str(album["id"])

        # 2. list assets
        # Newer Immich API: the album no longer embeds its assets, so fetch
        # them from the search endpoint instead.
        album_data = await api.get_album(session, album_id)
        if "assets" in album_data:
            assets = album_data["assets"]
        else:
            assets = await api.get_album_assets(session, album_id)

        # 3. fetch metadata
        tasks_info = [api.fetch_asset_info(session, str(a["id"]), sem) for a in assets]
        assetinfos = []
        with tqdm(
            total=len(tasks_info), desc="Downloading AssetInfo", unit="asset"
        ) as p:
            for coro in asyncio.as_completed(tasks_info):
                info = await coro
                assetinfos.append(info)
                p.update(1)

        # 4. decide which to download
        total_bytes = 0
        done_bytes = 0
        to_download = []
        done_ids = []
        used_names = set()
        keep_names = set()

        with tqdm(
            total=len(assetinfos), desc="Processing Checksums", unit="asset"
        ) as p:
            for info in assetinfos:
                aid = str(info["id"])
                size = info.get("fileSize", 0)
                if size == 0:
                    size = await api.fetch_asset_size(session, aid, sem)
                total_bytes += size

                orig = info.get("originalFileName", "")
                desc = (info.get("exifInfo") or {}).get("description") or ""
                dest = photodir / _file_name(aid, desc, orig, used_names, cfg.naming)
                keep_names.add(dest.name)
                if cfg.raw and dest.suffix.lower() != ".jpg":
                    keep_names.add(dest.with_suffix(".jpg").name)

                if dest.exists():
                    try:
                        if compute_checksum(dest) == info.get("checksum"):
                            done_bytes += size
                            done_ids.append(aid)
                            p.update(1)
                            continue
                    except Exception:
                        pass

                to_download.append((info, dest))
                p.update(1)

        # 5. download loop
        overall = tqdm(
            total=total_bytes,
            unit="B",
            unit_scale=True,
            initial=done_bytes,
            desc="Overall Download",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
        )

        async def process(info, dest):
            aid = str(info["id"])
            temp = dest.with_name(dest.name + ".part")
            if temp.exists():
                temp.unlink()

            for i in range(3):
                try:
                    url = f"{api.base_url}/api/assets/{aid}/original"
                    async with session.get(url, headers=api.headers_octo) as r:
                        r.raise_for_status()
                        total = int(
                            r.headers.get("Content-Length", info.get("fileSize", 0))
                        )
                        with tqdm(
                            total=total,
                            unit="B",
                            unit_scale=True,
                            desc=f"Downloading {dest.name}",
                            leave=False,
                        ) as pbar:
                            with temp.open("wb") as f:
                                async for chunk in r.content.iter_chunked(1024):
                                    f.write(chunk)
                                    pbar.update(len(chunk))
                                    overall.update(len(chunk))
                    temp.replace(dest)
                    break
                except Exception:
                    if temp.exists():
                        temp.unlink()
                    if i < 2:
                        await asyncio.sleep(2**i)
                    else:
                        raise

            # raw thumbnail
            if cfg.raw and dest.suffix.lower() != ".jpg":
                try:
                    import rawpy
                    import imageio

                    with rawpy.imread(str(dest)) as raw_img:
                        thumb = raw_img.extract_thumb()
                        jpg = dest.with_suffix(".jpg")
                        if thumb.format == rawpy.ThumbFormat.JPEG:
                            with jpg.open("wb") as f:
                                f.write(thumb.data)
                        else:
                            imageio.imwrite(str(jpg), thumb.data)
                except Exception:
                    pass

            return aid

        downloaded = done_ids + await asyncio.gather(
            *(process(i, d) for i, d in to_download)
        )
        overall.close()

    delete_orphans(photodir, keep_names)
    return downloaded


def sync_album(cfg):
    return asyncio.run(_run(cfg))
