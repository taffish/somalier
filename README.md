# somalier

`somalier` packages [Somalier](https://github.com/brentp/somalier) for TAFFISH.

Package identity:

- name: `somalier`
- command: `taf-somalier`
- kind: `tool`
- version: `0.3.3-r1`
- license: Apache-2.0
- upstream: [brentp/somalier](https://github.com/brentp/somalier)

## What This App Packages

Somalier extracts compact genotype sketches from BAM, CRAM, VCF, BCF, or
GVCF data. Those sketches support fast sample-identity, relatedness, pedigree,
ancestry, allele-balance, and contamination analyses. This app exposes the
unmodified upstream `somalier` CLI through a thin TAFFISH wrapper.

The executable is built from the official `v0.3.3` source tag with Nim 2.2.4.
All Nim dependencies are locked to exact revisions. The final image contains
HTSlib and OpenBLAS runtime libraries, but not the compiler, package cache, or
development headers.

## Scope

This app supports every public Somalier 0.3.3 command:

- `extract`: create one `.somalier` sketch per input sample
- `relate`: sample QC, pairwise relatedness, pedigree checking, and inference
- `ancestry`: PCA and neural-network ancestry prediction from labeled sketches
- `AB_plot`: autosomal allele-balance and depth HTML report
- `contamination`: CHARR and directional pairwise contamination estimates
- `find-sites`: derive a sites VCF from a population VCF
- `pedrel`: report expected pairwise relationships from a PED/FAM file

This app does not bundle a production sites VCF, reference genome, ancestry
reference sketches, or project data. Those resources are assembly- and
analysis-specific and remain user supplied.

## Container Contents

- `somalier`: the upstream 0.3.3 executable
- `/opt/somalier/share/ancestry-labels-1kg.tsv`: upstream 1000 Genomes labels
- `/opt/somalier/share/doc/somalier/`: upstream README, change log, citation,
  dependency lock, source provenance, and the documented build-only patch
- `/opt/somalier/share/licenses/somalier/LICENSE`: upstream MIT license
- `/opt/somalier/share/testdata/`: small synthetic and upstream-derived smoke
  fixtures; these are not production reference data

## Usage

Access the upstream command summary:

```sh
taf-somalier -- --help
```

Somalier uses subcommands. With TAFFISH command mode, use the explicit
executable form so `extract`, `relate`, and the other subcommands are not
interpreted as separate container executables:

```sh
taf-somalier somalier extract --help
taf-somalier somalier relate --help
```

Extract from an indexed BAM or CRAM:

```sh
taf-somalier somalier extract \
  --sites sites.hg38.vcf.gz \
  --fasta GRCh38.fa \
  --out-dir sketches \
  sample.bam
```

Extract all samples from an indexed multi-sample VCF or BCF:

```sh
taf-somalier somalier extract \
  --sites sites.hg38.vcf.gz \
  --fasta GRCh38.fa \
  --out-dir sketches \
  cohort.vcf.gz
```

Calculate relatedness and compare against a pedigree:

```sh
taf-somalier somalier relate \
  --sites sites.hg38.vcf.gz \
  --ped cohort.fam \
  --output-prefix cohort \
  sketches/*.somalier
```

For very large cohorts, place one `.somalier` path per line in a file ending
in `.list`, then pass that file to `relate`. This path-list support is the main
upstream change in 0.3.3.

```sh
taf-somalier somalier relate --output-prefix cohort sketches.list
```

Estimate contamination:

```sh
taf-somalier somalier contamination \
  --sites sites.hg38.vcf.gz \
  --output cohort-contamination \
  sketches/*.somalier
```

For a directed tumor-normal estimate, provide tumor first and normal second:

```sh
taf-somalier somalier contamination \
  --sites sites.hg38.vcf.gz \
  --tumor-normal-pair \
  tumor.somalier normal.somalier
```

Create an allele-balance report:

```sh
taf-somalier somalier AB_plot \
  --sites sites.hg38.vcf.gz \
  --output cohort-ab.html \
  sketches/*.somalier
```

## Command Mode

`taf-somalier somalier ...` runs the packaged executable explicitly. This is
the recommended form for upstream subcommands.

Use `taf-somalier -- --help` when passing an option-leading argument to the
default command. Automatic command mode also permits packaged shell utilities,
but no additional bioinformatics CLI is part of this app's public contract.

## Inputs

| Input | Meaning | Notes |
| --- | --- | --- |
| BAM/CRAM | Per-sample alignments | Coordinate index, matching FASTA, and FASTA index are required. Prefer this source when possible. |
| VCF/BCF/GVCF | Variant calls | Indexed compressed VCF/BCF is recommended. Multi-sample inputs create one sketch per sample. |
| sites VCF | Ordered informative variants | Must match the reference assembly used during extraction. Use the same site ordering across samples. |
| reference FASTA | Reference sequence | Must match both the input alignments/calls and sites VCF. Keep its `.fai` beside it. |
| `.somalier` | Compact extracted sketch | Inputs to `relate`, `ancestry`, `AB_plot`, and `contamination`. |
| PED/FAM or groups file | Expected relationships | Optional for `relate`; required by `pedrel`. |
| ancestry labels TSV | Sample ID and label | Used with labeled reference sketches by `ancestry`. |

Somalier uses FORMAT/AD where available. For genotype-only VCFs it derives
fixed pseudo-depths from GT, which is convenient but less informative than
alignment extraction or jointly called data.

## Output Notes

`extract` writes one `<sample>.somalier` binary sketch per sample.

With `--output-prefix cohort`, `relate` writes:

- `cohort.samples.tsv`: sample-level pedigree and QC metrics
- `cohort.pairs.tsv`: pairwise IBS, concordance, and relatedness metrics
- `cohort.groups.tsv`: related sample groups
- `cohort.html`: interactive relatedness report

`contamination -o PREFIX` writes `PREFIX.samples.tsv` and
`PREFIX.pairs.tsv`. `AB_plot` writes one HTML file. `ancestry` writes
`PREFIX.somalier-ancestry.tsv` and `PREFIX.somalier-ancestry.html`.
`find-sites` writes a compressed sites VCF.

## Sites, References, and Ancestry Data

Somalier production sites files are small external reference resources, not a
database embedded in this image. Select the file that matches the coordinate
system and chromosome naming of your FASTA and alignments:

- T2T CHM13v2: <https://github.com/brentp/somalier/files/9954286/sites.chm13v2.T2T.vcf.gz>
- hg19: <https://github.com/brentp/somalier/files/3412453/sites.hg19.vcf.gz>
- GRCh37: <https://github.com/brentp/somalier/files/3412455/sites.GRCh37.vcf.gz>
- hg38 with `chr`: <https://github.com/brentp/somalier/files/3412456/sites.hg38.vcf.gz>
- hg38 without `chr`: <https://github.com/brentp/somalier/files/3412454/sites.hg38.nochr.vcf.gz>
- hg38 RNA-focused: <https://github.com/brentp/somalier/files/4566475/sites.hg38.rna.vcf.gz>

Example download:

```sh
curl -fL \
  https://github.com/brentp/somalier/files/3412456/sites.hg38.vcf.gz \
  -o sites.hg38.vcf.gz
```

Keep resources in a project or shared reference directory visible to TAFFISH;
Somalier accepts their paths directly, so no fixed container mount point or
download helper is needed. A sketch records ordered counts, not genomic
coordinates. Upstream documents that sketches extracted from corresponding
build-specific sites sets can be compared after extraction, but inputs within
one extraction run must still match their own assembly exactly.

For `ancestry`, the bundled label file is only a mapping of 1000 Genomes sample
IDs to labels. It is not an ancestry model and does not include reference
`.somalier` sketches. Supply labeled reference sketches before `++`, query
sketches after `++`, and pass a matching `--labels` TSV:

```sh
taf-somalier somalier ancestry \
  --labels ancestry-labels.tsv \
  --output-prefix cohort \
  reference-sketches/*.somalier ++ query-sketches/*.somalier
```

See the upstream ancestry guide at
<https://github.com/brentp/somalier/wiki/ancestry>.

## HTML and Network Boundary

All Somalier calculations and HTML generation run without network access. The
upstream HTML templates reference Plotly, jQuery, Bootstrap, and Selectize from
public CDNs. Opening `relate`, `ancestry`, or `AB_plot` HTML therefore needs
browser network access for full interactive rendering unless those assets are
provided separately. TSV outputs are complete and remain fully offline.

This app does not rewrite upstream report templates because doing so would
change the upstream presentation contract.

## Resources and Platform

Native images are built for `linux/amd64` and `linux/arm64`. The source build
uses HTSlib for BAM/CRAM/VCF/BCF access and OpenBLAS for ancestry PCA and model
training. Set `OPENBLAS_NUM_THREADS` when a scheduler must limit BLAS threads.

The upstream Nim package still declares an old `brentp/zip#dev` build
dependency that no source module imports and that conflicts by package name
with Arraymancer's `nim-lang/zip`. The documented build-only patch removes
that unused declaration. It does not change Somalier source code or runtime
features.

Useful upstream environment variables include:

- `SOMALIER_SAMPLE_NAME`: override a BAM/CRAM sample name
- `SOMALIER_ALLOWED_FILTERS`: add accepted VCF FILTER values
- `SOMALIER_REPORT_ALL_PAIRS`: retain all pair rows in large-cohort reports
- `SOMALIER_AB_HOM_CUTOFF`: adjust the homozygous-reference AB cutoff
- `SOMALIER_TARGET_AF`: change the target AF used by `find-sites`

## Boundaries

- A sites VCF, FASTA, alignments/calls, and ancestry references must be chosen
  coherently; the container cannot infer the correct assembly.
- Single-sample VCF and GVCF extraction is supported, but upstream recommends
  BAM/CRAM or jointly called VCF/BCF when available.
- HTML CDN behavior affects browser rendering only, not calculations or TSV
  generation.
- The smoke fixtures prove executable paths and output contracts, not
  production-scale scientific accuracy.

## Troubleshooting

- `unable to open fasta` or CRAM failures usually mean the FASTA, `.fai`,
  alignment index, or assembly naming is missing or mismatched.
- Very long argument lists can be replaced by quoted glob patterns or a
  `.list` file containing one sketch path per line.
- Empty or unstable ancestry results usually indicate too few labeled samples,
  inconsistent site ordering, missing labels, or inadequate class diversity.
- A report that opens without plots usually indicates that its upstream CDN
  assets are blocked; inspect the TSV outputs or allow the documented CDNs.

## Testing

The smoke suite runs each check in an independent fresh-container context. It
covers:

- exact 0.3.3 identity, provenance, every public subcommand help, and licenses
- real extraction from indexed VCF, BAM, and CRAM fixtures
- `relate` TSV/HTML outputs through the 0.3.3 `.list` input path
- `AB_plot`, CHARR/pairwise `contamination`, `find-sites`, and `pedrel`
- synthetic two-class `ancestry`, including OpenBLAS PCA/training and TSV/HTML
- native amd64 and arm64 builds with lightweight QEMU-safe build-time checks

Tests are offline and deterministic at the file-contract level. They do not
replace validation on the user's reference build, cohort, pedigree, or
ancestry panel.

## License and Citation

TAFFISH app packaging: Apache-2.0.

Somalier is MIT licensed. The upstream license and citation metadata are
retained in the image. Cite:

Pedersen BS, Bhetariya PJ, Brown J, et al. Somalier: rapid relatedness
estimation for cancer and germline studies using efficient genome sketches.
Genome Medicine. 2020;12:62. <https://doi.org/10.1186/s13073-020-00761-2>.
