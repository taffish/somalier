somalier 0.3.3-r1

Purpose:
  Extract compact genome sketches and use them for sample identity,
  relatedness, pedigree, ancestry, allele-balance, and contamination QC.

Usage:
  taf-somalier -- --help
  taf-somalier somalier COMMAND [options]

Common workflows:
  Extract sketches from BAM, CRAM, VCF, BCF, or GVCF:
    taf-somalier somalier extract \
      --sites sites.hg38.vcf.gz --fasta GRCh38.fa \
      --out-dir sketches sample.bam

  Calculate relatedness, optionally against a pedigree:
    taf-somalier somalier relate \
      --sites sites.hg38.vcf.gz --ped cohort.fam \
      --output-prefix cohort sketches/*.somalier

  Use a long path list, one sketch path per line:
    taf-somalier somalier relate --output-prefix cohort sketches.list

Commands:
  extract         Extract sketches from BAM, CRAM, VCF, BCF, or GVCF.
  relate          Calculate relatedness and sample-level QC.
  ancestry        Predict ancestry from labeled and query sketches.
  AB_plot         Plot autosomal allele balance and depth.
  contamination   Estimate CHARR and pairwise contamination.
  find-sites      Select an informative sites VCF from a population VCF.
  pedrel          Report expected relationships from PED/FAM data.

Inputs:
  BAM/CRAM or VCF/BCF/GVCF  Indexed alignments or variant calls.
  sites VCF and FASTA       Ordered sites and matching reference assembly.
  .somalier sketches        Inputs for relate, ancestry, and QC reports.
  PED/FAM or labels TSV     Optional pedigree or ancestry labels.

Key outputs:
  <sample>.somalier      One compact binary sketch per sample.
  PREFIX.samples.tsv     Sample-level relatedness and QC metrics.
  PREFIX.pairs.tsv       Pairwise relatedness or contamination rows.
  PREFIX.groups.tsv      Related sample groups.
  PREFIX.html            Interactive relatedness report.
  PREFIX.somalier-ancestry.{tsv,html}  Ancestry results and report.

Sites and reference data:
  Production sites files and genome FASTA files are not bundled. Download a
  sites file matching the assembly and chromosome naming of your inputs.

  hg38 with chr:
    https://github.com/brentp/somalier/files/3412456/sites.hg38.vcf.gz
  hg38 without chr:
    https://github.com/brentp/somalier/files/3412454/sites.hg38.nochr.vcf.gz
  GRCh37:
    https://github.com/brentp/somalier/files/3412455/sites.GRCh37.vcf.gz
  hg19:
    https://github.com/brentp/somalier/files/3412453/sites.hg19.vcf.gz
  T2T CHM13v2:
    https://github.com/brentp/somalier/files/9954286/sites.chm13v2.T2T.vcf.gz
  hg38 RNA-focused:
    https://github.com/brentp/somalier/files/4566475/sites.hg38.rna.vcf.gz

Ancestry data:
  The image includes only the upstream 1000 Genomes label map:
    /opt/somalier/share/ancestry-labels-1kg.tsv
  Supply reference sketches before ++ and query sketches after ++.

Platform and resources:
  Native linux/amd64 and linux/arm64 images are provided. HTSlib handles
  sequence and variant formats; OpenBLAS is retained for ancestry analysis.
  OPENBLAS_NUM_THREADS can limit BLAS threads under a scheduler.

Boundaries:
  Input, sites VCF, FASTA, and indexes must use a coherent assembly.
  Computation and HTML generation are offline. Upstream HTML files load
  Plotly and related browser assets from public CDNs when viewed.
  TSV outputs do not require browser network access.

Detailed documentation:
  https://github.com/taffish/somalier
  https://github.com/brentp/somalier#usage

Wrapper options:
  taf-somalier --help       Show this TAFFISH help.
  taf-somalier --version    Show TAFFISH wrapper version.
  taf-somalier --compile    Compile the TAFFISH wrapper.
  taf-somalier -- --help    Pass --help to the default somalier command.

Notes:
  Use "taf-somalier somalier COMMAND ..." for upstream subcommands; automatic
  command mode otherwise treats the first bare word as a container executable.
