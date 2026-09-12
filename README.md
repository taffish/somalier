# somalier

`somalier` packages [Somalier](https://github.com/brentp/somalier) for TAFFISH.

Package identity:

- name: `somalier`
- command: `taf-somalier`
- kind: `tool`
- version: `0.3.5-r1`
- license: Apache-2.0 (packaging); MIT (upstream)

## What This App Packages

Somalier extracts compact genome sketches for sample identity, relatedness,
pedigree, ancestry and contamination QC. The CLI remains upstream Somalier.
The thin TAFFISH entry adds resource binds and ordinary-user output ownership,
not a second command dispatcher.

The fixed v0.3.5 source is built with Nim 2.2.4 and a complete dependency lock.
This release corrects reference/alternate homozygous counts in relate's TSV and
HTML when matching --sites is supplied, including chromosome X. Stored sketches
and the internal A/B genotypes are unchanged. hileup 0.1.0 retains the earlier
upstream CIGAR-boundary counting fix. The narrow
build-only patch still removes the unused legacy brentp/zip declaration that
collides with Arraymancer's zip dependency. Separately, HTML templates embed
checksum-pinned browser assets and license notices; calculations and upstream
interaction code are unchanged. These adaptations are recorded in the image.

## Scope

All seven public commands are retained: extract, relate, ancestry, AB_plot,
contamination, find-sites and pedrel. Source/entry-point/documentation inspection
found static HTML result viewing, not a desktop/server GUI or optional GUI
distribution. No noVNC, service, GPU, device, port or daemon is introduced.
OpenBLAS provides CPU ancestry PCA/training; NimCUDA/OpenCL in the dependency
graph do not imply a supported Somalier GPU interface.

Production sites, genome FASTA, 1KG sketches and user data are not in the image.
The 1KG label map and tiny test fixtures are bundled; neither is a pretrained
ancestry model. Ancestry remains upstream's experimental feature and trains
from the labeled sketches supplied for that run.

## Container Contents

- somalier and somalier-resources (explicit resource setup/verification)
- HTSlib, OpenBLAS, Python standard library and curl for resource setup
- /opt/somalier/share/ancestry-labels-1kg.tsv
- /opt/somalier/share/doc/somalier/: provenance, lock, patch and HTML asset pins
- /opt/somalier/share/licenses/: upstream, locked Nim/runtime and browser component licenses
- /usr/share/doc/ and /usr/share/common-licenses/: Debian runtime copyright/license notices
- /opt/somalier/share/testdata/: synthetic/upstream tiny fixtures, not references

The compiler, Nimble download cache and development headers stay in the builder.

## Installation

Install TAFFISH and configure Docker, Podman, or Apptainer (native Linux).
The wrapper examples below were validated with TAFFISH 0.11.0.
Once this release is published and accepted into the Hub Index, refresh the
index and install the exact package version:

```sh
taf update
taf install somalier 0.3.5-r1
taf-somalier-v0.3.5-r1 --version
taf-somalier-v0.3.5-r1 --help
```

The versioned wrapper pins this release; `taf-somalier` is the convenient
unversioned command used below. Installing the app does not install production
sites, genome FASTA or 1KG sketches; prepare those separately as described in
Resources, Databases, and Platform. Until Index acceptance, the installation
command above is not an available Hub release.

## Usage

Use the explicit executable before Somalier subcommands:

```sh
taf-somalier -- --help
taf-somalier somalier extract --help
taf-somalier somalier extract --sites sites.hg38.vcf.gz --fasta GRCh38.fa \
  --out-dir sketches sample.bam
taf-somalier somalier relate --sites sites.hg38.vcf.gz --ped cohort.fam \
  --output-prefix cohort sketches/*.somalier
taf-somalier somalier contamination --sites sites.hg38.vcf.gz \
  --output contamination sketches/*.somalier
taf-somalier somalier AB_plot --sites sites.hg38.vcf.gz \
  --output ab.html sketches/*.somalier
```

## Command Mode

taf-somalier --help/--version are wrapper metadata. Somalier itself reports
its version in --help, not --version. Bare subcommands can be interpreted as
container executables; use taf-somalier somalier COMMAND, including after --.
For many sketches, relate accepts a file ending in .list with one path per line.
Use explicit sample prefixes to avoid sample-name collisions.

Always pass the matching sites VCF to relate, including with a .list input:
`taf-somalier somalier relate --sites sites.vcf.gz sketches.list`.
Without --sites the upstream command warns and still reports alphabetical A/B
counts, not correctly oriented REF/ALT homozygous counts. INFO/AF is required
for CHARR. The sites must match the sketch's ordered autosomal/X/Y sites; 0.3.5
rejects different bucket counts, but equal counts alone do not prove identity.
Existing sketches need not be regenerated solely for this reporting fix;
rerun relate with their matching sites. Do not mix RNA and genomic panels.

TAFFISH 0.11 command mode needs literal inner quotes for a value containing
spaces, e.g. `--out-dir '"output with spaces"'` or
`--output-prefix '"report with spaces"'`. Plain shell quotes alone are lost at
the automatic command layer. Resource bind physical paths still require safe
no-space names; that restriction does not apply to these quoted analysis paths.

## Inputs

| Input | Requirement |
| --- | --- |
| BAM/CRAM | Coordinate-sorted, indexed; matching local FASTA and .fai |
| VCF/BCF/GVCF | Indexed compressed calls; AD preferred, GT-only uses pseudo-depths |
| sites VCF | Same assembly, chromosome naming and ordered sites as the reference/input |
| .somalier | Consistent ordered sites across compared samples |
| PED/FAM | Expected pedigree; optional for relate, required for pedrel |
| labels TSV | Reference sample IDs and ancestry labels |

Prefer BAM/CRAM or joint calls over single-sample VCF/GVCF when available.
Prepare FASTA/indexes before read-only analysis; no reference download fallback
is required when all local inputs are supplied. Custom references and population
VCFs for find-sites are project inputs, not an app-managed global database.

## Output Notes

extract writes SAMPLE.somalier. relate writes PREFIX.samples.tsv,
PREFIX.pairs.tsv, PREFIX.groups.tsv and PREFIX.html. contamination writes sample
and pair TSVs. ancestry writes PREFIX.somalier-ancestry.tsv and .html. AB_plot
writes its requested HTML. Existing names can be overwritten: use a new output
directory/prefix for each run. Keep input paths/indexes and parent output
directories visible inside the selected backend.

For ancestry, OPENBLAS_NUM_THREADS controls CPU BLAS parallelism. Set it inside
command mode, for example:
```sh
taf-somalier env OPENBLAS_NUM_THREADS=1 somalier ancestry --help
```
Other upstream environment controls (SOMALIER_SAMPLE_NAME,
SOMALIER_ALLOWED_FILTERS, SOMALIER_REPORT_ALL_PAIRS, SOMALIER_AB_HOM_CUTOFF,
SOMALIER_TARGET_AF) likewise belong inside the container command/environment.

## Resources, Databases, and Platform

### Fixed 1KG ancestry reference

The explicit resource ID 1kg-3479773 pins
[Zenodo 3479773](https://doi.org/10.5281/zenodo.3479773), dataset v0.2.3:
2,504 sketches, 82,856,769 compressed bytes and 533,870,328 expanded bytes.
SHA256: b2b7959cfd6d37d1ac7a96e03aeb13707cfe84e5c3a208329220712a935c5a1e.
The official MD5 is 25c62e15fe71d44fbb525a8648ff3ec2. The record explicitly
licenses the dataset CC-BY-4.0; credit Brent Pedersen and the dataset DOI.
It is not licensed under the app's Apache-2.0 or assumed software MIT.

```sh
root="$HOME/.local/share/taffish/resources/somalier"
mkdir -p "$root"
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_SOMALIER_RESOURCE_INSTALL_ROOT="$root" \
  taf-somalier somalier-resources install --resource 1kg-3479773 \
  --resource-root /resource-install --dry-run
# Remove --dry-run to explicitly download/install.
```

Use backend=podman or apptainer for the same installed-wrapper command.
An administrator may instead create /usr/local/share/taffish/resources/somalier
(or /opt/taffish/resources/somalier) and run installation once as its owner.
Ordinary users subsequently need no sudo, network or write access. This is a
site-local reuse contract, not authorization to redistribute unrelated data.
All site parent directories must allow ordinary-user traversal (normally 0755);
the installer does not change permissions of pre-existing host parents.

The TAFFISH resource installer serializes each resource with a private lock, checks free space
(archive + expanded data + 64 MiB reserve), caches/resumes downloads with finite
retries, checks exact bytes/SHA256, rejects unsafe tar members, and stages on the
destination filesystem before atomic promotion. Directories/files become
0755/0644. resource.json, SHA256SUMS and READY record identity and all members.
Existing installations are fully verified, never blindly skipped or overwritten.
There is no in-place --force: use a fresh parent/identity for a successor.
A corrupt cache or stale lock fails closed with its exact path; inspect ownership
and remove only that named cache/lock after confirming no active installer.
Partial downloads remain hidden in .downloads, never as a prepared resource.
--source can import the exact downloaded archive offline using the same checks.

Select and consume the prepared resource explicitly:

```sh
TAFFISH_SOMALIER_RESOURCE_ID=1kg-3479773 taf-somalier somalier ancestry \
  --labels /opt/somalier/share/ancestry-labels-1kg.tsv --output-prefix ancestry \
  '/somalier-resource/1kg-somalier/*.somalier' ++ query-sketches/*.somalier
```

The upstream guide recommends matching standard GRCh37/hg38 sites. RNA-focused
sites are not interchangeable. Do not infer suitability for other organisms,
panels or populations from the reference's availability.

### Sites: authorized local input and sharing

The upstream [release](https://github.com/brentp/somalier/releases/tag/v0.3.5)
links six fixed sites files. Their attachment pages and VCF headers do not
state a separate data license; software MIT is not assumed to cover attachments.
Automatic redistribution/download of those attachments is therefore not added.
Obtain permission appropriate to your use/sharing, or use your own authorized
sites produced with find-sites. This is a concrete license boundary, not a
blanket exemption because assemblies are selectable.

| Member | Official file | SHA256 |
| --- | --- | --- |
| hg19 | [265208 bytes](https://github.com/brentp/somalier/files/3412453/sites.hg19.vcf.gz) | 66655f4b1a93d9f474a3dd3d251c11f3d897981fb45f1355538dd807a63ba49a |
| GRCh37 | [255634 bytes](https://github.com/brentp/somalier/files/3412455/sites.GRCh37.vcf.gz) | 4ca35db90deb4b0e99838c9ef4d48657384b5e0e962476a90e70e039dd38c64d |
| hg38 chr | [265818 bytes](https://github.com/brentp/somalier/files/3412456/sites.hg38.vcf.gz) | d1a853b8bb2e5f1a520bc67c8303be699543d225d785bce51e8335a2420489b5 |
| hg38 no chr | [258239 bytes](https://github.com/brentp/somalier/files/3412454/sites.hg38.nochr.vcf.gz) | 297d938350eb3b41c3024b657bd8e96a5d85364251ffa5740f64c5d6baeb1343 |
| hg38 RNA | [266638 bytes](https://github.com/brentp/somalier/files/4566475/sites.hg38.rna.vcf.gz) | 901cb1c396460a94a69b21f7f20e51fd2d74ed33ee0857343784bc123f4aa0fa |
| CHM13v2 T2T | [320726 bytes](https://github.com/brentp/somalier/files/9954286/sites.chm13v2.T2T.vcf.gz) | b9d93b878966c9affce67a69274b2ba7965a6328bee7532cd4c9dd8ece32bebc |

Local import requires an explicit local-* identity, source checksum and a
license/authorization note. The note records your authorization; it grants none:

```sh
TAFFISH_SOMALIER_RESOURCE_INSTALL_ROOT="$root" taf-somalier somalier-resources \
  install --resource local-my-sites-v1 --resource-root /resource-install \
  --source sites.vcf.gz --sha256 YOUR_VERIFIED_SHA256 \
  --license-note '"Your actual permission and attribution"'
TAFFISH_SOMALIER_RESOURCE_ID=local-my-sites-v1 taf-somalier somalier extract \
  --sites /somalier-resource/sites.vcf.gz --fasta reference.fa \
  --out-dir sketches sample.bam
```

Uncompressed imported files are named sites.vcf. No helper chooses an assembly
or silently falls back to another panel. Corresponding genomic sites across
assemblies may be comparable after extraction, but the RNA set uses different
coordinates; reference/contig naming must match during extraction.

### Discovery and backend capability matrix

Native platforms remain linux/amd64 and linux/arm64; neither is emulation.
For a selected RESOURCE_ID, precedence is explicit RESOURCE_PATH, personal
~/.local/share/taffish/resources/somalier/ID (or TAFFISH_USER_HOME/resources/somalier/ID), /usr/local/share/.../ID, then
/opt/taffish/resources/somalier/ID. The wrapper checks READY, the receipt schema
and every listed file checksum, exact file inventory, absence of member symlinks,
and the selected ID against the receipt. It resolves root symlinks to the physical
directory and binds it read-only at /somalier-resource. A selected missing,
corrupt, extra-member or ID-mismatched root fails closed. The explicit verifier
also checks member count and fixed-catalog/local-payload source identity.
RESOURCE_AUTO_MOUNT=0 disables discovery. Only one selected unit is mounted per
run; sites extraction and ancestry are separate commands. Explicit upstream
paths remain supported. Resource physical paths must use letters, digits, _, .,
/, + or -; use a safe physical directory when backend argument parsing requires it.

All variables above have prefix TAFFISH_SOMALIER_, e.g.
TAFFISH_SOMALIER_RESOURCE_PATH=/srv/references/somalier/1kg-3479773.
Set RESOURCE_INSTALL_ROOT only during installation: it binds a writable parent
to /resource-install and deliberately takes precedence over read-only discovery.

| Capability | Docker | Podman | Apptainer |
| --- | --- | --- | --- |
| CLI / static HTML generation | same wrapper commands | same wrapper commands | same wrapper commands |
| Managed installation/reuse | RESOURCE_INSTALL_ROOT / RESOURCE_ID / RESOURCE_PATH | same | same |
| Output ownership | calling UID/GID | keep-id and calling UID/GID | calling ordinary user |
| Manual read-only fallback | TAFFISH_DOCKER_RUN_ARGS="-v /safe/root:/somalier-resource:ro" | TAFFISH_PODMAN_RUN_ARGS="-v /safe/root:/somalier-resource:ro" | TAFFISH_APPTAINER_RUN_ARGS="--bind /safe/root:/somalier-resource:ro" |

Use TAFFISH_CONTAINER_BACKEND=docker, podman or apptainer. For manual fallback,
set TAFFISH_SOMALIER_RESOURCE_AUTO_MOUNT=0, verify the prepared root separately,
then invoke the same analysis command. Docker/Podman VM file-sharing must expose
the physical host path. Apptainer requires native Linux and site permissions.
Application-required binds/UID args are in main.taf, not repeated global policy.

## HTML and Network Boundary

relate, ancestry and AB_plot emit single-file interactive HTML with inline,
versioned Plotly, jQuery, Bootstrap and Selectize where needed. Old
plotly-latest references are fixed to their 1.58.5 release; AB_plot retains
2.35.2. Browser component notices are embedded and retained in the image.
No report HTTP service, noVNC port or display is needed: open the generated file
in your host browser. Citation links require networking only if deliberately
clicked. Reports contain sample identifiers and scientific metadata; share only
with authorized readers. TSVs remain independent of the browser.

## Boundaries and Troubleshooting

- Wrong FASTA/sites assembly: correct reference and indexes; the runtime reports the
  mismatch locus. Do not suppress the check to make an extraction pass.
- Missing 1KG reference: run explicit setup or provide labeled local sketches;
  ancestry never downloads a model automatically.
- Missing shared resource: choose the exact prepared RESOURCE_PATH or inspect
  somalier-resources verify. No silent fallback or resource writes on analysis.
- Failed download/cache verification: preserve the diagnostic, inspect the named
  cache file and source; no automatic checksum bypass.
- Reports overwrite their requested filenames; use fresh prefixes.
- Ancestry needs sufficient diverse labeled samples and consistent site order.
  Tiny packaging tests are not accuracy, clinical or population validation.

## Testing

Current 0.3.5-r1 validation used native arm64 Docker/Podman and native amd64
Docker/Podman/Apptainer on the maintainer's xjp server. All 261 exact manifest
checks passed: 14 existence probes and 15 independent tests in nine groups,
including Docker/Podman normal and read-only roots and an actual read-only SIF
generated from the same amd64 OCI. All 140 final-wrapper checks passed across
the five measured platform/backend combinations. An interrupted local Podman
client group was preserved and replaced by a complete successful serial rerun.
The suite covers every public
help, identity/provenance, indexed BAM/CRAM/VCF extraction, .list relatedness,
contamination, AB_plot, find-sites, pedrel, synthetic ancestry, the M-versus-=/X
CIGAR regression, reference mismatch diagnostics, resource import/idempotence/
corruption rejection and offline HTML dependency closure. New reference-count
regression checks TSV and HTML counts, autosomal/X orientation, unchanged pair
results and sketches, missing-sites warnings and autosomal/X/Y mismatch rejection.
Only identity/help/notices and tiny VCF extraction run at Docker build time;
full calculations and browser rendering remain runtime checks.
Ten offline resource-contract checks and eight injected main/subcommand help
failures passed. The complete pinned 1KG resource was downloaded and installed
through the current wrapper; all 2,504 members were verified read-only on all
three xjp backends, with denied writes and offline idempotence. A second complete
installation reused the verified cache with networking disabled through the
actual Apptainer SIF. These prove resource mechanics, not ancestry accuracy.
All resource tests used private ordinary-user paths; administrator-owned system
installation and multi-user privilege switching were not performed.

Current images are 196,878,416 bytes (amd64) and 197,640,014 bytes (arm64).
The approximately 17 MB Somalier payload and required HTSlib/OpenBLAS/Python
runtime remain; compiler, development headers, Nimble/download caches and
production resources are absent. Debian copyright/license notices are retained.
Arm64 Apptainer is not separately validated; native-platform and backend evidence
axes are both satisfied, without an identified architecture-specific SIF risk.

The current browser tool rejected local HTML navigation under its URL security
policy; no workaround was attempted. Report generation, inline-asset closure,
embedded data and TSV/HTML reference-count consistency passed, but actual browser
rendering, interaction, console/network state and PNG export still require
maintainer acceptance. This is not an observed report-rendering failure. The
candidate is not yet ordinary publish_ready and has not been published.

## License and Citation

TAFFISH packaging: Apache-2.0. Somalier: MIT; hileup: Apache-2.0 (the pinned
source LICENSE, correcting the earlier MIT description). Locked Nim dependencies,
embedded miniz/stb components and Nim runtime notices are retained with source
identities and checksum inventories under /opt/somalier/share/licenses/.
Debian runtime copyright notices remain under /usr/share/doc/ with shared
license texts under /usr/share/common-licenses/; they are not disposable caches.
The fixed browser
libraries retain their own licenses (MIT; Selectize Apache-2.0, with bundled
component notices). Resource permissions are separate, as described above.
Cite [Pedersen et al., Genome Medicine 2020;12:62](https://doi.org/10.1186/s13073-020-00761-2)
for Somalier and [Zenodo 3479773](https://doi.org/10.5281/zenodo.3479773) when
using the 1KG sketches.
