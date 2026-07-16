============================================================================
                     AI CREATIVE STUDIO - STORAGE DESIGN
                    External-First Storage Architecture
============================================================================

DESIGN PRINCIPLE
----------------
The compute brain's root partition is SACRED. It contains:
  - The operating system
  - Docker engine and container images
  - SSH server

That's it. NOTHING else goes on root.

All models, projects, exports, cache, and logs live on external storage
mounted at /mnt/studio/. This means:
  - You can swap compute brains without losing data
  - You can plug the external drive into any machine to access files
  - Backups are trivial (copy /mnt/studio/)
  - Root partition stays clean and fast


EXTERNAL DRIVE OPTIONS
----------------------

Option A: Direct-Attached SSD (recommended)
  - USB-C or Thunderbolt NVMe enclosure + 1TB NVMe
  - Best throughput: 1-3 GB/s (TB), 400-1000 MB/s (USB 3.x)
  - Simplest setup, single point of failure

Option B: Network-Attached Storage (NAS)
  - NFS share from a NAS device or another machine
  - Throughput: 100-125 MB/s over gigabit
  - Good for multi-device access
  - Higher latency affects model loading time

Option C: SMB/CIFS Share
  - Windows/macOS file sharing
  - Throughput: 80-110 MB/s typical
  - Use only if NFS is not available

Option D: Hybrid (recommended for the user's setup)
  - Primary: Direct-attached SSD for active models + projects
  - Secondary: NFS/SMB share for archival and backup
  - Best of both worlds


MOUNT SETUP
-----------

Direct-Attached SSD (Linux)
----------------------------
# 1. Identify the drive
lsblk
# or
sudo fdisk -l

# 2. Format (ONE TIME ONLY - destroys data)
sudo mkfs.ext4 -L studio /dev/sdX1

# 3. Create mount point
sudo mkdir -p /mnt/studio

# 4. Get UUID (use UUID not device name)
sudo blkid /dev/sdX1

# 5. Add to /etc/fstab for auto-mount at boot
# UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx /mnt/studio ext4 defaults,noatime,nofail 0 2
sudo nano /etc/fstab

# 6. Mount now
sudo mount -a

# 7. Set ownership (your user, not root)
sudo chown -R $(id -u):$(id -g) /mnt/studio

# 8. Verify
df -h /mnt/studio
ls -la /mnt/studio/


NFS Mount (from remote NAS)
---------------------------
# 1. Install NFS client
sudo apt install -y nfs-common

# 2. Create mount point
sudo mkdir -p /mnt/studio

# 3. Add to /etc/fstab
# nas-server:/path/to/share /mnt/studio nfs defaults,_netdev,nofail,soft,timeo=30 0 0
sudo nano /etc/fstab

# 4. Mount
sudo mount -a

# 5. Set ownership
sudo chown -R $(id -u):$(id -g) /mnt/studio


SMB/CIFS Mount
--------------
# 1. Install SMB client
sudo apt install -y cifs-utils

# 2. Create credentials file
sudo nano /etc/samba/credentials-studio
  username=your_user
  password=your_pass

sudo chmod 600 /etc/samba/credentials-studio

# 3. Add to /etc/fstab
# //server/share /mnt/studio cifs credentials=/etc/samba/credentials-studio,_netdev,nofail,iocharset=utf8,uid=1000,gid=1000 0 0
sudo nano /etc/fstab

# 4. Mount
sudo mount -a


DIRECTORY STRUCTURE CREATION
-----------------------------
After mounting, create the full directory tree:

sudo mkdir -p /mnt/studio/{models/{text,image,video,audio},projects,exports,uploads,cache,logs}

# Verify
tree -L 2 /mnt/studio/ || ls -R /mnt/studio/

Expected output:
/mnt/studio/
  cache/
  exports/
  logs/
  models/
    audio/
    image/
    text/
    video/
  projects/
  uploads/


STORAGE ESTIMATES
-----------------
Component               Size        Notes
─────────────────────── ─────────── ─────────────────────────────────────
Models:
  Llama 3.1 70B          ~40 GB      Largest single model
  Llama 3.1 8B            ~4.7 GB     Quick helper model
  Mistral 7B              ~4.1 GB     Fast general-purpose
  CodeLlama 13B           ~7.4 GB     Code generation
  Qwen 2.5 7B             ~4.4 GB     Multilingual
  Flux.1 Dev              ~24 GB      Image generation
  Flux.1 Schnell          ~24 GB      Fast image generation
  SDXL 1.0                ~6.5 GB    Image generation
  SDXL Turbo              ~6.5 GB    Fast image generation
  RealVisXL V4.0          ~6.5 GB    Photorealistic
  Juggernaut XL V9        ~6.5 GB    Versatile
  CogVideoX 5B            ~12 GB      Video generation
  SVD XT                  ~9.8 GB    Image-to-video
  Wan 2.1 1.3B            ~3 GB       Lightweight video
  Kokoro TTS              ~300 MB     Voiceover
  AudioCraft/MusicGen     ~3.5 GB    Background music
  Whisper Large-v3        ~3 GB       Transcription
  ─────────────────────────────────────
  Models Total:          ~160 GB

Runtime:
  Docker images          ~15 GB      Cached on host
  Model cache (Torch)    ~5 GB       HuggingFace cache
  ComfyUI models         ~2 GB       Custom nodes + extras
  ─────────────────────────────────────
  Runtime Total:         ~22 GB

Workspace (variable):
  Active projects        10-50 GB    Per-project video/audio
  Exports                5-20 GB     Rendered output
  Uploads                Variable    Input media
  ─────────────────────────────────────
  Workspace Total:       ~30-100 GB

════════════════════════════════════════════════════════════════════════════
MINIMUM EXTERNAL DRIVE:   256 GB  (core text + image models + small projects)
RECOMMENDED:              512 GB  (full stack + comfortable workspace)
IDEAL:                    1 TB+   (everything + large projects + backup headroom)
════════════════════════════════════════════════════════════════════════════


SYMLINK STRATEGY FOR DOCKER
----------------------------
Docker containers bind-mount /mnt/studio directly. No symlinks needed
inside containers. But on the HOST, if you use multiple external drives:

# Example: models on fast drive, projects on large drive
sudo mount /dev/nvme0n1p1 /mnt/studio-models
sudo mount /dev/sdb1 /mnt/studio-projects

# Create unified view
sudo ln -s /mnt/studio-models/models /mnt/studio/models
sudo ln -s /mnt/studio-projects/projects /mnt/studio/projects
sudo ln -s /mnt/studio-projects/exports /mnt/studio/exports

Docker only sees /mnt/studio/ - it doesn't care about underlying drives.


BACKUP STRATEGY
---------------

Method 1: rsync to secondary location
  rsync -avh --progress /mnt/studio/ /mnt/backup/studio/

Method 2: rsync over SSH to another machine
  rsync -avh --progress /mnt/studio/ user@backup-host:/backup/studio/

Method 3: Automated daily backup (add to cron)
  # /etc/cron.d/studio-backup
  0 3 * * * root rsync -a --delete /mnt/studio/ /mnt/backup/studio/ >> /mnt/studio/logs/backup.log 2>&1

Method 4: Project-level sync to laptop (what the user actually uses)
  # Run from laptop
  rsync -avh --progress studio:/mnt/studio/exports/ ~/studio-exports/
  rsync -avh --progress studio:/mnt/studio/projects/my-project/ ~/studio-projects/

Models don't need frequent backup (they're downloadable).
Projects and exports do. Back up nightly or after each session.


