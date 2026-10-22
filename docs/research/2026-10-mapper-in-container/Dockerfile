# G-0006-2 spike: the Exporter's Linux mapper (gamescope headless + umu-run + Proton)
# in Docker, mirroring home-server/wrf-gpu/install.sh. Spike evidence, not the
# production image. Build context: this file, home-server's
# wrf-gpu/apt/debian-backports.sources, and exporter.tar (the Exporter's src/ with the
# downloaded UE4SS under src/mapper/ue4ss/, options_schema.py, requirements.txt,
# pyproject.toml). How it was run: ../2026-10-mapper-in-container.md.
FROM debian:trixie
ARG UMU_VERSION=1.4.4
# Mesa is pinned to the backports build the spike ran on (ADR-0006, G-0006-2).
ARG MESA_VERSION=26.1.6-1~bpo13+1
ENV DEBIAN_FRONTEND=noninteractive
COPY debian-backports.sources /etc/apt/sources.list.d/
RUN dpkg --add-architecture i386 && apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl python3 python3-venv \
      vulkan-tools procps \
 && apt-get install -y --no-install-recommends -t trixie-backports gamescope \
      mesa-vulkan-drivers=${MESA_VERSION} libgl1-mesa-dri=${MESA_VERSION} \
 && cd /tmp \
 && curl -fsSLO https://github.com/Open-Wine-Components/umu-launcher/releases/download/${UMU_VERSION}/python3-umu-launcher_${UMU_VERSION}-1_amd64_debian-13.deb \
 && curl -fsSLO https://github.com/Open-Wine-Components/umu-launcher/releases/download/${UMU_VERSION}/umu-launcher_${UMU_VERSION}-1_all_debian-13.deb \
 && apt-get install -y -t trixie-backports ./*.deb libgl1-mesa-dri:i386=${MESA_VERSION} \
      libglx-mesa0:i386=${MESA_VERSION} mesa-vulkan-drivers:i386=${MESA_VERSION} \
 && rm -f ./*.deb && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 wrf && usermod -aG render,video wrf 2>/dev/null || true
COPY exporter.tar /opt/
RUN mkdir /opt/exporter && tar -xf /opt/exporter.tar -C /opt/exporter && rm /opt/exporter.tar \
 && python3 -m venv /opt/venv && /opt/venv/bin/pip install -q -r /opt/exporter/requirements.txt \
 && chown -R wrf:wrf /opt/exporter
ENV PATH=/usr/games:/opt/venv/bin:$PATH XDG_RUNTIME_DIR=/run/user/1000
WORKDIR /opt/exporter
USER wrf
