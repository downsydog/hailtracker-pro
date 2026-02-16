FROM mambaorg/micromamba:1.5.8

USER root
WORKDIR /app

# System deps (curl for healthchecks/debug)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy code first (keeps rebuilds consistent)
COPY . /app

# Create conda env with Py-ART stack (NetCDF/HDF5) + pip deps
# - arm_pyart from conda-forge is the sane install path for Py-ART
# - netcdf4/h5py/etc get pulled correctly
RUN micromamba create -y -n hail -c conda-forge \
      python=3.11 \
      arm_pyart \
      netcdf4 \
      h5py \
      numpy \
      scipy \
      pandas \
      shapely \
      pyproj \
      gunicorn \
      eccodes \
      cfgrib \
      xarray \
  && micromamba clean -a -y

# Install the rest via pip inside the conda env
RUN micromamba run -n hail pip install --no-cache-dir \
      -r requirements.txt \
      nexradaws \
      flask-limiter \
      flask-cors \
      psycopg2-binary \
      openpyxl \
      python-docx

# Runtime env
ENV PYTHONUNBUFFERED=1
ENV SKIP_HEAVY_ML=true
ENV DEV_MODE=false

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
  CMD curl -sf http://localhost:5000/api/system/health || exit 1

# Use exec so Python becomes PID 1 and receives signals directly.
# micromamba run wraps the child process — signals may not be forwarded.
CMD ["bash", "-c", "eval \"$(micromamba shell hook --shell bash)\" && micromamba activate hail && exec python run.py --host 0.0.0.0 --port 5000 --monitor"]
