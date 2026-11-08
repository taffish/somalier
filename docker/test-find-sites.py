#!/usr/bin/env python3
"""Verify the v0.3.7 INFO normalization contract on tiny synthetic VCFs."""
import gzip
import math
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1])
root.mkdir()
for an, af, existing in (("AN", "AF", False), ("NALT", "AF", False),
                         ("AN", "FALT", False), ("NALT", "FALT", False),
                         ("NALT", "FALT", True)):
    name = f"{an}-{af}-{int(existing)}"
    input_vcf = root / f"{name}.vcf"
    output = root / f"{name}.vcf.gz"
    numeric = {an: ("1", "Integer"), af: ("A", "Float"), "AC": ("A", "Integer")}
    if existing:
        numeric.update(AN=("1", "Integer"), AF=("A", "Float"))
    columns = "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
    lines = ["##fileformat=VCFv4.2", "##contig=<ID=1,length=20000>"]
    lines += [f'##INFO=<ID={key},Number={n},Type={typ},Description="Synthetic test">'
              for key, (n, typ) in numeric.items()]
    lines.append(columns)
    for pos, number, freq in ((101, 200, 0.48), (5001, 120, 0.32), (9501, 4, 0.01)):
        info = f"{an}={number};AC=8;{af}={freq}"
        if existing:
            info += ";AN=2;AF=0.99"
        lines.append(f"1\t{pos}\trsTest\tA\tG\t.\tPASS\t{info}")
    input_vcf.write_text("\n".join(lines) + "\n")
    subprocess.run(["somalier", "find-sites", "--AN-field", an, "--AF-field", af,
                    "--min-AN", "10", "--min-AF", "0.1", "--snp-dist", "100",
                    "--output-vcf", str(output), str(input_vcf)], check=True)
    with gzip.open(output, "rt") as stream:
        records = stream.read().splitlines()
    for key in ("AN", "AF"):
        assert sum(line.startswith(f"##INFO=<ID={key},") for line in records) == 1, name
    actual = {}
    for line in records:
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        fields = dict(entry.split("=", 1) for entry in parts[7].split(";"))
        assert set(fields) == {"AN", "AF"} and parts[2] == ".", (name, line)
        actual[int(parts[1])] = (int(fields["AN"]), float(fields["AF"]))
    assert actual.keys() == {101, 5001}, (name, actual)
    assert actual[101][0] == 200 and math.isclose(actual[101][1], .48, abs_tol=1e-6)
    assert actual[5001][0] == 120 and math.isclose(actual[5001][1], .32, abs_tol=1e-6)
    print("INFO normalization PASS:", name)
