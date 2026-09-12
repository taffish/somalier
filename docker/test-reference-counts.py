#!/usr/bin/env python3
"""用合成 format-v2 sketch 经真实 CLI 验证 0.3.5 REF/ALT 计数修复。"""
import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys


def main():
    root = Path(sys.argv[1]).resolve()
    root.mkdir()  # 调用者提供唯一 scratch；拒绝复用已有测试目录。
    header = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    autosomes = [f"1\t{i + 1}\t.\t" + ("G\tC" if i % 2 == 0 else "A\tG")
                 + "\t.\tPASS\tAF=0.2\n" for i in range(20)]
    autosomes += ["1\t21\t.\tT\tC\t.\tPASS\tAF=0.2\n"]
    xrows = [f"chrX\t{i + 1}\t.\tT\tC\t.\tPASS\tAF=0.2\n" for i in range(5)]
    yrows = ["chrY\t1\t.\tT\tC\t.\tPASS\tAF=0.2\n"]
    sites = root / "sites.vcf"
    sites.write_text(header + "".join(reversed(autosomes + xrows + yrows)))
    ac = [(0, 80, 0) if i % 2 == 0 else (80, 0, 0) for i in range(20)] + [(0, 0, 0)]
    xc = [(0, 80, 0), (0, 80, 0), (80, 0, 0), (40, 40, 0), (0, 0, 0)]
    yc = [(0, 80, 0)]
    sketches = []
    # common.nim/write_counts: version/name-length uint8, name, three uint16 lengths,
    # then three uint32 allele counts per site, in autosomal/X/Y bucket order.
    for name in ("sampleA", "sampleB"):
        sketch = root / (name + ".somalier")
        payload = struct.pack("<BB", 2, len(name)) + name.encode()
        payload += struct.pack("<HHH", len(ac), len(xc), len(yc))
        payload += b"".join(struct.pack("<III", *counts) for counts in ac + xc + yc)
        sketch.write_bytes(payload)
        sketches.append(sketch)
    original = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sketches}

    def run(label, selected_sites=None, expected_error=None):
        argv = ["somalier", "relate", "--output-prefix", str(root / label)]
        if selected_sites:
            argv += ["--sites", str(selected_sites)]
        argv += list(map(str, sketches))
        result = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=60)
        (root / (label + ".log")).write_text(result.stdout)
        ok = (result.returncode != 0 and expected_error in result.stdout) if expected_error else result.returncode == 0
        if not ok:
            print(f"reference-counts stage={label} exit={result.returncode}", file=sys.stderr)
            print("\n".join(result.stdout.splitlines()[-80:]), file=sys.stderr)
            raise AssertionError(label)
        return result.stdout

    legacy_log = run("legacy")
    assert "no --sites given" in legacy_log
    run("oriented", sites)
    for label, auto_expected, x_expected in (("legacy", (10, 0, 10, 1), (1, 1, 2)),
                                             ("oriented", (20, 0, 0, 1), (2, 1, 1))):
        with (root / (label + ".samples.tsv")).open() as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        assert len(rows) == 2
        for row in rows:
            assert tuple(int(row[k]) for k in ("n_hom_ref", "n_het", "n_hom_alt", "n_unknown")) == auto_expected
            assert tuple(int(row[k]) for k in ("X_hom_ref", "X_het", "X_hom_alt")) == x_expected
        html = (root / (label + ".html")).read_text()
        samples, _ = json.JSONDecoder().raw_decode(html.split("var sample_data = ", 1)[1].lstrip())
        assert len(samples) == 2
        for row in samples:
            assert tuple(row[k] for k in ("n_hom_ref", "n_het", "n_hom_alt", "n_unknown")) == auto_expected
            assert tuple(row[k] for k in ("x_hom_ref", "x_het", "x_hom_alt")) == x_expected
    assert (root / "legacy.pairs.tsv").read_bytes() == (root / "oriented.pairs.tsv").read_bytes()
    for bucket, records in (("autosomal", autosomes[:-1] + xrows + yrows),
                            ("X", autosomes + xrows[:-1] + yrows), ("Y", autosomes + xrows)):
        bad = root / (bucket + ".vcf")
        bad.write_text(header + "".join(records))
        run("mismatch-" + bucket, bad, expected_error=f"{bucket} sites, expected")
    assert original == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sketches}
    print("reference-counts=autosomal-X-TSV-HTML-pairs-unchanged-three-mismatch-reject PASS")


if __name__ == "__main__":
    main()