PERFORMANCE TIPS
----------------
1. Use ext4 or xfs filesystem (not NTFS/FAT32)
2. Use noatime in fstab mount options (reduces write overhead)
3. USB 3.2 or Thunderbolt for direct-attach (avoid USB 2.0)
4. For NFS: use gigabit ethernet minimum, prefer 10GbE
5. Keep models on the fastest drive (NVMe > SATA > HDD)
6. Cache directory can be on host SSD for speed
7. Set swappiness low: echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf


DISK MONITORING
---------------
# Check available space
df -h /mnt/studio

# Check per-directory usage
du -sh /mnt/studio/* | sort -h

# Monitor in real-time
watch -n 5 'df -h /mnt/studio'

# Alert when below 50GB free (add to cron)
# 0 */6 * * * [ $(df /mnt/studio --output=avail -B1 | tail -1) -lt 50000000000 ] && echo "LOW DISK" | mail -s "Studio Storage Alert" you@email.com


LAPTOP STORAGE CONSIDERATIONS
------------------------------
The laptop only needs:
  - Active project files being edited (sync from compute brain)
  - Final exports (downloaded from compute brain)
  - DaVinci Resolve project files

The laptop does NOT need:
  - Models (compute brain has them)
  - Docker images (compute brain runs them)
  - Cache/temp files (compute brain's job)

Typical laptop footprint: 5-50 GB for active work.

============================================================================
