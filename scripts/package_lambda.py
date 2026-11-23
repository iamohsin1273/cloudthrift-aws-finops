"""Build a reproducible source-only Lambda zip; Lambda supplies boto3/botocore."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

root = Path(__file__).resolve().parents[1]
source = root / "src"
target = root / "build" / "cloudthrift.zip"
target.parent.mkdir(exist_ok=True)
with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted((source / "cloudthrift").rglob("*.py")):
        info = ZipInfo(path.relative_to(source).as_posix(), (1980, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, path.read_bytes())
print(target)
