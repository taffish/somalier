#!/usr/bin/env python3
"""Self-consistent local receipts are not sufficient evidence for a fixed reference."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import resource_validation as rv

def seal(root, payloads, identity, source):
    (root / "resource.json").write_text(json.dumps(dict(schema=rv.SCHEMA, resource=identity,
                                                      members=len(payloads), source=source)))
    sums = "".join(f"{rv.digest(p)}  {p.relative_to(root)}\n" for p in sorted([root/"resource.json", *payloads]))
    (root/"SHA256SUMS").write_text(sums); (root/"READY").write_text(rv.digest(root/"SHA256SUMS") + "\n")

class Libraries(unittest.TestCase):
    def test_fixed_archive_content_survives_receipt_resealing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); d=root/"1kg-somalier"; d.mkdir()
            p=d/"ref.somalier"; p.write_bytes(b"reference")
            item=dict(files=1,expanded_bytes=9)
            payload=hashlib.sha256(f"{rv.digest(p)}  1kg-somalier/ref.somalier\n".encode()).hexdigest()
            with patch.dict(rv.CATALOG, {"fixture":item}), patch.dict(rv.FIXED_PAYLOAD, {"fixture":payload}):
                seal(root,[p],"fixture",item); rv.verify(root,"fixture")
                p.write_bytes(b"not right"); seal(root,[p],"fixture",item)
                with self.assertRaisesRegex(ValueError,"fixed official archive"): rv.verify(root,"fixture")

    def test_local_vcf_and_compressed_input(self):
        with tempfile.TemporaryDirectory() as temp:
            raw=b"##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
            for zipped in (True,False):
                p=Path(temp)/("sites.vcf.gz" if zipped else "sites.vcf")
                for rows in [b"1\t99\t.\tA\tG\t.\tPASS\t.\n", b"", b"not a row\n"]:
                    content=raw+rows
                    p.write_bytes(gzip.compress(content) if zipped else content)
                    if rows.startswith(b"1\t"): rv.validate_sites(p)
                    else:
                        with self.assertRaises(ValueError): rv.validate_sites(p)

if __name__=="__main__":
    unittest.main()
