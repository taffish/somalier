# Source, base images and Nim dependencies are pinned and verified. Debian APT
# metadata/packages remain rolling: availability and resolved versions may drift.
# Upstream/CDN retention can invalidate old URLs; checks fail rather than silently
# accepting replacements. These pins do not promise perpetual rebuildability.
ARG NIM_BUILDER_IMAGE=nimlang/nim:2.2.4@sha256:6918c5619250b7c6f200a98f4602dadaa8d74a4534d29a998b40675a94ada8ab
ARG RUNTIME_IMAGE=debian:13-slim@sha256:020c0d20b9880058cbe785a9db107156c3c75c2ac944a6aa7ab59f2add76a7bd
ARG SOMALIER_VERSION=0.3.6
ARG SOMALIER_COMMIT=43fdfdffc89cb19d4804f6b8ded448a5770779bf
ARG SOMALIER_SOURCE_SHA256=7dc3c8764d9dd962221b653353be0e444ac98e53d1c872e47d745674215f2da2

FROM ${NIM_BUILDER_IMAGE} AS builder

ARG SOMALIER_VERSION
ARG SOMALIER_COMMIT
ARG SOMALIER_SOURCE_SHA256
ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' \
      /etc/apt/sources.list.d/debian.sources; \
    apt-get -o Acquire::Retries=5 update; \
    attempt=1; \
    until apt-get -o Acquire::Retries=5 -o Acquire::http::Pipeline-Depth=0 \
      install -y --no-install-recommends \
        build-essential ca-certificates curl git libbz2-dev \
        libcurl4-gnutls-dev libhts-dev liblzma-dev libopenblas-dev \
        libssl-dev patch pkg-config python3 samtools tabix zlib1g-dev; do \
      if [ "$attempt" -ge 5 ]; then exit 1; fi; \
      attempt=$((attempt + 1)); \
      sleep 5; \
      apt-get -o Acquire::Retries=5 update; \
    done; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

WORKDIR /tmp/build

COPY docker/nimble.lock /tmp/nimble.lock
COPY docker/remove-unused-zip-dependency.patch /tmp/remove-unused-zip-dependency.patch
COPY docker/make-testdata.sh /tmp/make-testdata.sh
COPY docker/report-assets.json /tmp/report-assets.json
COPY docker/embed-report-assets.py /tmp/embed-report-assets.py

RUN set -eux; \
    curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL \
      "https://github.com/brentp/somalier/archive/refs/tags/v${SOMALIER_VERSION}.tar.gz" \
      -o somalier.tar.gz; \
    echo "${SOMALIER_SOURCE_SHA256}  somalier.tar.gz" | sha256sum -c -; \
    mkdir src; \
    tar -xzf somalier.tar.gz -C src --strip-components=1; \
    cd src; \
    test "$(sed -n 's/let somalierVersion\* = "\([^"]*\)"/\1/p' src/somalierpkg/version.nim)" = "${SOMALIER_VERSION}"; \
    patch -p1 < /tmp/remove-unused-zip-dependency.patch; \
    if grep -F 'https://github.com/brentp/zip#dev' somalier.nimble; then exit 1; fi; \
    cp /tmp/nimble.lock nimble.lock; \
    git config --global http.version HTTP/1.1; \
    attempt=1; \
    until nimble install -d -y; do \
      if [ "$attempt" -ge 5 ]; then exit 1; fi; \
      attempt=$((attempt + 1)); \
      rm -rf /tmp/nimble_*; \
      sleep 5; \
    done; \
    grep -F '"vcsRevision": "a04aa8a39c7f9aa69e5cbac30a19620061635a6f"' nimble.lock >/dev/null; \
    grep -F '"vcsRevision": "3133320d9660620a4a7f4da5647c85bf2b2738a6"' nimble.lock >/dev/null; \
    grep -F '"vcsRevision": "93ad65442b16d0191aa0c44803d10a6fb7cde9fa"' nimble.lock >/dev/null; \
    paths="$(find /root/.nimble/pkgs2 -mindepth 1 -maxdepth 1 -type d \
      -printf '--path:%p --path:%p/src ')"; \
    python3 /tmp/embed-report-assets.py /tmp/build/src /tmp/report-assets /tmp/report-assets.json; \
    nim c $paths -d:danger -d:release -o:/tmp/build/somalier src/somalier.nim; \
    /tmp/build/somalier --help 2>&1 | grep -F "somalier version: ${SOMALIER_VERSION}" >/dev/null; \
    /tmp/build/somalier --help 2>&1 | grep -F 'contamination' >/dev/null

RUN set -eux; \
    install_root=/opt/somalier; \
    fixture="$install_root/share/testdata"; \
    mkdir -p \
      "$install_root/bin" \
      "$install_root/share/doc/somalier" \
      "$install_root/share/licenses/somalier" \
      "$fixture"; \
    install -m 0755 /tmp/build/somalier "$install_root/bin/somalier"; \
    strip "$install_root/bin/somalier"; \
    install -m 0644 src/README.md src/CHANGES.md src/CITATION.cff \
      "$install_root/share/doc/somalier/"; \
    install -m 0644 src/cancer-concordance-contamination.md \
      "$install_root/share/doc/somalier/"; \
    install -m 0644 src/LICENSE "$install_root/share/licenses/somalier/LICENSE"; \
    install -m 0644 src/scripts/ancestry-labels-1kg.tsv \
      "$install_root/share/ancestry-labels-1kg.tsv"; \
    install -m 0644 src/nimble.lock \
      "$install_root/share/doc/somalier/nimble.lock"; \
    install -m 0644 /tmp/remove-unused-zip-dependency.patch \
      "$install_root/share/doc/somalier/remove-unused-zip-dependency.patch"; \
    install -m 0644 /tmp/make-testdata.sh \
      "$install_root/share/doc/somalier/make-testdata.sh"; \
    install -m 0644 /tmp/report-assets.json /tmp/embed-report-assets.py \
      "$install_root/share/doc/somalier/"; \
    mkdir -p "$install_root/share/licenses/report-assets"; \
    install -m 0644 /tmp/report-assets/LICENSE-* "$install_root/share/licenses/report-assets/"; \
    /bin/sh /tmp/make-testdata.sh /tmp/build/src "$fixture"; \
    { \
      echo "Somalier ${SOMALIER_VERSION}"; \
      echo "upstream_tag=v${SOMALIER_VERSION}"; \
      echo "upstream_commit=${SOMALIER_COMMIT}"; \
      echo "source=https://github.com/brentp/somalier/archive/refs/tags/v${SOMALIER_VERSION}.tar.gz"; \
      echo "source_sha256=${SOMALIER_SOURCE_SHA256}"; \
      echo "nim=2.2.4"; \
      echo "nim_builder_image=nimlang/nim:2.2.4@sha256:6918c5619250b7c6f200a98f4602dadaa8d74a4534d29a998b40675a94ada8ab"; \
      echo "runtime_image=debian:13-slim@sha256:020c0d20b9880058cbe785a9db107156c3c75c2ac944a6aa7ab59f2add76a7bd"; \
      echo "dependency_lock_sha256=$(sha256sum src/nimble.lock | awk '{print $1}')"; \
      echo "build_patch_sha256=$(sha256sum /tmp/remove-unused-zip-dependency.patch | awk '{print $1}')"; \
      echo "build_patch=remove unused legacy brentp/zip declaration; no source module imports it"; \
      echo "html_adaptation=fixed checksum-verified browser libraries embedded in original templates; no analysis algorithm changes"; \
      echo "build=official tagged source; locked Nim dependencies; system HTSlib and OpenBLAS; native linux/amd64 and linux/arm64"; \
    } > "$install_root/share/doc/somalier/source.txt"; \
    chmod -R a+rX "$install_root"; \
    test -s "$fixture/test.bam.bai"; \
    test -s "$fixture/test.cram.crai"; \
    test -s "$fixture/ancestry.vcf.gz.tbi"; \
    test -s "$install_root/share/ancestry-labels-1kg.tsv"

COPY docker/licenses/ /opt/somalier/share/licenses/
COPY docker/collect-nim-notices.py /tmp/collect-nim-notices.py
RUN python3 /tmp/collect-nim-notices.py /opt/somalier/share/licenses \
      /root/.cache/nim/somalier_r /tmp/build/src/nimble.lock

FROM ${RUNTIME_IMAGE}

LABEL org.opencontainers.image.title="Somalier" \
      org.opencontainers.image.description="TAFFISH runtime for sample identity, relatedness, ancestry, and contamination QC" \
      org.opencontainers.image.source="https://github.com/brentp/somalier" \
      org.opencontainers.image.licenses="MIT"

ARG SOMALIER_VERSION
ARG SOMALIER_COMMIT
ARG SOMALIER_SOURCE_SHA256
ENV DEBIAN_FRONTEND=noninteractive \
    SOMALIER_HOME=/opt/somalier \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/somalier/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COPY --from=builder /opt/somalier /opt/somalier
COPY docker/somalier-smoke.sh /opt/somalier/share/testdata/somalier-smoke.sh
COPY docker/check-notices.py /opt/somalier/share/testdata/check-notices.py
COPY docker/test-reference-counts.py /opt/somalier/share/testdata/test-reference-counts.py
COPY docker/somalier-resources.py /usr/local/bin/somalier-resources
COPY src/resource_validation.py /opt/somalier/lib/resource_validation.py

RUN set -eux; \
    apt-get -o Acquire::Retries=5 update; \
    attempt=1; \
    until apt-get -o Acquire::Retries=5 -o Acquire::http::Pipeline-Depth=0 \
      install -y --no-install-recommends \
        ca-certificates coreutils findutils grep gzip libhts3t64 \
        libopenblas0-pthread mawk sed curl python3; do \
      if [ "$attempt" -ge 5 ]; then exit 1; fi; \
      attempt=$((attempt + 1)); \
      sleep 5; \
      apt-get -o Acquire::Retries=5 update; \
    done; \
    libhts_path="$(dpkg-query -L libhts3t64 | \
      sed -n '/\/libhts\.so\.3$/ {p;q;}')"; \
    test -n "$libhts_path"; \
    ln -s "$libhts_path" /usr/local/lib/libhts.so; \
    ldconfig; \
    test -e /usr/local/lib/libhts.so; \
    rm -rf \
      /var/lib/apt/lists/* \
      /var/cache/apt/archives/* \
      /root/.cache \
      /usr/share/info/* \
      /usr/share/man/*; \
    chmod 0755 /opt /opt/somalier /opt/somalier/lib; \
    chmod 0644 /opt/somalier/lib/resource_validation.py; \
    chmod 0755 /opt/somalier/share/testdata/somalier-smoke.sh; \
    chmod 0755 /usr/local/bin/somalier-resources; \
    find /usr/lib/python3* -type d -name __pycache__ -prune -exec rm -rf '{}' +; \
    ln -s /opt/somalier/bin/somalier /usr/local/bin/somalier; \
    grep -F "upstream_commit=${SOMALIER_COMMIT}" \
      /opt/somalier/share/doc/somalier/source.txt >/dev/null; \
    grep -F "source_sha256=${SOMALIER_SOURCE_SHA256}" \
      /opt/somalier/share/doc/somalier/source.txt >/dev/null; \
    /bin/sh -x /opt/somalier/share/testdata/somalier-smoke.sh identity; \
    /bin/sh -x /opt/somalier/share/testdata/somalier-smoke.sh extract-vcf; \
    rm -rf /tmp/taf-somalier-*

ENV TAFFISH_ENV=TAFFISH \
    TAFFISH_NAME=somalier \
    TAFFISH_VERSION=${SOMALIER_VERSION} \
    TAFFISH_RELEASE=1

WORKDIR /work
